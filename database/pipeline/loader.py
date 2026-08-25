import hashlib
import logging
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
    logger.info("[Database] PostGIS extension verified & all tables initialized successfully.")

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
            lat=r.get("lat"),
            lng=r.get("lng"),
            geom=text(f"ST_SetSRID(ST_MakePoint({r['lng']}, {r['lat']}), 4326)") if r.get("lat") and r.get("lng") else None,
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
        geom_val = text(f"ST_SetSRID(ST_GeomFromGeoJSON('{r['geojson_geom']}'), 4326)") if r.get("geojson_geom") else None
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
                "geom": stmt.excluded.geom if geom_val is not None else RefWilayah.geom
            }
        )
        session.execute(stmt)
        count += 1

    session.commit()
    logger.info(f"[Upsert] Processed {count} ref_wilayah records idempotently.")
    return count
