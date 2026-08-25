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
    Base, RefWilayah, TblRumahSakit, TblPenduduk, TblAgregatWilayah,
    TblPipelineLog, EnumKelasRS, EnumKepemilikan, EnumTipeWilayah, EnumPipelineStatus
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
        conn.commit()
    Base.metadata.create_all(engine)

    # Ensure GIST indexes for spatial performance
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_rs_geom ON tbl_rumah_sakit USING GIST (geom);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_wilayah_geom ON ref_wilayah USING GIST (geom);"))
        conn.commit()

    logger.info("[Database] PostGIS extension & GIST spatial indexes verified successfully.")

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
            jenis_rs=r.get("jenis_rs", "RSU"),
            jumlah_tt=r.get("jumlah_tt", 0),
            layanan=r.get("layanan", []),
            telepon=r.get("telepon"),
            website=r.get("website"),
            lat=clean_lat,
            lng=clean_lng,
            geom=geom_val,
            sumber_data=r.get("sumber_data", "SIRS Kemenkes"),
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
                "jenis_rs": stmt.excluded.jenis_rs,
                "jumlah_tt": stmt.excluded.jumlah_tt,
                "layanan": stmt.excluded.layanan,
                "telepon": stmt.excluded.telepon,
                "website": stmt.excluded.website,
                "lat": stmt.excluded.lat,
                "lng": stmt.excluded.lng,
                "geom": stmt.excluded.geom,
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
            sumber_file=r.get("sumber_file"),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_indikator_wilayah_tahun",
            set_={
                "nilai": stmt.excluded.nilai,
                "topik": stmt.excluded.topik,
                "satuan": stmt.excluded.satuan,
                "sumber_file": stmt.excluded.sumber_file,
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
