from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import EnumTipeWilayah


class WilayahBase(BaseModel):
    kode_bps: str
    nama_wilayah: str
    tipe: EnumTipeWilayah

    model_config = ConfigDict(from_attributes=True)


class WilayahAgregatSummary(BaseModel):
    total_rs: int
    total_puskesmas: int
    total_tt: int
    jumlah_penduduk_2021: int
    rasio_tt_resmi: float
    kategori_who_resmi: str
    proyeksi_penduduk_2026: int
    rasio_tt_proyeksi_2026: float
    kategori_who_proyeksi_2026: str


class WilayahDetail(WilayahBase):
    agregat: Optional[WilayahAgregatSummary] = None


class ChoroplethWilayahItem(BaseModel):
    kode_bps: str
    nama_wilayah: str
    tipe: str
    total_rs: int
    total_puskesmas: int
    total_tt: int
    jumlah_penduduk_2021: int
    rasio_tt_resmi: float
    kategori_who_resmi: str
    proyeksi_penduduk_2026: int
    rasio_tt_proyeksi_2026: float
    kategori_who_proyeksi_2026: str
    geojson: Optional[Dict[str, Any]] = None
