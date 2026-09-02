from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class IndikatorKiaItem(BaseModel):
    id: int
    kode_bps: str
    nama_wilayah: Optional[str] = None
    tahun: int
    bulan: Optional[int] = None
    aki: Optional[float] = None
    akb: Optional[float] = None
    akaba: Optional[float] = None
    jumlah_kelahiran_hidup: Optional[int] = None
    jumlah_kematian_ibu: Optional[int] = None
    jumlah_kematian_bayi: Optional[int] = None
    k1_coverage: Optional[float] = None
    k4_coverage: Optional[float] = None
    persen_persalinan_faskes: Optional[float] = None
    persen_bblr: Optional[float] = None
    prevalensi_stunting: Optional[float] = None
    prevalensi_gizi_buruk: Optional[float] = None
    prevalensi_gizi_kurang: Optional[float] = None
    cakupan_idl: Optional[float] = None
    persen_desa_uci: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class KiaSummary(BaseModel):
    total_wilayah: int
    avg_stunting: float
    avg_aki: float
    avg_akb: float
    avg_cakupan_imunisasi: float
    highest_stunting_wilayah: Optional[str] = None
    lowest_stunting_wilayah: Optional[str] = None


class AlertRuleItem(BaseModel):
    id: int
    kode: str
    nama: str
    blok: str
    kondisi_desc: Optional[str] = None
    threshold: Optional[Dict[str, Any]] = None
    severity: str
    rekomendasi: Optional[str] = None
    is_active: int

    model_config = ConfigDict(from_attributes=True)


class AlertEventItem(BaseModel):
    id: int
    rule_id: int
    nama_rule: Optional[str] = None
    kode_bps: Optional[str] = None
    nama_wilayah: Optional[str] = None
    faskes_id: Optional[int] = None
    faskes_tipe: Optional[str] = None
    nilai_terdeteksi: Optional[float] = None
    pesan: str
    severity: str
    status: str
    triggered_at: Optional[str] = None
    resolved_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
