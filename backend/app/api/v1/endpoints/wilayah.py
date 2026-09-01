from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse, GeoJSONFeatureCollection
from backend.app.schemas.wilayah import WilayahBase, WilayahDetail, ChoroplethWilayahItem
from backend.app.services.wilayah_service import WilayahService

router = APIRouter(prefix="/wilayah", tags=["Wilayah & Spatial Choropleth"])


@router.get("", response_model=APIResponse[List[WilayahBase]])
async def list_wilayah(
    db: AsyncSession = Depends(get_db),
):
    """
    List all 38 Kabupaten / Kota in East Java.
    """
    data = await WilayahService.get_all_wilayah(db)
    return APIResponse(
        success=True,
        message="38 Kabupaten/Kota retrieved successfully.",
        data=data,
        meta={"total": len(data)},
    )


@router.get("/choropleth", response_model=APIResponse[List[ChoroplethWilayahItem]])
async def get_choropleth_data(
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated healthcare and population metrics (Official 2021 vs Projection 2026) for choropleth mapping.
    """
    data = await WilayahService.get_choropleth_data(db)
    return APIResponse(
        success=True,
        message="Choropleth spatial metrics retrieved successfully.",
        data=data,
        meta={"total": len(data)},
    )


@router.get("/choropleth/geojson", response_model=GeoJSONFeatureCollection)
async def get_choropleth_geojson(
    db: AsyncSession = Depends(get_db),
):
    """
    RFC 7946 GeoJSON FeatureCollection containing polygons and health indicators for Leaflet/Mapbox choropleth layers.
    """
    return await WilayahService.get_choropleth_geojson(db)


@router.get("/{kode_bps}", response_model=APIResponse[WilayahDetail])
async def get_wilayah_by_code(
    kode_bps: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed profile and aggregated healthcare metrics for a specific Kabupaten/Kota.
    """
    data = await WilayahService.get_wilayah_detail(db, kode_bps)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wilayah with BPS code '{kode_bps}' not found.",
        )
    return APIResponse(
        success=True,
        message=f"Detail for {data.nama_wilayah} retrieved.",
        data=data,
    )
