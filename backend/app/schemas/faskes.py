from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.enums import EnumKelasRS, EnumKepemilikan, EnumTipeRawatPuskesmas


# Base Faskes Schema
class FaskesBase(BaseModel):
    id_faskes: str
    jenis_faskes: str  # 'rumah_sakit' | 'puskesmas'
    nama: str
    kelas_tipe: str
    kepemilikan: str
    alamat: Optional[str] = None
    kode_bps: Optional[str] = None
    telepon: Optional[str] = None
    jumlah_tt: int = 0
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_valid_coord: int = 1
    coverage_periode: str = "2026-LIVE"

    model_config = ConfigDict(from_attributes=True)


# Detail Rumah Sakit
class RumahSakitDetail(BaseModel):
    id: int
    kode_rs: str
    nama_rs: str
    alamat: Optional[str] = None
    kode_bps: Optional[str] = None
    nama_wilayah: Optional[str] = None
    kelas: EnumKelasRS
    kepemilikan: EnumKepemilikan
    pemilik_raw: Optional[str] = None
    jenis_rs: Optional[str] = "RSU"
    jumlah_tt: int = 0
    layanan: List[str] = Field(default_factory=list)
    telepon: Optional[str] = None
    website: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_valid_coord: int = 1
    sumber_data: str = "SIRS Kemenkes"
    coverage_periode: str = "2026-LIVE"

    model_config = ConfigDict(from_attributes=True)


# Detail Puskesmas
class PuskesmasDetail(BaseModel):
    id: int
    kode_puskesmas: str
    nama: str
    tipe_rawat: EnumTipeRawatPuskesmas
    alamat: Optional[str] = None
    kode_bps: Optional[str] = None
    nama_wilayah: Optional[str] = None
    kecamatan: Optional[str] = None
    telepon: Optional[str] = None
    jumlah_tt: int = 0
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_valid_coord: int = 1
    source_id: Optional[str] = None
    coverage_periode: str = "2024-OFFICIAL"

    model_config = ConfigDict(from_attributes=True)


# Nearby Query Request/Response
class FaskesNearbyFilter(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    radius_km: float = Field(default=5.0, ge=0.5, le=50.0)
    jenis_faskes: Optional[str] = None  # 'rumah_sakit' | 'puskesmas' | None
    limit: int = Field(default=20, ge=1, le=100)


class FaskesNearbyItem(FaskesBase):
    distance_meters: float
    distance_km: float
