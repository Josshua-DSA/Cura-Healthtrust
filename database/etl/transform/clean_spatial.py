import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

logger = logging.getLogger("CleanSpatial")

def clean_and_validate_districts(geojson_raw: Optional[Dict[str, Any]], rasio_tt_raw: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """
    Validate 38 East Java districts polygon & generate standardized bed ratio dataframe.
    """
    rasio_map = {}
    if rasio_tt_raw and "wilayah" in rasio_tt_raw:
        for it in rasio_tt_raw["wilayah"]:
            kbps = str(it.get("kode", "")).strip()
            if kbps:
                rasio_map[kbps] = it

    district_records = []
    ratio_rows = []

    features = geojson_raw.get("features", []) if geojson_raw else []
    for feat in features:
        props = feat.get("properties", {})
        kbps = str(props.get("KODE_BPS") or props.get("ID2013", "")).strip()
        nama = props.get("PROVINSI", "")
        geom_json = json.dumps(feat.get("geometry", {}))

        if not kbps:
            continue

        r_info = rasio_map.get(kbps, {})
        tot_tt = int(r_info.get("jumlah_tt", 0))
        pddk = int(r_info.get("penduduk", props.get("jumlah_penduduk", 0)))
        rasio = float(r_info.get("bed_per_1000", 0.0))
        kategori = str(r_info.get("kategori", "kuning"))

        tipe = "KOTA" if "kota" in nama.lower() else "KABUPATEN"
        nama_std = f"Kabupaten {nama}" if tipe == "KABUPATEN" and not nama.lower().startswith("kab") else (f"Kota {nama}" if tipe == "KOTA" and not nama.lower().startswith("kota") else nama)

        district_records.append({
            "kode_bps": kbps,
            "nama_wilayah": nama_std,
            "tipe": tipe,
            "geojson_geom": geom_json
        })

        ratio_rows.append({
            "kode_bps": kbps,
            "nama_wilayah": nama_std,
            "total_tt": tot_tt,
            "jumlah_penduduk": pddk,
            "rasio_tt_per_1000": rasio,
            "kategori_who": kategori
        })

    df_ratio = pd.DataFrame(ratio_rows)
    return district_records, df_ratio
