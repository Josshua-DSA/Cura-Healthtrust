"""
Maternal and Child Health (KIA) Cleaner — OOP Class sesuai RULES.md Seksi 2.3.
Standardisasi dan validasi metrik KIA (AKI, AKB, Stunting, Imunisasi IDL).
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pandera as pa
import pandera.pandas as pa_pd
from pandera.typing import Series

from pipeline.clean.base_cleaner import BaseCleaner

logger = logging.getLogger("KiaCleaner")


class CleanKiaSchema(pa_pd.DataFrameModel):
    kode_bps: Series[str] = pa.Field(nullable=False)
    nama_wilayah: Series[str] = pa.Field(nullable=False)
    tahun: Series[int] = pa.Field(ge=2020, le=2030)
    aki: Series[float] = pa.Field(ge=0.0, nullable=True)
    akb: Series[float] = pa.Field(ge=0.0, nullable=True)
    prevalensi_stunting: Series[float] = pa.Field(ge=0.0, le=100.0, nullable=True)
    cakupan_idl: Series[float] = pa.Field(ge=0.0, le=100.0, nullable=True)

    class Config:
        strict = False
        coerce = True


class KiaCleaner(BaseCleaner):
    """OOP Transformer untuk data KIA Jawa Timur."""

    @property
    def schema_input(self) -> None:
        return None

    @property
    def schema_output(self) -> pa.DataFrameSchema:
        return CleanKiaSchema.to_schema()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        df = df.copy()
        df["kode_bps"] = df["kode_bps"].astype(str).str.strip().str.zfill(4)
        df["nama_wilayah"] = df["nama_wilayah"].astype(str).str.strip()
        df["tahun"] = pd.to_numeric(df["tahun"], errors="coerce").fillna(2024).astype(int)

        float_cols = [
            "aki", "akb", "akaba", "k1_coverage", "k4_coverage",
            "persen_persalinan_faskes", "persen_bblr", "prevalensi_stunting",
            "prevalensi_gizi_buruk", "prevalensi_gizi_kurang", "prevalensi_gizi_lebih",
            "ds_ratio_posyandu", "cakupan_idl", "persen_desa_uci", "dropout_rate_imunisasi"
        ]
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        int_cols = ["jumlah_kelahiran_hidup", "jumlah_kematian_ibu", "jumlah_kematian_bayi"]
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        if "bulan" in df.columns:
            df["bulan"] = pd.to_numeric(df["bulan"], errors="coerce")

        df = df[df["kode_bps"].str.match(self.KODE_BPS_PATTERN)].copy()
        logger.info(f"[KiaCleaner] Successfully standardized {len(df)} KIA records.")
        return df

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        return self.clean(pd.DataFrame(raw_records))


def clean_and_validate_kia(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    cleaner = KiaCleaner()
    return cleaner.clean_records(raw_records)
