from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class IndikatorItem(BaseModel):
    id: int
    kode_bps: str
    nama_wilayah: Optional[str] = None
    tahun: int
    topik: str
    nama_indikator: str
    nilai: float
    satuan: Optional[str] = None
    coverage_periode: str = "2024-OFFICIAL"
    sumber_data: str = "Dinas Kesehatan Provinsi Jawa Timur"

    model_config = ConfigDict(from_attributes=True)


class IndikatorTrendPoint(BaseModel):
    tahun: int
    nilai: float


class IndikatorTrendResponse(BaseModel):
    kode_bps: str
    nama_wilayah: str
    nama_indikator: str
    satuan: Optional[str] = None
    trend: List[IndikatorTrendPoint]


class SDMSummaryItem(BaseModel):
    kode_bps: str
    nama_wilayah: str
    total_dokter: int
    total_puskesmas: int
    total_rs: int
    jumlah_penduduk_2021: int
    proyeksi_penduduk_2026: int
    rasio_dokter_per_1000: float
