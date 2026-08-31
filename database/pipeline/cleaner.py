"""
Hospital Data Cleaner — OOP class + legacy functions sesuai RULES.md Seksi 2.3.
Backward-compatible: fungsi legacy dan CleanHospitalSchema tetap tersedia.
"""

import re
import math
import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from models import EnumKelasRS, EnumKepemilikan
from pipeline.clean.base_cleaner import BaseCleaner
from exceptions import ValidationError

logger = logging.getLogger("DataCleaner")

# Bounding Box Jawa Timur + Pulau Bawean + Kepulauan Kangean (v3.0)
JATIM_LAT_MIN = -8.8
JATIM_LAT_MAX = -5.7
JATIM_LNG_MIN = 110.9
JATIM_LNG_MAX = 116.6

# Dummy Kemenkes Coordinates (Default Laut Bangka Belitung)
DUMMY_LAT = -2.4185588
DUMMY_LNG = 108.4919086


# ─── Standalone Helper Functions (dipakai tests & cleaner) ─────────


def normalize_text_clean(text_val: Optional[str]) -> Optional[str]:
    """Clean newlines, tabs, and multiple spaces."""
    if not text_val or pd.isna(text_val):
        return None
    cleaned = str(text_val).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else None


def normalize_telepon(phone_val: Optional[str]) -> Optional[str]:
    """Remove trailing underscores, extra spaces. Preserve masking **** from source."""
    if not phone_val or pd.isna(phone_val):
        return None
    cleaned = str(phone_val).replace("\r\n", "").replace("\n", "").replace("\r", "").strip()
    cleaned = cleaned.rstrip("_").rstrip("-").strip()
    cleaned = re.sub(r'[^0-9+\-/\s,()*]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else None


def normalize_nama_rs(nama_val: Optional[str]) -> str:
    """Clean and standardize hospital name."""
    if not nama_val or pd.isna(nama_val):
        return "RS Tanpa Nama"
    cleaned = normalize_text_clean(nama_val) or "RS Tanpa Nama"
    return cleaned.strip()


def sanitize_coordinates(lat_raw: Any, lng_raw: Any) -> Tuple[Optional[float], Optional[float], bool, bool]:
    """
    Apply Action Plan v3.0 Rules for Spatial Coordinates:
    1. Check Dummy Kemenkes [-2.4185588, 108.4919086] -> Set NULL, needs_geocoding=True
    2. Check Swapped Lat/Lng (if lat > lng) -> Swap back
    3. Check Expanded Bounding Box Jatim (lat: -8.8 s/d -5.7, lng: 110.9 s/d 116.6)
    Returns: (lat, lng, is_valid_coord, needs_geocoding)
    """
    if lat_raw is None or lng_raw is None:
        return None, None, False, True

    try:
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (ValueError, TypeError):
        return None, None, False, True

    if math.isnan(lat) or math.isnan(lng):
        return None, None, False, True

    # Rule 1: Check Dummy Kemenkes Coordinate
    if abs(lat - DUMMY_LAT) < 0.001 and abs(lng - DUMMY_LNG) < 0.001:
        return None, None, False, True

    # Rule 2: Check Swapped Lat / Lng (e.g. [111.90, -8.06])
    if lat > lng:
        lat, lng = lng, lat

    # Rule 3: Check Expanded Bounding Box Jawa Timur + Pulau Terluar
    is_valid = (JATIM_LAT_MIN <= lat <= JATIM_LAT_MAX) and (JATIM_LNG_MIN <= lng <= JATIM_LNG_MAX)
    if not is_valid:
        return None, None, False, True

    return round(lat, 6), round(lng, 6), True, False


def normalize_kelas(kelas_raw: Optional[str]) -> str:
    """Normalize kelas to EnumKelasRS."""
    if not kelas_raw or pd.isna(kelas_raw):
        return EnumKelasRS.tidak_diketahui.value
    k = str(kelas_raw).strip().upper()
    if k in ["A", "B", "C", "D"]:
        return k
    return EnumKelasRS.tidak_diketahui.value


def normalize_kepemilikan(pemilik_raw: Optional[str]) -> str:
    """
    Normalize 17 SIRS ownership categories to 4 PostgreSQL enums:
    - pemerintah: Pemprop, Pemkab, Pemkot, Kemkes, Kementerian Lain, BUMN
    - swasta: SWASTA/LAINNYA, Perusahaan, Organisasi Islam/Katholik/Protestan/Sosial, Perorangan
    - tni_polri: TNI AD, TNI AL, TNI AU, POLRI
    - lainnya: fallback
    """
    if not pemilik_raw or pd.isna(pemilik_raw):
        return EnumKepemilikan.lainnya.value
    p = str(pemilik_raw).strip().lower()
    if any(x in p for x in ["pemkab", "pemkot", "pemprop", "kemkes", "kementerian", "pemerintah", "bumn"]):
        return EnumKepemilikan.pemerintah.value
    if any(x in p for x in ["tni", "polri", "bhayangkara"]):
        return EnumKepemilikan.tni_polri.value
    if any(x in p for x in ["swasta", "perusahaan", "perorangan", "pt", "organisasi"]):
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


# ─── Pandera Validation Schema ────────────────────────────────────


class CleanHospitalSchema(pa_pd.DataFrameModel):
    kode_rs: Series[str] = pa.Field(unique=True, nullable=False)
    nama_rs: Series[str] = pa.Field(nullable=False)
    alamat: Series[str] = pa.Field(nullable=True)
    telepon: Series[str] = pa.Field(nullable=True)
    kode_bps: Series[str] = pa.Field(nullable=True)
    kelas: Series[str] = pa.Field(isin=["A", "B", "C", "D", "tidak_diketahui"])
    kepemilikan: Series[str] = pa.Field(isin=["pemerintah", "swasta", "tni_polri", "lainnya"])
    pemilik_raw: Series[str] = pa.Field(nullable=True)
    jenis_rs: Series[str] = pa.Field(nullable=False)
    lat: Series[float] = pa.Field(nullable=True)
    lng: Series[float] = pa.Field(nullable=True)
    is_valid_coord: Series[int] = pa.Field(isin=[0, 1])
    needs_geocoding: Series[int] = pa.Field(isin=[0, 1])
    sumber_data: Series[str] = pa.Field(nullable=False)
    coverage_periode: Series[str] = pa.Field(eq="2026-LIVE")

    class Config:
        strict = True
        coerce = True


# ─── OOP Cleaner Class ────────────────────────────────────────────


class RumahSakitCleaner(BaseCleaner):
    """
    Cleaner class untuk data Rumah Sakit SIRS Kemenkes.
    Sesuai RULES.md Seksi 2.3: validate_raw → transform → validate_output.
    """

    @property
    def schema_input(self) -> None:
        """Raw data dari SIRS tidak punya schema ketat — skip validasi input."""
        return None

    @property
    def schema_output(self) -> None:
        """Output divalidasi via CleanHospitalSchema di dalam transform."""
        return None

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tidak digunakan langsung — gunakan clean_records() untuk raw dict list."""
        return df

    def clean_records(
        self,
        raw_rs_list: List[Dict[str, Any]],
        raw_rekap_list: Optional[List[Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Orchestrate full cleaning & validation with quality gates (Action Plan v3.0).
        Join sirs_kemenkes_list (447 RS) + sirs_kemenkes_rekap (449 RS) on kode_rs.
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

            pemilik_raw_val = str(rekap_info.get("pemilik") or it.get("pemilik") or "").strip() or None
            kepemilikan = normalize_kepemilikan(pemilik_raw_val)

            jenis_rs = normalize_text_clean(it.get("jenis") or rekap_info.get("jenis")) or "RSU"

            coords = it.get("koordinat", [])
            lat_raw = coords[0] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else it.get("lat")
            lng_raw = coords[1] if isinstance(coords, (list, tuple)) and len(coords) >= 2 else it.get("lng")
            lat, lng, is_valid_coord, needs_geocoding = sanitize_coordinates(lat_raw, lng_raw)

            kode_bps = extract_kode_bps_from_kode_rs(kode_rs)

            cleaned_rows.append({
                "kode_rs": kode_rs,
                "nama_rs": nama_rs,
                "alamat": alamat,
                "telepon": telepon,
                "kode_bps": kode_bps,
                "kelas": kelas,
                "kepemilikan": kepemilikan,
                "pemilik_raw": pemilik_raw_val,
                "jenis_rs": jenis_rs,
                "lat": lat,
                "lng": lng,
                "is_valid_coord": 1 if is_valid_coord else 0,
                "needs_geocoding": 1 if needs_geocoding else 0,
                "sumber_data": "SIRS Kemenkes",
                "coverage_periode": "2026-LIVE"
            })

        df = pd.DataFrame(cleaned_rows)
        df_validated = CleanHospitalSchema.validate(df)

        valid_count = len(df_validated[df_validated["is_valid_coord"] == 1])
        geocode_count = len(df_validated[df_validated["needs_geocoding"] == 1])
        logger.info(f"[Validation] Validated {len(df_validated)} RS. Valid coords: {valid_count}, Needs geocoding: {geocode_count}.")
        return df_validated


# ─── Backward-Compatible Legacy Function ──────────────────────────


def clean_and_validate_hospitals(
    raw_rs_list: List[Dict[str, Any]],
    raw_rekap_list: Optional[List[Dict[str, Any]]] = None
) -> pd.DataFrame:
    """Legacy wrapper: clean hospitals via OOP class."""
    cleaner = RumahSakitCleaner()
    return cleaner.clean_records(raw_rs_list, raw_rekap_list)
