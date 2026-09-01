"""
Workforce Data Cleaner — OOP class sesuai RULES.md Seksi 2.3.
Standardisasi dan validasi data SDM Tenaga Medis (Dokter, Perawat, Bidan) Jawa Timur.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from pipeline.clean.base_cleaner import BaseCleaner
from exceptions import ValidationError

logger = logging.getLogger("WorkforceCleaner")

ALLOWED_NAKES = [
    "dokter_umum", "dokter_spesialis", "dokter_gigi",
    "perawat", "bidan", "ahli_gizi", "anestesi", "sanitarian"
]


class CleanWorkforceSchema(pa_pd.DataFrameModel):
    kode_bps: Series[str] = pa.Field(nullable=False)
    nama_wilayah: Series[str] = pa.Field(nullable=False)
    tahun: Series[int] = pa.Field(ge=2020, le=2030)
    semester: Series[int] = pa.Field(isin=[1, 2])
    jenis_nakes: Series[str] = pa.Field(isin=ALLOWED_NAKES)
    jumlah: Series[int] = pa.Field(ge=0)
    faskes_level: Series[str] = pa.Field(nullable=False)
    sumber_data: Series[str] = pa.Field(nullable=False)
    coverage_periode: Series[str] = pa.Field(eq="2024-OFFICIAL")

    class Config:
        strict = True
        coerce = True


class WorkforceCleaner(BaseCleaner):
    """Cleaner untuk dataset Tenaga Kesehatan / SDM Medis (Domain B)."""

    @property
    def schema_input(self) -> None:
        return None

    @property
    def schema_output(self) -> pa.DataFrameSchema:
        return CleanWorkforceSchema.to_schema()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        cleaned_rows = []
        for _, row in df.iterrows():
            kbps = str(row.get("kode_bps", "")).strip()
            if not (len(kbps) == 4 and kbps.startswith("35")):
                continue

            nama_wil = self._normalize_text(row.get("nama_wilayah", "Wilayah"))
            tahun = int(float(row.get("tahun", 2024)))
            semester = int(float(row.get("semester", 1)))
            j_nakes = str(row.get("jenis_nakes", "")).strip().lower()
            if j_nakes not in ALLOWED_NAKES:
                continue

            jumlah = max(0, int(float(row.get("jumlah", 0))))
            f_lvl = self._normalize_text(row.get("faskes_level", "Semua Faskes"))
            sumber = self._normalize_text(row.get("sumber_data", "Dinas Kesehatan Provinsi Jawa Timur"))

            cleaned_rows.append({
                "kode_bps": kbps,
                "nama_wilayah": nama_wil,
                "tahun": tahun,
                "semester": semester,
                "jenis_nakes": j_nakes,
                "jumlah": jumlah,
                "faskes_level": f_lvl,
                "sumber_data": sumber,
                "coverage_periode": "2024-OFFICIAL"
            })

        return pd.DataFrame(cleaned_rows)

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        return self.clean(pd.DataFrame(raw_records))


def clean_and_validate_workforce(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    cleaner = WorkforceCleaner()
    return cleaner.clean_records(raw_records)
