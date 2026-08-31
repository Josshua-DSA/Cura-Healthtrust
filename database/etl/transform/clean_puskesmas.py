"""
Puskesmas Cleaner — OOP class sesuai RULES.md Seksi 2.3.
Validasi tipe rawat, kode BPS 35xx, sanitasi koordinat Jatim, dan Pandera schema output.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from pipeline.clean.base_cleaner import BaseCleaner
from exceptions import ValidationError

logger = logging.getLogger("PuskesmasCleaner")


class CleanPuskesmasSchema(pa_pd.DataFrameModel):
    kode_puskesmas: Series[str] = pa.Field(unique=True, nullable=False)
    nama: Series[str] = pa.Field(nullable=False)
    tipe_rawat: Series[str] = pa.Field(isin=["rawat_inap", "non_rawat_inap"])
    alamat: Series[str] = pa.Field(nullable=True)
    kode_bps: Series[str] = pa.Field(nullable=True)
    kecamatan: Series[str] = pa.Field(nullable=True)
    telepon: Series[str] = pa.Field(nullable=True)
    jumlah_tt: Series[int] = pa.Field(ge=0)
    lat: Series[float] = pa.Field(nullable=True)
    lng: Series[float] = pa.Field(nullable=True)
    is_valid_coord: Series[int] = pa.Field(isin=[0, 1])
    needs_geocoding: Series[int] = pa.Field(isin=[0, 1])
    source_id: Series[str] = pa.Field(nullable=False)
    coverage_periode: Series[str] = pa.Field(eq="2024-OFFICIAL")

    class Config:
        strict = True
        coerce = True


class PuskesmasCleaner(BaseCleaner):
    """
    Cleaner untuk data Puskesmas Jawa Timur.
    Sesuai RULES.md: validate_raw → transform → validate_output.
    """

    @property
    def schema_input(self) -> None:
        return None

    @property
    def schema_output(self) -> pa.DataFrameSchema:
        return CleanPuskesmasSchema.to_schema()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize raw puskesmas DataFrame."""
        cleaned_rows = []
        for _, row in df.iterrows():
            kode_pkm = str(row.get("kode_puskesmas", "")).strip()
            nama = str(row.get("nama", "Puskesmas Tanpa Nama")).strip()
            tipe = str(row.get("tipe_rawat", "non_rawat_inap")).strip().lower()
            if tipe not in ["rawat_inap", "non_rawat_inap"]:
                tipe = "non_rawat_inap"

            alamat = self._normalize_text(row.get("alamat"))
            kbps = str(row.get("kode_bps", "")).strip()
            if not (len(kbps) == 4 and kbps.startswith("35")):
                kbps = None

            kecamatan = self._normalize_text(row.get("kecamatan"))
            telepon = self._normalize_text(row.get("telepon"))
            jumlah_tt = int(float(row.get("jumlah_tt", 0))) if tipe == "rawat_inap" else 0

            # Coordinates
            lat_raw = row.get("lat")
            lng_raw = row.get("lng")
            lat_valid = None
            lng_valid = None
            is_valid = 0
            needs_geocode = 1

            if lat_raw is not None and lng_raw is not None and str(lat_raw).strip() and str(lng_raw).strip():
                try:
                    lat_f = float(str(lat_raw))
                    lng_f = float(str(lng_raw))
                    if (self.BBOX_LAT[0] <= lat_f <= self.BBOX_LAT[1]) and (self.BBOX_LNG[0] <= lng_f <= self.BBOX_LNG[1]):
                        lat_valid = round(lat_f, 6)
                        lng_valid = round(lng_f, 6)
                        is_valid = 1
                        needs_geocode = 0
                except (ValueError, TypeError):
                    pass

            cleaned_rows.append({
                "kode_puskesmas": kode_pkm,
                "nama": nama,
                "tipe_rawat": tipe,
                "alamat": alamat,
                "kode_bps": kbps,
                "kecamatan": kecamatan,
                "telepon": telepon,
                "jumlah_tt": jumlah_tt,
                "lat": lat_valid,
                "lng": lng_valid,
                "is_valid_coord": is_valid,
                "needs_geocoding": needs_geocode,
                "source_id": "opendata_jatim",
                "coverage_periode": "2024-OFFICIAL"
            })

        df_out = pd.DataFrame(cleaned_rows)
        return df_out

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convenience method for raw list of dicts."""
        df_raw = pd.DataFrame(raw_records)
        return self.clean(df_raw)


def clean_and_validate_puskesmas(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Legacy/convenience wrapper function."""
    cleaner = PuskesmasCleaner()
    return cleaner.clean_records(raw_records)
