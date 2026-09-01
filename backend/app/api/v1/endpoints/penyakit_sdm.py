from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse
from backend.app.schemas.penyakit_sdm import TenagaKesehatanItem, PasienPenyakitItem
from backend.app.services.penyakit_sdm_service import PenyakitSdmService

router = APIRouter(tags=["SDM Spesifik & Epidemiologi Penyakit"])


@router.get("/sdm/nakes", response_model=APIResponse[List[TenagaKesehatanItem]])
async def list_tenaga_kesehatan_detail(
    kode_bps: Optional[str] = Query(None, description="Kode BPS 4 digit misal '3578'"),
    jenis_nakes: Optional[str] = Query(None, description="dokter_umum, dokter_spesialis, perawat, bidan, dll"),
    tahun: Optional[int] = Query(None, description="Tahun data misal 2025"),
    db: AsyncSession = Depends(get_db),
):
    """
    Rincian SDM Tenaga Medis dan Kesehatan (Dokter, Perawat, Bidan, Ahli Gizi) per wilayah.
    """
    service = PenyakitSdmService(db)
    data = await service.list_tenaga_kesehatan(kode_bps=kode_bps, jenis_nakes=jenis_nakes, tahun=tahun)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(data)} health workforce records.",
        data=data,
        meta={"total": len(data)},
    )


@router.get("/penyakit/morbiditas", response_model=APIResponse[List[PasienPenyakitItem]])
async def list_pasien_penyakit(
    kode_bps: Optional[str] = Query(None, description="Kode BPS misal '3578'"),
    nama_penyakit: Optional[str] = Query(None, description="Filter nama diagnosa"),
    kode_icd10: Optional[str] = Query(None, description="Filter kode ICD-10"),
    tipe_pelayanan: Optional[str] = Query(None, description="rawat_inap, rawat_jalan, igd"),
    tahun: Optional[int] = Query(None, description="Tahun"),
    db: AsyncSession = Depends(get_db),
):
    """
    Tren kasus morbiditas pasien triwulanan (Q1-Q4) berbasis diagnosa ICD-10 untuk riset Machine Learning.
    """
    service = PenyakitSdmService(db)
    data = await service.list_pasien_penyakit(
        kode_bps=kode_bps,
        nama_penyakit=nama_penyakit,
        kode_icd10=kode_icd10,
        tipe_pelayanan=tipe_pelayanan,
        tahun=tahun,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(data)} disease morbidity records.",
        data=data,
        meta={"total": len(data)},
    )


@router.get("/penyakit/top-trend", response_model=APIResponse[List[Dict[str, Any]]])
async def get_top_disease_trends(
    kode_bps: Optional[str] = Query(None, description="Kode BPS"),
    tahun: Optional[int] = Query(None, description="Tahun data"),
    db: AsyncSession = Depends(get_db),
):
    """
    10 Penyakit terbanyak dengan akumulasi volume pasien (Machine Learning feature preparation).
    """
    service = PenyakitSdmService(db)
    data = await service.get_disease_trends(kode_bps=kode_bps, tahun=tahun)
    return APIResponse(
        success=True,
        message="Top disease trends retrieved successfully.",
        data=data,
    )
