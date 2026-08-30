import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import requests

from pipeline.cleaner import sanitize_coordinates

logger = logging.getLogger("Geocoder")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "CuraHealthTrust-DataPipeline/3.0 (healthtrust@local.dev)"}

def geocode_address_osm(query_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Query OpenStreetMap Nominatim API for coordinates.
    Returns: (lat, lng) or (None, None)
    """
    if not query_str or len(query_str.strip()) < 4:
        return None, None

    params = {
        "q": query_str,
        "format": "json",
        "limit": 1,
        "countrycodes": "id"
    }

    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                return lat, lng
    except Exception as e:
        logger.debug(f"[Geocoder] Nominatim query failed for '{query_str}': {e}")

    return None, None

def enrich_unmapped_hospitals(hospital_records: List[Dict[str, Any]], max_lookups: int = 5) -> List[Dict[str, Any]]:
    """
    Try geocoding for hospitals marked as needs_geocoding == 1.
    Rate limited with 1s sleep per Nominatim TOS.
    """
    geocoded_count = 0
    skipped_count = 0
    for r in hospital_records:
        if r.get("needs_geocoding") == 1 and geocoded_count < max_lookups:
            nama = r.get("nama_rs", "")
            alamat = r.get("alamat", "")
            
            # Construct query: e.g. "RS Wijaya Surabaya, Jawa Timur"
            clean_nama = re.sub(r'\(.*?\)', '', nama).strip()
            query = f"{clean_nama}, Jawa Timur"

            lat_raw, lng_raw = geocode_address_osm(query)
            if not lat_raw and alamat:
                # Fallback to address query
                query_addr = f"{alamat}, Jawa Timur"
                lat_raw, lng_raw = geocode_address_osm(query_addr)

            if lat_raw and lng_raw:
                lat, lng, is_valid, needs_gc = sanitize_coordinates(lat_raw, lng_raw)
                if is_valid:
                    r["lat"] = lat
                    r["lng"] = lng
                    r["is_valid_coord"] = 1
                    r["needs_geocoding"] = 0
                    geocoded_count += 1
                    logger.info(f"[Geocoder] Successfully resolved coordinates for {nama} -> ({lat}, {lng})")
            else:
                skipped_count += 1
            
            time.sleep(1.0) # Respect OSM Nominatim 1 req/sec policy

    logger.info(f"[Geocoder] Enrichment completed. Resolved: {geocoded_count}, Unresolved: {skipped_count}.")
    return hospital_records


def geocode_pending_from_db(max_lookups: int = 50) -> Dict[str, Any]:
    """
    Standalone batch geocoder: reads needs_geocoding=1 from PostGIS,
    resolves via Nominatim, updates DB in-place, and regenerates exports.
    """
    from pipeline.loader import get_session, get_engine
    from models import TblRumahSakit
    from sqlalchemy import text
    import pandas as pd
    import os

    session = get_session()
    pending = session.query(TblRumahSakit).filter(TblRumahSakit.needs_geocoding == 1).all()
    logger.info(f"[Geocoder] Found {len(pending)} hospitals pending geocoding.")

    resolved = 0
    for i, rs in enumerate(pending):
        if resolved >= max_lookups:
            break

        clean_nama = re.sub(r'\(.*?\)', '', rs.nama_rs or "").strip()
        query = f"{clean_nama}, Jawa Timur"

        lat_raw, lng_raw = geocode_address_osm(query)
        if not lat_raw and rs.alamat:
            query_addr = f"{rs.alamat}, Jawa Timur"
            lat_raw, lng_raw = geocode_address_osm(query_addr)

        if lat_raw and lng_raw:
            lat, lng, is_valid, _ = sanitize_coordinates(lat_raw, lng_raw)
            if is_valid:
                rs.lat = lat
                rs.lng = lng
                rs.is_valid_coord = 1
                rs.needs_geocoding = 0
                geom_sql = text(f"ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)")
                session.execute(
                    text(f"UPDATE tbl_rumah_sakit SET lat={lat}, lng={lng}, is_valid_coord=1, needs_geocoding=0, geom=ST_SetSRID(ST_MakePoint({lng},{lat}),4326) WHERE kode_rs=:kode"),
                    {"kode": rs.kode_rs}
                )
                session.commit()
                resolved += 1
                logger.info(f"[Geocoder] [{resolved}/{len(pending)}] {rs.nama_rs} -> ({lat}, {lng})")

        time.sleep(1.0)

    # Regenerate export after batch update
    if resolved > 0:
        engine = get_engine()
        df_rs = pd.read_sql("SELECT * FROM tbl_rumah_sakit ORDER BY kode_rs", engine)
        exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(exports_dir, exist_ok=True)
        df_rs.to_csv(os.path.join(exports_dir, "hospitals_clean.csv"), index=False)
        try:
            df_rs.to_parquet(os.path.join(exports_dir, "hospitals_clean.parquet"), index=False)
        except Exception:
            pass
        logger.info(f"[Geocoder] Regenerated exports with {resolved} newly geocoded hospitals.")

    session.close()
    remaining = len(pending) - resolved
    logger.info(f"[Geocoder] Batch complete. Resolved: {resolved}, Still pending: {remaining}.")
    return {"resolved": resolved, "remaining": remaining}
