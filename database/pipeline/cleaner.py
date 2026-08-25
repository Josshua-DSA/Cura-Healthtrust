import re
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from models import EnumKelasRS, EnumKepemilikan

logger = logging.getLogger("DataCleaner")

# Bounding box validasi Jawa Timur
LAT_MIN, LAT_MAX = -8.9, -6.6
LNG_MIN, LNG_MAX = 110.8, 114.6

class CleanHospitalSchema(pa.DataFrameModel):
    kode_rs: Series[str] = pa.Field(nullable=False, unique=True)
    nama_rs: Series[str] = pa.Field(nullable=False)
    alamat: Series[str] = pa.Field(nullable=True)
    telepon: Series[str] = pa.Field(nullable=True)
    kode_bps: Series[str] = pa.Field(nullable=True, str_length={"min_value": 4, "max_value": 4})
    kelas: Series[str] = pa.Field(isin=["A", "B", "C", "D", "tidak_diketahui"])
    kepemilikan: Series[str] = pa.Field(isin=["pemerintah", "swasta", "tni_polri", "lainnya"])
    jenis_rs: Series[str] = pa.Field(nullable=False)
    lat: Series[float] = pa.Field(nullable=True, ge=LAT_MIN, le=LAT_MAX)
    lng: Series[float] = pa.Field(nullable=True, ge=LNG_MIN, le=LNG_MAX)
    sumber_data: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = True
        coerce = True

def normalize_kelas(raw_kelas: Optional[str]) -> str:
    """Normalize raw class string into standard enum."""
    if not raw_kelas or not isinstance(raw_kelas, str):
        return EnumKelasRS.tidak_diketahui.value
    cleaned = raw_kelas.strip().upper()
    if cleaned in ("A", "B", "C", "D"):
        return cleaned
    return EnumKelasRS.tidak_diketahui.value

def normalize_kepemilikan(raw_pemilik: Optional[str]) -> str:
    """Map verbose ownership strings from SIRS to standardized enum."""
    if not raw_pemilik or not isinstance(raw_pemilik, str):
        return EnumKepemilikan.lainnya.value
    p = raw_pemilik.lower()
    if any(k in p for k in ["tni", "polri"]):
        return EnumKepemilikan.tni_polri.value
    if any(k in p for k in ["pemkab", "pemkot", "pemprop", "kemkes", "kementerian", "pemerintah"]):
        return EnumKepemilikan.pemerintah.value
    if any(k in p for k in ["swasta", "perusahaan", "perorangan", "organisasi"]):
        return EnumKepemilikan.swasta.value
    return EnumKepemilikan.lainnya.value

def extract_kode_bps_from_kode_rs(kode_rs: str) -> Optional[str]:
    """SIRS Hospital code first 4 digits correspond to BPS code (e.g. 3501016 -> 3501)."""
    if kode_rs and len(str(kode_rs).strip()) >= 4:
        sub = str(kode_rs).strip()[:4]
        if sub.isdigit() and sub.startswith("35"):
            return sub
    return None

def clean_and_validate_hospitals(raw_rs_list: List[Dict[str, Any]], raw_rekap_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Join RS List with Rekap Data, sanitize string, parse coordinate bounding box,
    and enforce Pandera Data Contract.
    """
    # Create ownership lookup by kode_rs
    pemilik_map = {}
    for r in raw_rekap_list:
        k = str(r.get("kode", "")).strip()
        if k:
            pemilik_map[k] = r.get("pemilik")

    cleaned_records = []
    for item in raw_rs_list:
        kode = str(item.get("kode", "")).strip()
        if not kode:
            continue

        raw_nama = item.get("nama", "").strip()
        nama_rs = re.sub(r"\s+", " ", raw_nama)

        alamat = item.get("alamat")
        if alamat:
            alamat = re.sub(r"\s+", " ", alamat).strip()

        telepon = item.get("telepon")
        if telepon:
            telepon = re.sub(r"\s+", " ", telepon).strip()

        raw_kelas = item.get("kelas")
        kelas_enum = normalize_kelas(raw_kelas)

        raw_pemilik = pemilik_map.get(kode, "Lainnya")
        kepemilikan_enum = normalize_kepemilikan(raw_pemilik)

        jenis_rs = item.get("jenis", "RSU").strip() or "RSU"

        # Coordinates parsing & bounding box check
        coords = item.get("koordinat", [])
        lat, lng = None, None
        if isinstance(coords, list) and len(coords) >= 2:
            try:
                raw_lat = float(coords[0])
                raw_lng = float(coords[1])
                # Check if coordinates inside East Java bounding box
                if (LAT_MIN <= raw_lat <= LAT_MAX) and (LNG_MIN <= raw_lng <= LNG_MAX):
                    lat, lng = raw_lat, raw_lng
                else:
                    logger.warning(f"Coordinate out of East Java bound for RS {nama_rs}: [{raw_lat}, {raw_lng}]")
            except (ValueError, TypeError):
                pass

        kode_bps = extract_kode_bps_from_kode_rs(kode)

        cleaned_records.append({
            "kode_rs": kode,
            "nama_rs": nama_rs,
            "alamat": alamat if alamat else None,
            "telepon": telepon if telepon else None,
            "kode_bps": kode_bps,
            "kelas": kelas_enum,
            "kepemilikan": kepemilikan_enum,
            "jenis_rs": jenis_rs,
            "lat": lat,
            "lng": lng,
            "sumber_data": "SIRS Kemenkes"
        })

    df = pd.DataFrame(cleaned_records)
    # Deduplicate by kode_rs
    df = df.drop_duplicates(subset=["kode_rs"]).reset_index(drop=True)

    # Validate with Pandera
    validated_df = CleanHospitalSchema.validate(df)
    logger.info(f"[Validation] Successfully validated {len(validated_df)} hospital records with Pandera.")
    return validated_df
