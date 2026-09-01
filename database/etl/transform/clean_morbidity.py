"""
Morbidity Data Cleaner — OOP class sesuai RULES.md Seksi 2.3.
Standardisasi dan validasi data Kasus Pasien & 10 Penyakit Terbanyak (Domain C).
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from pipeline.clean.base_cleaner import BaseCleaner
from exceptions import ValidationError

logger = logging.getLogger("MorbidityCleaner")


class CleanMorbiditySchema(pa_pd.DataFrameModel):
    kode_bps: Series[str] = pa.Field(nullable=False)
    nama_wilayah: Series[str] = pa.Field(nullable=False)
    tahun: Series[int] = pa.Field(ge=2020, le=2030)
    triwulan: Series[str] = pa.Field(isin=["Q1", "Q2", "Q3", "Q4", "TAHUNAN"])
    tipe_pelayanan: Series[str] = pa.Field(isin=["rawat_inap", "rawat_jalan", "igd"])
    nama_penyakit: Series[str] = pa.Field(nullable=False)
    kode_icd10: Series[str] = pa.Field(nullable=True)
    jumlah_pasien: Series[int] = pa.Field(ge=0)
    status_kasus: Series[str] = pa.Field(isin=["menular", "tidak_menular"])
    sumber_data: Series[str] = pa.Field(nullable=False)
    coverage_periode: Series[str] = pa.Field(eq="2024-OFFICIAL")

    class Config:
        strict = True
        coerce = True


class MorbidityCleaner(BaseCleaner):
    """Cleaner untuk dataset Kasus Pasien dan Tren Morbiditas (Domain C)."""

    @property
    def schema_input(self) -> None:
        return None

    @property
    def schema_output(self) -> pa.DataFrameSchema:
        return CleanMorbiditySchema.to_schema()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        cleaned_rows = []
        for _, row in df.iterrows():
            kbps = str(row.get("kode_bps", "")).strip()
            if not (len(kbps) == 4 and kbps.startswith("35")):
                continue

            nama_wil = self._normalize_text(row.get("nama_wilayah", "Wilayah"))
            tahun = int(float(row.get("tahun", 2024)))
            triwulan = str(row.get("triwulan", "Q1")).strip().upper()
            if triwulan not in ["Q1", "Q2", "Q3", "Q4", "TAHUNAN"]:
                triwulan = "Q1"

            tipe_pel = str(row.get("tipe_pelayanan", "rawat_inap")).strip().lower()
            if tipe_pel not in ["rawat_inap", "rawat_jalan", "igd"]:
                tipe_pel = "rawat_inap"

            nama_p = self._normalize_text(row.get("nama_penyakit", "Penyakit"))
            icd = str(row.get("kode_icd10", "")).strip() or None
            jumlah = max(0, int(float(row.get("jumlah_pasien", 0))))
            status_k = str(row.get("status_kasus", "menular")).strip().lower()
            if status_k not in ["menular", "tidak_menular"]:
                status_k = "menular"

            sumber = self._normalize_text(row.get("sumber_data", "Dinas Kesehatan Provinsi Jawa Timur"))

            cleaned_rows.append({
                "kode_bps": kbps,
                "nama_wilayah": nama_wil,
                "tahun": tahun,
                "triwulan": triwulan,
                "tipe_pelayanan": tipe_pel,
                "nama_penyakit": nama_p,
                "kode_icd10": icd,
                "jumlah_pasien": jumlah,
                "status_kasus": status_k,
                "sumber_data": sumber,
                "coverage_periode": "2024-OFFICIAL"
            })

        return pd.DataFrame(cleaned_rows)

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        return self.clean(pd.DataFrame(raw_records))


def clean_and_validate_morbidity(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    cleaner = MorbidityCleaner()
    return cleaner.clean_records(raw_records)
