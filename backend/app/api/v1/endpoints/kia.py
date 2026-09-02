from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse, GeoJSONFeatureCollection
from backend.app.schemas.monitoring import IndikatorKiaItem, KiaSummary
from backend.app.services.monitoring_service import KiaService

router = APIRouter(prefix="/kia", tags=["Blok 3 — Kesehatan Ibu & Anak (KIA) & Gizi"])


@router.get("/summary", response_model=APIResponse[KiaSummary])
async def get_kia_summary(db: AsyncSession = Depends(get_db)):
    """
    Ringkasan makro indikator KIA seluruh Jawa Timur (Stunting, AKI, AKB, Imunisasi).
    """
    service = KiaService(db)
    data = await service.get_kia_summary()
    return APIResponse(
        success=True,
        message="KIA summary retrieved successfully.",
        data=data,
    )


@router.get("/choropleth", response_model=GeoJSONFeatureCollection)
async def get_kia_choropleth(
    metrik: str = Query("stunting", description="stunting, aki, akb, imunisasi"),
    db: AsyncSession = Depends(get_db),
):
    """
    GeoJSON MultiPolygon choropleth map untuk visualisasi spasial metrik KIA.
    """
    service = KiaService(db)
    return await service.get_kia_choropleth(metrik=metrik)


@router.get("/{kode_bps}", response_model=APIResponse[IndikatorKiaItem])
async def get_kia_by_wilayah(
    kode_bps: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Detail profil dan metrik KIA per Kabupaten/Kota.
    """
    service = KiaService(db)
    data = await service.get_kia_by_wilayah(kode_bps)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data KIA untuk kode wilayah {kode_bps} tidak ditemukan.",
        )
    return APIResponse(
        success=True,
        message=f"KIA data for {kode_bps} retrieved successfully.",
        data=data,
    )
