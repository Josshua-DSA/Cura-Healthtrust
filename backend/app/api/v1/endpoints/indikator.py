from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse
from backend.app.schemas.indikator import IndikatorItem, SDMSummaryItem
from backend.app.services.indikator_service import IndikatorService

router = APIRouter(tags=["Indikator Kesehatan, SDM & Penyakit"])


@router.get("/indikator", response_model=APIResponse[List[IndikatorItem]])
async def list_indikator(
    topik: Optional[str] = Query(None, description="Topik indikator misal 'Puskesmas', 'Tenaga Medis'"),
    kode_bps: Optional[str] = Query(None, description="Kode BPS 4 digit misal '3578'"),
    tahun: Optional[int] = Query(None, description="Tahun data misal 2024"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get thematic public health indicators (Puskesmas inpatient/outpatient, Doctors) from Dinkes Jatim.
    """
    data = await IndikatorService.get_indikator_list(
        db=db,
        topik=topik,
        kode_bps=kode_bps,
        tahun=tahun,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(data)} indicator records.",
        data=data,
        meta={"total": len(data)},
    )


@router.get("/sdm/summary", response_model=APIResponse[List[SDMSummaryItem]])
async def get_sdm_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated healthcare human resources (Doctors) and ratios per 1,000 population across 38 Kab/Kota.
    """
    data = await IndikatorService.get_sdm_summary(db)
    return APIResponse(
        success=True,
        message="Healthcare HR summary retrieved successfully.",
        data=data,
        meta={"total_districts": len(data)},
    )


@router.get("/penyakit/icd10", response_model=APIResponse[List[Dict[str, Any]]])
async def get_icd10_catalog(
    db: AsyncSession = Depends(get_db),
):
    """
    Master ICD-10 disease classification catalog.
    """
    data = await IndikatorService.get_icd10_catalog(db)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(data)} ICD-10 disease categories.",
        data=data,
        meta={"total": len(data)},
    )
