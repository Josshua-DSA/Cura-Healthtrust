from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class TenagaKesehatanItem(BaseModel):
    id: int
    kode_bps: str
    nama_wilayah: Optional[str] = None
    tahun: int
    semester: int
    jenis_nakes: str
    jumlah: int
    faskes_level: str
    sumber_data: str = "Dinas Kesehatan Provinsi Jawa Timur"
    coverage_periode: str = "2025-OFFICIAL"

    model_config = ConfigDict(from_attributes=True)


class PasienPenyakitItem(BaseModel):
    id: int
    kode_bps: str
    nama_wilayah: Optional[str] = None
    tahun: int
    triwulan: str
    tipe_pelayanan: str
    nama_penyakit: str
    kode_icd10: Optional[str] = None
    jumlah_pasien: int
    status_kasus: str
    sumber_data: str = "Dinkes & OpenData Jatim"
    coverage_periode: str = "2025-OFFICIAL"

    model_config = ConfigDict(from_attributes=True)


class PenyakitTrendItem(BaseModel):
    nama_penyakit: str
    kode_icd10: Optional[str] = None
    status_kasus: str
    total_kasus_triwulanan: List[dict]
