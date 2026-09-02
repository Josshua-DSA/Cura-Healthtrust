"""
Surveillance Data Cleaner — OOP Class sesuai RULES.md Seksi 2.3.
Standardisasi dan validasi deteksi anomali mingguan/bulanan penyakit potensial KLB.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from pipeline.clean.base_cleaner import BaseCleaner

logger = logging.getLogger("SurveillanceCleaner")


class CleanSurveillanceSchema(pa_pd.DataFrameModel):
    kode_bps: Series[str] = pa.Field(nullable=False)
    kode_icd10: Series[str] = pa.Field(nullable=False)
    periode_bulan: Series[str] = pa.Field(nullable=False)
    kasus_bulan_ini: Series[int] = pa.Field(ge=0)
    status_surveillance: Series[str] = pa.Field(isin=["normal", "waspada", "perhatian"])

    class Config:
        strict = False
        coerce = True


class SurveillanceCleaner(BaseCleaner):
    """OOP Transformer untuk data Surveillance Epidemiologi KLB."""

    @property
    def schema_input(self) -> None:
        return None

    @property
    def schema_output(self) -> pa.DataFrameSchema:
        return CleanSurveillanceSchema.to_schema()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        df = df.copy()
        df["kode_bps"] = df["kode_bps"].astype(str).str.strip().str.zfill(4)
        df["kode_icd10"] = df["kode_icd10"].astype(str).str.strip()
        df["periode_bulan"] = df["periode_bulan"].astype(str).str.strip()

        df["kasus_bulan_ini"] = pd.to_numeric(df["kasus_bulan_ini"], errors="coerce").fillna(0).astype(int)
        df["rata_rata_3bln"] = pd.to_numeric(df["rata_rata_3bln"], errors="coerce").fillna(0.0).astype(float)
        df["delta_persen"] = pd.to_numeric(df["delta_persen"], errors="coerce").fillna(0.0).astype(float)

        def classify_status(delta: float) -> str:
            if delta >= 50.0:
                return "perhatian"
            elif delta >= 20.0:
                return "waspada"
            return "normal"

        if "status_surveillance" not in df.columns or df["status_surveillance"].isnull().all():
            df["status_surveillance"] = df["delta_persen"].apply(classify_status)

        df = df[df["kode_bps"].str.match(self.KODE_BPS_PATTERN)].copy()
        logger.info(f"[SurveillanceCleaner] Standardized {len(df)} surveillance records.")
        return df

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        return self.clean(pd.DataFrame(raw_records))


def clean_and_validate_surveillance(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    cleaner = SurveillanceCleaner()
    return cleaner.clean_records(raw_records)
