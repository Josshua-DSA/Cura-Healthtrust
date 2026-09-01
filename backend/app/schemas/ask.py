from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AskDataRequest(BaseModel):
    query: str
    include_context_domains: Optional[List[str]] = None  # ['faskes', 'indikator', 'sdm']
    target_wilayah: Optional[str] = None  # kode_bps misal '3578'


class AskDataCitation(BaseModel):
    dataset_name: str
    source_institution: str
    coverage_periode: str
    relevance_note: str


class AskDataResponse(BaseModel):
    query: str
    answer: str
    grounding_data: Dict[str, Any]
    citations: List[AskDataCitation]
    disclaimer: str = "Insight ini dihasilkan AI berdasarkan data resmi Jawa Timur."
