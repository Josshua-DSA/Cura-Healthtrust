import os
import sys
import logging
import requests
from typing import Dict, Any, Optional, Tuple

from pipeline.storage import save_raw_snapshot, load_latest_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DataFetcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (HealthTrust Pipeline; Linux x86_64) AppleWebKit/537.36"
}

def fetch_sirs_data_rs() -> Tuple[Dict[str, Any], bool]:
    """
    Fetch 447+ RS list and coordinates in East Java.
    Returns: (data_dict, is_live_fetch)
    """
    source_id = "sirs_kemenkes_list"
    url = "https://sirs.kemkes.go.id/fo/home/list_prop_noncovid?id=35"
    try:
        logger.info(f"Fetching live data from {url} ...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        save_raw_snapshot(source_id, data, extension="json")
        return data, True
    except Exception as e:
        logger.warning(f"Live fetch failed for '{source_id}': {e}. Attempting fallback...")
        fallback_data, path = load_latest_snapshot(source_id, extension="json")
        if fallback_data is not None:
            return fallback_data, False
        raise RuntimeError(f"Failed to fetch live data and no local snapshot available for {source_id}")

def fetch_sirs_rekap_rs() -> Tuple[Dict[str, Any], bool]:
    """
    Fetch ownership and details of RS in East Java.
    Returns: (data_dict, is_live_fetch)
    """
    source_id = "sirs_kemenkes_rekap"
    url = "https://sirs.kemkes.go.id/fo/home/rekap_rs_all?id=35"
    try:
        logger.info(f"Fetching live data from {url} ...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        save_raw_snapshot(source_id, data, extension="json")
        return data, True
    except Exception as e:
        logger.warning(f"Live fetch failed for '{source_id}': {e}. Attempting fallback...")
        fallback_data, path = load_latest_snapshot(source_id, extension="json")
        if fallback_data is not None:
            return fallback_data, False
        raise RuntimeError(f"Failed to fetch live data and no local snapshot available for {source_id}")

def fetch_sirs_rasio_tt() -> Tuple[Dict[str, Any], bool]:
    """
    Fetch bed capacity and ratio per 1000 population per 38 Kab/Kota.
    Returns: (data_dict, is_live_fetch)
    """
    source_id = "sirs_kemenkes_rasio_tt"
    url = "https://sirs.kemkes.go.id/fo/mapgeo/rasio_tt?id=35"
    try:
        logger.info(f"Fetching live data from {url} ...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        save_raw_snapshot(source_id, data, extension="json")
        return data, True
    except Exception as e:
        logger.warning(f"Live fetch failed for '{source_id}': {e}. Attempting fallback...")
        fallback_data, path = load_latest_snapshot(source_id, extension="json")
        if fallback_data is not None:
            return fallback_data, False
        raise RuntimeError(f"Failed to fetch live data and no local snapshot available for {source_id}")

def fetch_sirs_geojson() -> Tuple[Dict[str, Any], bool]:
    """
    Fetch GeoJSON boundaries & BPS codes for 38 Kab/Kota in East Java.
    Returns: (data_dict, is_live_fetch)
    """
    source_id = "sirs_kemenkes_geojson"
    url = "https://sirs.kemkes.go.id/fo/mapgeo/koordinat?id=35&mapfile=json%2Fprovinsi.json"
    try:
        logger.info(f"Fetching live data from {url} ...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        save_raw_snapshot(source_id, data, extension="json")
        return data, True
    except Exception as e:
        logger.warning(f"Live fetch failed for '{source_id}': {e}. Attempting fallback...")
        fallback_data, path = load_latest_snapshot(source_id, extension="json")
        if fallback_data is not None:
            return fallback_data, False
        raise RuntimeError(f"Failed to fetch live data and no local snapshot available for {source_id}")

def fetch_all_sources() -> Dict[str, Any]:
    """Fetch all primary datasets and return consolidated dict."""
    logger.info("=" * 60)
    logger.info(" [HealthTrust Pipeline] Ingesting All Sources to Raw Storage")
    logger.info("=" * 60)
    
    results = {}
    
    # 1. RS List & Koordinat
    rs_list, live1 = fetch_sirs_data_rs()
    results["rs_list"] = {"count": len(rs_list.get("rs", [])), "is_live": live1}
    
    # 2. Rekap RS (Pemilik)
    rekap_rs, live2 = fetch_sirs_rekap_rs()
    results["rekap_rs"] = {"count": len(rekap_rs.get("data", [])), "is_live": live2}
    
    # 3. Rasio TT & Wilayah
    rasio_tt, live3 = fetch_sirs_rasio_tt()
    results["rasio_tt"] = {"count": len(rasio_tt.get("wilayah", [])), "is_live": live3}
    
    # 4. GeoJSON Batas Wilayah
    geojson_data, live4 = fetch_sirs_geojson()
    results["geojson"] = {"count": len(geojson_data.get("features", [])), "is_live": live4}
    
    logger.info("=" * 60)
    logger.info(f" Ingestion Summary: {results}")
    logger.info("=" * 60)
    return results

if __name__ == "__main__":
    fetch_all_sources()
