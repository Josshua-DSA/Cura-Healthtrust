from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from backend.app.schemas.common import APIResponse
from backend.app.schemas.katalog import DatasetKatalogItem
from backend.app.services.katalog_service import KatalogService

router = APIRouter(prefix="/katalog", tags=["Katalog Dataset & Unduh Data"])


@router.get("", response_model=APIResponse[List[DatasetKatalogItem]])
async def list_catalog_datasets():
    """
    Explore all verified, cleaned public health datasets available for researchers & analysts.
    """
    datasets = KatalogService.get_all_datasets()
    return APIResponse(
        success=True,
        message=f"{len(datasets)} clean datasets available in catalog.",
        data=datasets,
        meta={"total_datasets": len(datasets)},
    )


@router.get("/{dataset_id}", response_model=APIResponse[DatasetKatalogItem])
async def get_catalog_dataset_detail(
    dataset_id: str,
):
    """
    Get detailed schema & metadata for a single dataset by ID.
    """
    datasets = KatalogService.get_all_datasets()
    target = next((d for d in datasets if d.id == dataset_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found in catalog.",
        )
    return APIResponse(
        success=True,
        message=f"Dataset '{target.judul}' metadata retrieved.",
        data=target,
    )


@router.get("/{dataset_id}/download")
async def download_dataset_file(
    dataset_id: str,
    format: str = Query("parquet", description="'parquet' or 'csv'"),
):
    """
    Direct high-performance file download (.parquet or .csv) without requiring database credentials.
    """
    file_path = KatalogService.get_dataset_file_path(dataset_id, format)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for dataset '{dataset_id}' in format '{format}' not found.",
        )

    media_type = "application/octet-stream" if format.lower() == "parquet" else "text/csv"
    filename = f"{dataset_id}.{format.lower()}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
