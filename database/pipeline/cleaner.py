import re
import math
import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from models import EnumKelasRS, EnumKepemilikan

logger = logging.getLogger("DataCleaner")

# Bounding Box Jawa Timur Resmi
JATIM_LAT_MIN = -8.8
JATIM_LAT_MAX = -6.7
JATIM_LNG_MIN = 110.9
JATIM_LNG_MAX = 114.4

# Dummy Kemenkes Coordinates (Default Laut Bangka Belitung)
DUMMY_LAT = -2.4185588
DUMMY_LNG = 108.4919086

def normalize_text_clean(text_val: Optional[str]) -> Optional[str]:
    """Clean newlines, tabs, and multiple spaces."""
    if not text_val or pd.isna(text_val):
        return None
    cleaned = str(text_val).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else None

def normalize_telepon(phone_val: Optional[str]) -> Optional[str]:
    """Remove trailing underscores, extra spaces, and invalid chars."""
    if not phone_val or pd.isna(phone_val):
        return None
    cleaned = str(phone_val).replace("\r\n", "").replace("\n", "").strip()
    cleaned = cleaned.rstrip("_").rstrip("-").strip()
    cleaned = re.sub(r'[^0-9+\-/\s,()]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else None

def normalize_nama_rs(nama_val: str) -> str:
    """Clean and standardize hospital name."""
    if not nama_val or pd.isna(nama_val):
        return "RS Tanpa Nama"
    cleaned = normalize_text_clean(nama_val) or "RS Tanpa Nama"
    # Ensure no leading/trailing weird symbols
    return cleaned.strip()

def sanitize_coordinates(lat_raw: Any, lng_raw: Any) -> Tuple[Optional[float], Optional[float], bool]:
    """
    Apply Action Plan Rules for Spatial Coordinates:
    1. Check Dummy Kemenkes [-2.4185588, 108.4919086] -> Set NULL
    2. Check Swapped Lat/Lng (if lat > lng) -> Swap back
    3. Check Bounding Box Jatim (lat: -8.8 s/d -6.7, lng: 110.9 s/d 114.4)
    Returns: (lat, lng, is_valid_coord)
    """
    if lat_raw is None or lng_raw is None:
        return None, None, False

    try:
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (ValueError, TypeError):
        return None, None, False

    if math.isnan(lat) or math.isnan(lng):
        return None, None, False

    # Rule 1: Check Dummy Kemenkes Coordinate
    if abs(lat - DUMMY_LAT) < 0.001 and abs(lng - DUMMY_LNG) < 0.001:
        return None, None, False

    # Rule 2: Check Swapped Lat / Lng (e.g. [111.90, -8.06])
    if lat > lng:
        lat, lng = lng, lat

    # Rule 3: Check Bounding Box Jawa Timur
    is_valid = (JATIM_LAT_MIN <= lat <= JATIM_LAT_MAX) and (JATIM_LNG_MIN <= lng <= JATIM_LNG_MAX)
    if not is_valid:
        return None, None, False

    return round(lat, 6), round(lng, 6), True

def normalize_kelas(kelas_raw: Optional[str]) -> str:
    """Normalize kelas to EnumKelasRS."""
    if not kelas_raw or pd.isna(kelas_raw):
        return EnumKelasRS.tidak_diketahui.value
    k = str(kelas_raw).strip().upper()
    if k in ["A", "B", "C", "D"]:
        return k
    return EnumKelasRS.tidak_diketahui.value

def normalize_kepemilikan(pemilik_raw: Optional[str]) -> str:
    """Normalize ownership to EnumKepemilikan."""
    if not pemilik_raw or pd.isna(pemilik_raw):
        return EnumKepemilikan.lainnya.value
    p = str(pemilik_raw).strip().lower()
    if any(x in p for x in ["pemkab", "pemkot", "pemprop", "kemkes", "kementerian", "pemerintah"]):
        return EnumKepemilikan.pemerintah.value
    if any(x in p for x in ["tni", "polri", "bhayangkara"]):
        return EnumKepemilikan.tni_polri.value
    if any(x in p for x in ["swasta", "perusahaan", "perorangan", "pt"]):
        return EnumKepemilikan.swasta.value
    return EnumKepemilikan.lainnya.value

def extract_kode_bps_from_kode_rs(kode_rs: str) -> Optional[str]:
    """Map first 4 digits of SIRS code to BPS Jatim code (3501 - 3579)."""
    if not kode_rs or pd.isna(kode_rs):
        return None
    code_str = str(kode_rs).strip()
    if len(code_str) >= 4 and code_str.startswith("35"):
        bps_candidate = code_str[:4]
        if bps_candidate.isdigit() and (3501 <= int(bps_candidate) <= 3579):
            return bps_candidate
    return None

class CleanHospitalSchema(pa.DataFrameModel):
    kode_rs: Series[str] = pa.Field(unique=True, nullable=False)
    nama_rs: Series[str] = pa.Field(nullable=False)
    alamat: Series[str] = pa.Field(nullable=True)
    telepon: Series[str] = pa.Field(nullable=True)
    kode_bps: Series[str] = pa.Field(nullable=True)
    kelas: Series[str] = pa.Field(isin=["A", "B", "C", "D", "tidak_diketahui"])
    kepemilikan: Series[str] = pa.Field(isin=["pemerintah", "swasta", "tni_polri", "lainnya"])
    jenis_rs: Series[str] = pa.Field(nullable=False)
    lat: Series[float] = pa.Field(nullable=True)
    lng: Series[float] = pa.Field(nullable=True)
    is_valid_coord: Series[bool] = pa.Field(nullable=False)
    sumber_data: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = True
        coerce = True

def clean_and_validate_hospitals(raw_rs_list: List[Dict[str, Any]], raw_rekap_list: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
    """
    Orchestrate full cleaning & validation with quality gates.
    """
    rekap_map = {}
    if raw_rekap_list:
        for r in raw_rekap_list:
            kode = str(r.get("kode", "")).strip()
            if kode:
                rekap_map[kode] = r

    cleaned_rows = []
    for it in raw_rs_list:
        kode_rs = str(it.get("kode", "")).strip()
        if not kode_rs:
            continue

        rekap_info = rekap_map.get(kode_rs, {})
        nama_rs = normalize_nama_rs(it.get("nama") or rekap_info.get("nama", "RS Tanpa Nama"))
        alamat = normalize_text_clean(it.get("alamat") or rekap_info.get("alamat"))
        telepon = normalize_telepon(it.get("TELEPON") or it.get("telepon") or rekap_info.get("TELEPON"))
        kelas = normalize_kelas(it.get("kelas") or rekap_info.get("kelas"))
        kepemilikan = normalize_kepemilikan(rekap_info.get("pemilik") or it.get("pemilik"))
        jenis_rs = normalize_text_clean(it.get("jenis") or rekap_info.get("jenis")) or "RSU"
        
        # Coordinate handling
        coords = it.get("koordinat", [])
        lat_raw = coords[0] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else it.get("lat")
        lng_raw = coords[1] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else it.get("lng")
        lat, lng, is_valid_coord = sanitize_coordinates(lat_raw, lng_raw)

        kode_bps = extract_kode_bps_from_kode_rs(kode_rs)

        cleaned_rows.append({
            "kode_rs": kode_rs,
            "nama_rs": nama_rs,
            "alamat": alamat,
            "telepon": telepon,
            "kode_bps": kode_bps,
            "kelas": kelas,
            "kepemilikan": kepemilikan,
            "jenis_rs": jenis_rs,
            "lat": lat,
            "lng": lng,
            "is_valid_coord": is_valid_coord,
            "sumber_data": "SIRS Kemenkes"
        })

    df = pd.DataFrame(cleaned_rows)
    df_validated = CleanHospitalSchema.validate(df)
    logger.info(f"[Validation] Successfully validated {len(df_validated)} hospital records with Pandera.")
    return df_validated
