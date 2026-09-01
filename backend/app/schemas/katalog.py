from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class DatasetKatalogItem(BaseModel):
    id: str
    judul: str
    deskripsi: str
    domain: str  # A: Faskes, B: SDM, C: Indikator, E: Demografi
    institusi_sumber: str
    coverage_periode: str
    cakupan_wilayah: str
    format_tersedia: List[str]  # ["parquet", "csv"]
    total_baris: int
    total_kolom: int
    file_size_parquet: str
    file_size_csv: str
    last_updated: str
    lisensi: str
    skema_ringkas: List[Dict[str, str]]
