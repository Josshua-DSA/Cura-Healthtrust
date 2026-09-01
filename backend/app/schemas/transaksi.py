from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.models.transaksi import EnumJenisKunjungan


class KunjunganCreate(BaseModel):
    faskes_id: str
    tanggal: date
    jenis_kunjungan: EnumJenisKunjungan = EnumJenisKunjungan.rawat_jalan
    poli: Optional[str] = "Umum"
    jumlah_pasien: int


class KunjunganItem(KunjunganCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OccupancyCreate(BaseModel):
    faskes_id: str
    periode: str  # 'YYYY-MM'
    bor: float
    alos: Optional[float] = None
    toi: Optional[float] = None
    bto: Optional[float] = None
    total_tempat_tidur: int
    hari_perawatan: Optional[int] = None


class OccupancyItem(OccupancyCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StokObatCreate(BaseModel):
    faskes_id: str
    kode_obat: str
    nama_obat: str
    satuan: str = "tablet"
    stok_tersedia: int
    stok_minimum: int = 100
    pemakaian_bulanan: int = 0


class StokObatItem(StokObatCreate):
    id: int
    status_stok: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
