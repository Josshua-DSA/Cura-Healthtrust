from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse
from backend.app.schemas.statistik import (
    ExecutiveSummaryKPI,
    AccessibilityMetrics,
    WilayahCompareResponse,
)
from backend.app.services.statistik_service import StatistikService

router = APIRouter(prefix="/statistik", tags=["Statistik & Analisis Wilayah"])


@router.get("/executive-summary", response_model=APIResponse[ExecutiveSummaryKPI])
async def get_executive_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get executive macroeconomic health summary KPIs for East Java (Dashboard D01).
    """
    data = await StatistikService.get_executive_summary(db)
    return APIResponse(
        success=True,
        message="Executive summary metrics retrieved successfully.",
        data=data,
    )


@router.get("/accessibility", response_model=APIResponse[AccessibilityMetrics])
async def get_accessibility_metrics(
    db: AsyncSession = Depends(get_db),
):
    """
    Healthcare accessibility & gap analysis metrics across 38 districts (Dashboard D02).
    """
    data = await StatistikService.get_accessibility_metrics(db)
    return APIResponse(
        success=True,
        message="Accessibility metrics retrieved successfully.",
        data=data,
    )


@router.get("/compare", response_model=APIResponse[WilayahCompareResponse])
async def compare_wilayah(
    kode_bps_a: str = Query(..., description="Kode BPS Wilayah A misal '3578' (Surabaya)"),
    kode_bps_b: str = Query(..., description="Kode BPS Wilayah B misal '3573' (Malang)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two Kabupaten/Kota side-by-side across bed ratios, hospitals, clinics, and doctors.
    """
    data = await StatistikService.compare_wilayah(db, kode_bps_a, kode_bps_b)
    if not data.wilayah_a or not data.wilayah_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both wilayah codes not found.",
        )
    return APIResponse(
        success=True,
        message="Comparison generated successfully.",
        data=data,
    )
