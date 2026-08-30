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
            
            time.sleep(1.0) # Respect OSM Nominatim 1 req/sec policy

    logger.info(f"[Geocoder] Enrichment completed. Successfully resolved {geocoded_count} hospital locations.")
    return hospital_records
