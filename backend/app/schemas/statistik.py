from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class ExecutiveSummaryKPI(BaseModel):
    total_rs: int
    total_puskesmas: int
    total_faskes: int
    total_tempat_tidur: int
    total_dokter: int
    total_penduduk_2021: int
    total_proyeksi_penduduk_2026: int
    rasio_tt_rata_rata_resmi: float
    rasio_tt_rata_rata_2026: float
    distribusi_kategori_who_resmi: Dict[str, int]  # {'hijau': 24, 'kuning': 12, 'merah': 2}
    distribusi_kategori_who_2026: Dict[str, int]
    top_wilayah_faskes: List[Dict[str, Any]]


class AccessibilityMetrics(BaseModel):
    under_served_districts: List[Dict[str, Any]]  # Rasio < 0.7 (merah)
    optimal_served_districts: List[Dict[str, Any]]  # Rasio >= 1.0 (hijau)
    avg_rasio_dokter_jatim: float
    avg_rasio_tt_jatim: float
    gap_summary: str


class WilayahCompareResponse(BaseModel):
    wilayah_a: Dict[str, Any]
    wilayah_b: Dict[str, Any]
    comparison: Dict[str, Any]
