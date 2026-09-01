import hashlib
import logging
import math
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config.settings import settings
from models import (
    Base, RefWilayah, RefSumberData, RefIcd10, FaskesPuskesmas, TblRumahSakit, TblPenduduk, TblAgregatWilayah,
    TblPipelineLog, EnumKelasRS, EnumKepemilikan, EnumTipeWilayah, EnumPipelineStatus, EnumTipeRawatPuskesmas,
    TblTenagaKesehatan, TblPasienPenyakitWilayah, EnumJenisNakes, EnumTipePelayanan, EnumStatusKasusPenyakit
)

logger = logging.getLogger("DatabaseUpserter")

def get_engine():
    return create_engine(settings.sync_database_url, echo=False)

def get_session() -> Session:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def init_db():
    """Initialize database extensions and create tables."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
        conn.commit()
    Base.metadata.create_all(engine)

    # Ensure GIST indexes for spatial performance & GIN for Trigram text search
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_rs_geom ON tbl_rumah_sakit USING GIST (geom);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pkm_geom ON faskes_puskesmas USING GIST (geom);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_wilayah_geom ON ref_wilayah USING GIST (geom);"))
        
        # GIN Trigram indexes for fast typo-tolerant fuzzy search (<5ms)
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rs_nama_trgm ON tbl_rumah_sakit USING GIN (nama_rs gin_trgm_ops);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pkm_nama_trgm ON faskes_puskesmas USING GIN (nama gin_trgm_ops);"))

        # Point 5: Unified Spatial View for All Faskes (RS + Puskesmas)
        conn.execute(text("DROP VIEW IF EXISTS v_faskes_all CASCADE;"))
        conn.execute(text("""
            CREATE VIEW v_faskes_all AS
            SELECT 
                kode_rs AS id_faskes,
                'rumah_sakit' AS jenis_faskes,
                nama_rs AS nama,
                kelas::text AS kelas_tipe,
                kepemilikan::text AS kepemilikan,
                alamat,
                kode_bps,
                telepon,
                jumlah_tt,
                lat,
                lng,
                geom,
                is_valid_coord,
                coverage_periode
            FROM tbl_rumah_sakit
            UNION ALL
            SELECT 
                kode_puskesmas AS id_faskes,
                'puskesmas' AS jenis_faskes,
                nama,
                tipe_rawat::text AS kelas_tipe,
                'pemerintah' AS kepemilikan,
                alamat,
                kode_bps,
                telepon,
                jumlah_tt,
                lat,
                lng,
                geom,
                is_valid_coord,
                coverage_periode
            FROM faskes_puskesmas;
        """))

        # Point 3 & 5: Pre-built PostgreSQL Spatial View for Frontend/Backend Choropleth
        conn.execute(text("DROP VIEW IF EXISTS v_choropleth_wilayah CASCADE;"))
        conn.execute(text("""
            CREATE VIEW v_choropleth_wilayah AS
            SELECT 
                w.kode_bps,
                w.nama_wilayah,
                w.tipe,
                COALESCE(a.total_rs, 0) AS total_rs,
                COALESCE(pkm.total_pkm, 0) AS total_puskesmas,
                COALESCE(a.total_tt, 0) + COALESCE(pkm.total_pkm_tt, 0) AS total_tt,
                COALESCE(a.jumlah_penduduk, 0) AS jumlah_penduduk_2021,
                COALESCE(a.rasio_tt_per_1000, 0.0) AS rasio_tt_resmi,
                COALESCE(a.kategori_ketercukupan, 'kuning') AS kategori_who_resmi,
                ROUND((COALESCE(a.jumlah_penduduk, 0) * 1.03549)::numeric, 0) AS proyeksi_penduduk_2026,
                ROUND(CASE WHEN COALESCE(a.jumlah_penduduk, 0) > 0 THEN ((COALESCE(a.total_tt, 0) + COALESCE(pkm.total_pkm_tt, 0)) / (a.jumlah_penduduk * 1.03549) * 1000.0)::numeric ELSE 0.0 END, 2) AS rasio_tt_proyeksi_2026,
                w.geom
            FROM ref_wilayah w
            LEFT JOIN tbl_agregat_wilayah a ON a.kode_bps = w.kode_bps
            LEFT JOIN (
                SELECT 
                    kode_bps,
                    COUNT(*) AS total_pkm,
                    SUM(COALESCE(jumlah_tt, 0)) AS total_pkm_tt
                FROM faskes_puskesmas
                GROUP BY kode_bps
            ) pkm ON pkm.kode_bps = w.kode_bps;
        """))
        conn.commit()

    logger.info("[Database] PostGIS, pg_trgm, unaccent, GIN indexes & unified spatial views verified successfully.")

def generate_rs_key(nama_rs: str, kode_bps: Optional[str], kode_rs: Optional[str] = None) -> str:
    """
    Generate deterministic unique key for a hospital.
    If kode_rs is valid and not empty, use it. Otherwise, SHA256(nama_rs + kode_bps).
    """
    if kode_rs and str(kode_rs).strip() and str(kode_rs).strip() != "0":
        return str(kode_rs).strip()
    raw = f"{(nama_rs or '').strip().lower()}_{(kode_bps or '').strip()}"
    return f"gen_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

def upsert_rumah_sakit(session: Session, records: List[Dict[str, Any]]) -> int:
    """
    Idempotent bulk upsert for tbl_rumah_sakit.
    Uses PostgreSQL ON CONFLICT (kode_rs) DO UPDATE.
    """
    if not records:
        return 0

    inserted_or_updated = 0
    for r in records:
        lat_val = r.get("lat")
        lng_val = r.get("lng")
        has_valid_geom = (
            lat_val is not None and lng_val is not None and
            not (isinstance(lat_val, float) and math.isnan(lat_val)) and
            not (isinstance(lng_val, float) and math.isnan(lng_val))
        )
        geom_val = text(f"ST_SetSRID(ST_MakePoint({lng_val}, {lat_val}), 4326)") if has_valid_geom else None
        clean_lat = lat_val if has_valid_geom else None
        clean_lng = lng_val if has_valid_geom else None

        stmt = pg_insert(TblRumahSakit).values(
            kode_rs=r["kode_rs"],
            nama_rs=r["nama_rs"],
            alamat=r.get("alamat"),
            kode_bps=r.get("kode_bps"),
            kelas=r.get("kelas", EnumKelasRS.tidak_diketahui),
            kepemilikan=r.get("kepemilikan", EnumKepemilikan.lainnya),
            pemilik_raw=r.get("pemilik_raw"),
            jenis_rs=r.get("jenis_rs", "RSU"),
            jumlah_tt=r.get("jumlah_tt", 0),
            layanan=r.get("layanan", []),
            telepon=r.get("telepon"),
            website=r.get("website"),
            lat=clean_lat,
            lng=clean_lng,
            geom=geom_val,
            is_valid_coord=r.get("is_valid_coord", 1),
            needs_geocoding=r.get("needs_geocoding", 0),
            sumber_data=r.get("sumber_data", "SIRS Kemenkes"),
            coverage_periode=r.get("coverage_periode", "2026-LIVE"),
            last_updated_source=r.get("last_updated_source", datetime.utcnow()),
            updated_at=datetime.utcnow()
        )

        # Do Update on conflict
        stmt = stmt.on_conflict_do_update(
            index_elements=["kode_rs"],
            set_={
                "nama_rs": stmt.excluded.nama_rs,
                "alamat": stmt.excluded.alamat,
                "kode_bps": stmt.excluded.kode_bps,
                "kelas": stmt.excluded.kelas,
                "kepemilikan": stmt.excluded.kepemilikan,
                "pemilik_raw": stmt.excluded.pemilik_raw,
                "jenis_rs": stmt.excluded.jenis_rs,
                "jumlah_tt": stmt.excluded.jumlah_tt,
                "layanan": stmt.excluded.layanan,
                "telepon": stmt.excluded.telepon,
                "website": stmt.excluded.website,
                "lat": stmt.excluded.lat,
                "lng": stmt.excluded.lng,
                "geom": stmt.excluded.geom,
                "is_valid_coord": stmt.excluded.is_valid_coord,
                "needs_geocoding": stmt.excluded.needs_geocoding,
                "sumber_data": stmt.excluded.sumber_data,
                "last_updated_source": stmt.excluded.last_updated_source,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        inserted_or_updated += 1

    session.commit()
    logger.info(f"[Upsert] Processed {inserted_or_updated} hospital records idempotently.")
    return inserted_or_updated

def upsert_puskesmas(session: Session, records: List[Dict[str, Any]]) -> int:
    """
    Idempotent bulk upsert for faskes_puskesmas.
    Uses PostgreSQL ON CONFLICT (kode_puskesmas) DO UPDATE.
    """
    if not records:
        return 0

    count = 0
    for r in records:
        lat_val = r.get("lat")
        lng_val = r.get("lng")
        has_valid_geom = (
            lat_val is not None and lng_val is not None and
            not (isinstance(lat_val, float) and math.isnan(lat_val)) and
            not (isinstance(lng_val, float) and math.isnan(lng_val))
        )
        geom_val = text(f"ST_SetSRID(ST_MakePoint({lng_val}, {lat_val}), 4326)") if has_valid_geom else None
        clean_lat = lat_val if has_valid_geom else None
        clean_lng = lng_val if has_valid_geom else None

        stmt = pg_insert(FaskesPuskesmas).values(
            kode_puskesmas=r["kode_puskesmas"],
            nama=r["nama"],
            tipe_rawat=r.get("tipe_rawat", EnumTipeRawatPuskesmas.non_rawat_inap),
            alamat=r.get("alamat"),
            kode_bps=r.get("kode_bps"),
            kecamatan=r.get("kecamatan"),
            telepon=r.get("telepon"),
            jumlah_tt=r.get("jumlah_tt", 0),
            lat=clean_lat,
            lng=clean_lng,
            geom=geom_val,
            is_valid_coord=r.get("is_valid_coord", 1),
            needs_geocoding=r.get("needs_geocoding", 0),
            source_id=r.get("source_id", "opendata_jatim"),
            status_operasional=r.get("status_operasional", 1),
            coverage_periode=r.get("coverage_periode", "2024-OFFICIAL"),
            updated_at=datetime.utcnow()
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["kode_puskesmas"],
            set_={
                "nama": stmt.excluded.nama,
                "tipe_rawat": stmt.excluded.tipe_rawat,
                "alamat": stmt.excluded.alamat,
                "kode_bps": stmt.excluded.kode_bps,
                "kecamatan": stmt.excluded.kecamatan,
                "telepon": stmt.excluded.telepon,
                "jumlah_tt": stmt.excluded.jumlah_tt,
                "lat": stmt.excluded.lat,
                "lng": stmt.excluded.lng,
                "geom": stmt.excluded.geom,
                "is_valid_coord": stmt.excluded.is_valid_coord,
                "needs_geocoding": stmt.excluded.needs_geocoding,
                "source_id": stmt.excluded.source_id,
                "status_operasional": stmt.excluded.status_operasional,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} puskesmas records idempotently.")
    return count


def upsert_tenaga_kesehatan(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent bulk upsert for tbl_tenaga_kesehatan (Domain B)."""
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = pg_insert(TblTenagaKesehatan).values(
            kode_bps=r["kode_bps"],
            tahun=r.get("tahun", 2024),
            semester=r.get("semester", 1),
            jenis_nakes=r["jenis_nakes"],
            jumlah=r.get("jumlah", 0),
            faskes_level=r.get("faskes_level", "Semua Faskes"),
            sumber_data=r.get("sumber_data", "Dinas Kesehatan Provinsi Jawa Timur"),
            coverage_periode=r.get("coverage_periode", "2024-OFFICIAL"),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_nakes_wilayah_tahun",
            set_={
                "jumlah": stmt.excluded.jumlah,
                "sumber_data": stmt.excluded.sumber_data,
                "coverage_periode": stmt.excluded.coverage_periode,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} tenaga kesehatan records idempotently.")
    return count


def upsert_pasien_morbiditas(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent bulk upsert for tbl_pasien_penyakit_wilayah (Domain C)."""
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = pg_insert(TblPasienPenyakitWilayah).values(
            kode_bps=r["kode_bps"],
            tahun=r.get("tahun", 2024),
            triwulan=r.get("triwulan", "Q1"),
            tipe_pelayanan=r.get("tipe_pelayanan", EnumTipePelayanan.rawat_inap),
            nama_penyakit=r["nama_penyakit"],
            kode_icd10=r.get("kode_icd10"),
            jumlah_pasien=r.get("jumlah_pasien", 0),
            status_kasus=r.get("status_kasus", EnumStatusKasusPenyakit.menular),
            sumber_data=r.get("sumber_data", "Dinas Kesehatan Provinsi Jawa Timur"),
            coverage_periode=r.get("coverage_periode", "2024-OFFICIAL"),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_morbiditas_wilayah",
            set_={
                "jumlah_pasien": stmt.excluded.jumlah_pasien,
                "kode_icd10": stmt.excluded.kode_icd10,
                "status_kasus": stmt.excluded.status_kasus,
                "sumber_data": stmt.excluded.sumber_data,
                "coverage_periode": stmt.excluded.coverage_periode,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} pasien morbiditas records idempotently.")
    return count


def upsert_ref_sumber_data(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent upsert for ref_sumber_data."""
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = pg_insert(RefSumberData).values(
            source_id=r["source_id"],
            nama=r["nama"],
            institusi=r.get("institusi"),
            url=r.get("url"),
            lisensi=r.get("lisensi"),
            lisensi_url=r.get("lisensi_url"),
            cakupan_wilayah=r.get("cakupan_wilayah"),
            cakupan_periode=r.get("cakupan_periode"),
            format_asli=r.get("format_asli"),
            catatan_batasan=r.get("catatan_batasan"),
            frekuensi_update=r.get("frekuensi_update"),
            is_active=r.get("is_active", 1)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id"],
            set_={
                "nama": stmt.excluded.nama,
                "institusi": stmt.excluded.institusi,
                "url": stmt.excluded.url,
                "lisensi": stmt.excluded.lisensi,
                "lisensi_url": stmt.excluded.lisensi_url,
                "cakupan_wilayah": stmt.excluded.cakupan_wilayah,
                "cakupan_periode": stmt.excluded.cakupan_periode,
                "format_asli": stmt.excluded.format_asli,
                "catatan_batasan": stmt.excluded.catatan_batasan,
                "frekuensi_update": stmt.excluded.frekuensi_update,
                "is_active": stmt.excluded.is_active
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} ref_sumber_data records idempotently.")
    return count


def upsert_ref_icd10(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent upsert for ref_icd10."""
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = pg_insert(RefIcd10).values(
            kode=r["kode"],
            nama_en=r.get("nama_en"),
            nama_id=r.get("nama_id"),
            kategori=r.get("kategori"),
            is_active=r.get("is_active", 1)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["kode"],
            set_={
                "nama_en": stmt.excluded.nama_en,
                "nama_id": stmt.excluded.nama_id,
                "kategori": stmt.excluded.kategori,
                "is_active": stmt.excluded.is_active
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} ref_icd10 records idempotently.")
    return count


def upsert_ref_wilayah(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent upsert for 38 kab/kota reference."""
    if not records:
        return 0

    count = 0
    for r in records:
        geom_val = text(f"ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON('{r['geojson_geom']}'), 4326))") if r.get("geojson_geom") else None
        stmt = pg_insert(RefWilayah).values(
            kode_bps=r["kode_bps"],
            nama_wilayah=r["nama_wilayah"],
            tipe=r["tipe"],
            geom=geom_val
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["kode_bps"],
            set_={
                "nama_wilayah": stmt.excluded.nama_wilayah,
                "tipe": stmt.excluded.tipe,
                "geom": stmt.excluded.geom if geom_val is not None else RefWilayah.__table__.c.geom
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} ref_wilayah records idempotently.")
    return count

def upsert_indikator_kesehatan(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent upsert for tbl_indikator_kesehatan."""
    if not records:
        return 0

    from models import TblIndikatorKesehatan
    count = 0
    for r in records:
        stmt = pg_insert(TblIndikatorKesehatan).values(
            kode_bps=r["kode_bps"],
            tahun=r["tahun"],
            topik=r.get("topik", "Umum"),
            nama_indikator=r["nama_indikator"],
            nilai=r["nilai"],
            satuan=r.get("satuan", "Unit"),
            sumber_data=r.get("sumber_data", "Dinas Kesehatan Provinsi Jawa Timur"),
            coverage_periode=r.get("coverage_periode", "2024-OFFICIAL"),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_indikator_wilayah_tahun",
            set_={
                "nilai": stmt.excluded.nilai,
                "topik": stmt.excluded.topik,
                "satuan": stmt.excluded.satuan,
                "sumber_data": stmt.excluded.sumber_data,
                "coverage_periode": stmt.excluded.coverage_periode,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} tbl_indikator_kesehatan records idempotently.")
    return count

def upsert_penduduk(session: Session, records: List[Dict[str, Any]]) -> int:
    """Idempotent upsert for tbl_penduduk."""
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = pg_insert(TblPenduduk).values(
            kode_bps=r["kode_bps"],
            tahun=r.get("tahun", datetime.utcnow().year),
            jumlah_penduduk=r["jumlah_penduduk"],
            sumber=r.get("sumber", "SIRS / Disdukcapil / BPS")
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_wilayah_tahun",
            set_={
                "jumlah_penduduk": stmt.excluded.jumlah_penduduk,
                "sumber": stmt.excluded.sumber
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} tbl_penduduk records idempotently.")
    return count

def recompute_agregat_wilayah(session: Session, tahun: int = 2024, rasio_data_list: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Poin 4: Pre-compute aggregates per 38 Kab/Kota in tbl_agregat_wilayah.
    Calculates total RS from tbl_rumah_sakit, joins population from tbl_penduduk or rasio_tt dataset,
    and updates tbl_agregat_wilayah for sub-second dashboard query.
    """
    # 1. Calculate count of RS grouped by kode_bps
    rs_count_query = text("""
        SELECT kode_bps, COUNT(id) as total_rs
        FROM tbl_rumah_sakit
        WHERE kode_bps IS NOT NULL
        GROUP BY kode_bps;
    """)
    rs_counts = {row[0]: row[1] for row in session.execute(rs_count_query).fetchall()}

    # 2. Get all ref_wilayah
    wilayah_list = session.query(RefWilayah).all()
    if not wilayah_list:
        logger.warning("[Aggregate] ref_wilayah is empty. Skipping aggregate calculation.")
        return 0

    # Build map from rasio_data_list if provided (from SIRS rasio_tt endpoint)
    sirs_rasio_map = {}
    if rasio_data_list:
        for it in rasio_data_list:
            kbps = str(it.get("kode", "")).strip()
            if kbps:
                sirs_rasio_map[kbps] = it

    processed_count = 0
    for w in wilayah_list:
        kbps = w.kode_bps
        tot_rs = rs_counts.get(kbps, 0)
        
        # Check SIRS rasio data
        s_data = sirs_rasio_map.get(kbps, {})
        tot_tt = s_data.get("jumlah_tt", 0)
        pddk = s_data.get("penduduk", 0)
        rasio = s_data.get("bed_per_1000", 0.0)
        kategori = s_data.get("kategori", "kuning")

        # Fallback to tbl_penduduk if sirs population is 0
        if pddk == 0:
            penduduk_rec = session.query(TblPenduduk).filter_by(kode_bps=kbps, tahun=tahun).first()
            if penduduk_rec:
                pddk = penduduk_rec.jumlah_penduduk
                if pddk > 0 and tot_tt > 0:
                    rasio = round((tot_tt / pddk) * 1000, 2)

        stmt = pg_insert(TblAgregatWilayah).values(
            kode_bps=kbps,
            tahun=tahun,
            total_rs=tot_rs,
            total_tt=tot_tt,
            jumlah_penduduk=pddk,
            rasio_tt_per_1000=rasio,
            kategori_ketercukupan=kategori,
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_agregat_wilayah_tahun",
            set_={
                "total_rs": stmt.excluded.total_rs,
                "total_tt": stmt.excluded.total_tt,
                "jumlah_penduduk": stmt.excluded.jumlah_penduduk,
                "rasio_tt_per_1000": stmt.excluded.rasio_tt_per_1000,
                "kategori_ketercukupan": stmt.excluded.kategori_ketercukupan,
                "updated_at": datetime.utcnow()
            }
        )
        session.execute(stmt)
        processed_count += 1

    session.commit()
    logger.info(f"[Aggregate] Pre-computed aggregate stats for {processed_count} Kab/Kota (Year: {tahun}).")
    return processed_count
