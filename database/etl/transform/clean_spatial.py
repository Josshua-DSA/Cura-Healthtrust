import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

logger = logging.getLogger("CleanSpatial")

def clean_and_validate_districts(geojson_raw: Optional[Dict[str, Any]], rasio_tt_raw: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """
    Validate 38 East Java districts polygon & generate standardized bed ratio dataframe.
    Falls back to local static seed if live geojson is empty.
    """
    # Fallback to local seed if live geojson has no features
    features = geojson_raw.get("features", []) if geojson_raw else []
    if not features:
        seed_geojson_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "seeds", "jatim_districts.geojson")
        if os.path.exists(seed_geojson_path):
            try:
                with open(seed_geojson_path, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
                    features = seed_data.get("features", [])
                    logger.info(f"[CleanSpatial] Using fallback static seed from {seed_geojson_path} ({len(features)} features)")
            except Exception as e:
                logger.warning(f"[CleanSpatial] Failed loading fallback seed geojson: {e}")

    # Fallback to local ref_wilayah CSV if still empty
    if not features:
        seed_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "seeds", "ref_wilayah_jatim.csv")
        if os.path.exists(seed_csv_path):
            df_seed = pd.read_csv(seed_csv_path)
            features = [
                {
                    "properties": {
                        "KODE_BPS": str(row["kode_bps"]),
                        "PROVINSI": row["nama_wilayah"],
                        "jumlah_penduduk": 0
                    },
                    "geometry": None
                }
                for _, row in df_seed.iterrows()
            ]

    rasio_map = {}
    if rasio_tt_raw and "wilayah" in rasio_tt_raw:
        for it in rasio_tt_raw["wilayah"]:
            kbps = str(it.get("kode", "")).strip()
            if kbps:
                rasio_map[kbps] = it

    district_records = []
    ratio_rows = []

    for feat in features:
        props = feat.get("properties", {})
        kbps = str(props.get("KODE_BPS") or props.get("ID2013", "")).strip()
        nama = props.get("PROVINSI", "")
        geom_obj = feat.get("geometry")
        geom_json = json.dumps(geom_obj) if geom_obj else None

        if not kbps:
            continue

        r_info = rasio_map.get(kbps, {})
        tot_tt = int(r_info.get("jumlah_tt", 0))
        pddk_2021 = int(r_info.get("penduduk", props.get("jumlah_penduduk", 0)))
        rasio_resmi = float(r_info.get("bed_per_1000", 0.0))
        kategori_resmi = str(r_info.get("kategori", "kuning"))

        # Point 1 Optimization: BPS East Java Population Projection (2021 -> 2026 with ~0.7%/year growth)
        # Formula: P_2026 = P_2021 * (1 + 0.007)^5 = P_2021 * 1.03549
        pddk_proyeksi_2026 = int(round(pddk_2021 * 1.03549)) if pddk_2021 > 0 else 0
        rasio_proyeksi_2026 = round((tot_tt / pddk_proyeksi_2026) * 1000.0, 2) if pddk_proyeksi_2026 > 0 else rasio_resmi
        
        # Determine Projected WHO Category
        if rasio_proyeksi_2026 >= 1.0:
            kategori_proyeksi_2026 = "hijau"
        elif rasio_proyeksi_2026 >= 0.7:
            kategori_proyeksi_2026 = "kuning"
        else:
            kategori_proyeksi_2026 = "merah"

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
            "jumlah_penduduk_2021": pddk_2021,
            "rasio_tt_resmi": rasio_resmi,
            "kategori_who_resmi": kategori_resmi,
            "proyeksi_penduduk_2026": pddk_proyeksi_2026,
            "rasio_tt_proyeksi_2026": rasio_proyeksi_2026,
            "kategori_who_proyeksi_2026": kategori_proyeksi_2026,
            "coverage_periode": "2026-PROJECTED"
        })

    df_ratio = pd.DataFrame(ratio_rows)
    return district_records, df_ratio
