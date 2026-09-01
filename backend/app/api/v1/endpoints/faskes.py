from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    GeoJSONFeatureCollection,
)
from backend.app.schemas.faskes import (
    FaskesBase,
    RumahSakitDetail,
    PuskesmasDetail,
    FaskesNearbyItem,
)
from backend.app.services.faskes_service import FaskesService

router = APIRouter(prefix="/faskes", tags=["Fasilitas Kesehatan (RS + Puskesmas)"])


@router.get("", response_model=PaginatedResponse[FaskesBase])
async def list_faskes(
    jenis_faskes: Optional[str] = Query(None, description="'rumah_sakit' or 'puskesmas'"),
    kode_bps: Optional[str] = Query(None, description="BPS code e.g. '3578'"),
    kelas_rs: Optional[str] = Query(None, description="Hospital Class 'A', 'B', 'C', 'D'"),
    kepemilikan: Optional[str] = Query(None, description="'pemerintah', 'swasta', 'tni_polri'"),
    search: Optional[str] = Query(None, description="Search by name or address"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and filter all healthcare facilities (Hospitals + Puskesmas) with pagination.
    """
    items, total_records = await FaskesService.get_faskes_list(
        db=db,
        jenis_faskes=jenis_faskes,
        kode_bps=kode_bps,
        kelas_rs=kelas_rs,
        kepemilikan=kepemilikan,
        search=search,
        page=page,
        page_size=page_size,
    )
    total_pages = (total_records + page_size - 1) // page_size

    return PaginatedResponse(
        success=True,
        message=f"{len(items)} healthcare facilities retrieved.",
        data=items,
        pagination=PaginationMeta(
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get("/map/geojson", response_model=GeoJSONFeatureCollection)
async def get_faskes_geojson(
    jenis_faskes: Optional[str] = Query(None, description="'rumah_sakit' or 'puskesmas'"),
    kode_bps: Optional[str] = Query(None, description="Filter by BPS district code"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns valid Point features GeoJSON (RFC 7946) for Leaflet/Mapbox interactive clustering map.
    """
    return await FaskesService.get_faskes_geojson(
        db=db,
        jenis_faskes=jenis_faskes,
        kode_bps=kode_bps,
    )


@router.get("/nearby", response_model=APIResponse[List[FaskesNearbyItem]])
async def get_nearby_faskes(
    lat: float = Query(..., ge=-90.0, le=90.0, description="User Latitude (e.g. -7.2575)"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="User Longitude (e.g. 112.7521)"),
    radius_km: float = Query(5.0, ge=0.5, le=50.0, description="Search radius in kilometers"),
    jenis_faskes: Optional[str] = Query(None, description="'rumah_sakit' or 'puskesmas'"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    PostGIS-powered sub-10ms spatial radius search (ST_DWithin & ST_Distance).
    """
    items = await FaskesService.get_nearby_faskes(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        jenis_faskes=jenis_faskes,
        limit=limit,
    )
    return APIResponse(
        success=True,
        message=f"Found {len(items)} facilities within {radius_km} km.",
        data=items,
        meta={"radius_km": radius_km, "total_found": len(items)},
    )


@router.get("/rs/{kode_rs}", response_model=APIResponse[RumahSakitDetail])
async def get_hospital_detail(
    kode_rs: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full detail for a hospital by SIRS ID (e.g. '3578016').
    """
    rs = await FaskesService.get_hospital_detail(db, kode_rs)
    if not rs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with code '{kode_rs}' not found.",
        )
    return APIResponse(
        success=True,
        message=f"Hospital detail for '{rs.nama_rs}' retrieved.",
        data=rs,
    )


@router.get("/puskesmas/{kode_puskesmas}", response_model=APIResponse[PuskesmasDetail])
async def get_puskesmas_detail(
    kode_puskesmas: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full detail for a Puskesmas by code (e.g. 'PKM35780001').
    """
    pkm = await FaskesService.get_puskesmas_detail(db, kode_puskesmas)
    if not pkm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Puskesmas with code '{kode_puskesmas}' not found.",
        )
    return APIResponse(
        success=True,
        message=f"Puskesmas detail for '{pkm.nama}' retrieved.",
        data=pkm,
    )
