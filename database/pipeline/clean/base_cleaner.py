"""
BaseCleaner — Abstract base class untuk semua data cleaner.
Sesuai RULES.md Seksi 2.3: Alur validate_raw → transform → validate_output.
"""

from abc import ABC, abstractmethod
from typing import Optional
import re
import logging
import pandas as pd
import pandera as pa

from exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseCleaner(ABC):
    """
    Base class untuk semua data cleaner Cura.
    Subclass wajib implement: schema_input, schema_output, transform.

    Alur: clean() → schema_input.validate → transform → schema_output.validate
    """

    # Bounding Box Jawa Timur + Pulau Bawean + Kepulauan Kangean (v3.0)
    BBOX_LAT = (-8.8, -5.7)
    BBOX_LNG = (110.9, 116.6)

    # Kode BPS pattern: 4 digit prefiks 35xx
    KODE_BPS_PATTERN = r"^35\d{2}$"

    # Enum standar
    KELAS_RS_VALID = {"A", "B", "C", "D", "tidak_diketahui"}
    KEPEMILIKAN_VALID = {"pemerintah", "swasta", "tni_polri", "lainnya"}

    @property
    @abstractmethod
    def schema_input(self) -> pa.DataFrameSchema:
        """Pandera schema untuk validasi raw data."""
        ...

    @property
    @abstractmethod
    def schema_output(self) -> pa.DataFrameSchema:
        """Pandera schema untuk validasi data bersih."""
        ...

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Logika transformasi utama. Diimplementasi subclass."""
        ...

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Entry point: validate input → transform → validate output.
        Raise ValidationError jika gagal.
        """
        try:
            if self.schema_input is not None:
                df = self.schema_input.validate(df, lazy=True)
            df = self.transform(df)
            if self.schema_output is not None:
                df = self.schema_output.validate(df, lazy=True)
            return df
        except pa.errors.SchemaErrors as e:
            raise ValidationError(
                f"Schema validation failed: {e.failure_cases.head(5).to_string()}"
            ) from e

    # ─── Helper methods yang bisa dipakai semua subclass ───

    def _normalize_text(self, text_val: Optional[str]) -> Optional[str]:
        """Clean newlines, tabs, and multiple spaces."""
        if not text_val or pd.isna(text_val):
            return None
        cleaned = str(text_val).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else None

    def _normalize_kode_bps(self, series: pd.Series) -> pd.Series:
        """Normalize and validate kode BPS 4-digit (35xx)."""
        return series.astype(str).str.zfill(4).where(
            series.astype(str).str.match(self.KODE_BPS_PATTERN), other=None
        )

    def _validate_koordinat(
        self, lat: pd.Series, lng: pd.Series
    ) -> tuple:
        """Validate coordinates against Jatim bounding box."""
        lat_valid = lat.where(lat.between(*self.BBOX_LAT))
        lng_valid = lng.where(lng.between(*self.BBOX_LNG))
        invalid = lat_valid.isna() & lat.notna()
        if invalid.any():
            logger.warning(f"{invalid.sum()} koordinat di luar bounding box Jatim → set NULL")
        return lat_valid, lng_valid

    def _normalize_enum(self, series: pd.Series, mapping: dict, default: str) -> pd.Series:
        """Map raw enum values to standardized values."""
        return series.str.lower().str.strip().map(mapping).fillna(default)
