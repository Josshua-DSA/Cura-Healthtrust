import io
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.core.database import get_db
from backend.app.models.auth import AuthUser
from backend.app.models.enums import EnumUserRole
from backend.app.models.transaksi import (
    TrxKunjungan,
    TrxOccupancy,
    TrxStokObat,
    EnumJenisKunjungan,
)
from backend.app.schemas.common import APIResponse
from backend.app.schemas.transaksi import (
    KunjunganCreate,
    KunjunganItem,
    OccupancyCreate,
    OccupancyItem,
    StokObatCreate,
    StokObatItem,
)
from backend.app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/transaksi", tags=["Transaksi Operasional & Data Input"])


def check_faskes_permission(user: AuthUser, faskes_id: str):
    """
    Operator can only view/mutate their own assigned faskes.
    Admins and Superadmins can access any faskes.
    """
    if user.role in [EnumUserRole.admin, EnumUserRole.superadmin, EnumUserRole.analyst]:
        return
    if user.role == EnumUserRole.operator:
        if user.faskes_id != faskes_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Operator only permitted to access assigned faskes '{user.faskes_id}'.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role not authorized for transaction operations.",
        )


@router.get("/bor", response_model=APIResponse[List[OccupancyItem]])
async def get_occupancy_bor(
    faskes_id: str = Query(..., description="Kode RS atau Puskesmas"),
    periode: Optional[str] = Query(None, description="Periode YYYY-MM e.g. '2026-08'"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Bed Occupancy Rate (BOR), ALOS, TOI, BTO metrics for a facility.
    """
    check_faskes_permission(current_user, faskes_id)

    stmt = select(TrxOccupancy).where(TrxOccupancy.faskes_id == faskes_id)
    if periode:
        stmt = stmt.where(TrxOccupancy.periode == periode)
    stmt = stmt.order_by(TrxOccupancy.periode.desc())

    result = await db.execute(stmt)
    items = result.scalars().all()

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} occupancy records.",
        data=[OccupancyItem.model_validate(i) for i in items],
    )


@router.post("/bor", response_model=APIResponse[OccupancyItem], status_code=status.HTTP_201_CREATED)
async def create_occupancy_record(
    payload: OccupancyCreate,
    current_user: AuthUser = Depends(require_role([EnumUserRole.operator, EnumUserRole.admin])),
    db: AsyncSession = Depends(get_db),
):
    check_faskes_permission(current_user, payload.faskes_id)

    stmt = select(TrxOccupancy).where(
        TrxOccupancy.faskes_id == payload.faskes_id,
        TrxOccupancy.periode == payload.periode,
    )
    existing = await db.scalar(stmt)
    if existing:
        existing.bor = payload.bor
        existing.alos = payload.alos
        existing.toi = payload.toi
        existing.bto = payload.bto
        existing.total_tempat_tidur = payload.total_tempat_tidur
        existing.hari_perawatan = payload.hari_perawatan
        record = existing
    else:
        record = TrxOccupancy(
            faskes_id=payload.faskes_id,
            periode=payload.periode,
            bor=payload.bor,
            alos=payload.alos,
            toi=payload.toi,
            bto=payload.bto,
            total_tempat_tidur=payload.total_tempat_tidur,
            hari_perawatan=payload.hari_perawatan,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)

    return APIResponse(
        success=True,
        message="Occupancy record saved successfully.",
        data=OccupancyItem.model_validate(record),
    )


@router.get("/kunjungan", response_model=APIResponse[List[KunjunganItem]])
async def get_kunjungan_list(
    faskes_id: str = Query(..., description="Kode RS atau Puskesmas"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_faskes_permission(current_user, faskes_id)

    stmt = (
        select(TrxKunjungan)
        .where(TrxKunjungan.faskes_id == faskes_id)
        .order_by(TrxKunjungan.tanggal.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} visit records.",
        data=[KunjunganItem.model_validate(i) for i in items],
    )


@router.get("/stok-obat", response_model=APIResponse[List[StokObatItem]])
async def get_stok_obat_list(
    faskes_id: str = Query(..., description="Kode RS atau Puskesmas"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_faskes_permission(current_user, faskes_id)

    stmt = (
        select(TrxStokObat)
        .where(TrxStokObat.faskes_id == faskes_id)
        .order_by(TrxStokObat.nama_obat)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} pharmacy stock records.",
        data=[StokObatItem.model_validate(i) for i in items],
    )


@router.post("/import", response_model=APIResponse[Dict[str, Any]])
async def import_operational_csv(
    tipe_data: str = Query(..., description="'kunjungan', 'occupancy', 'stok_obat'"),
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role([EnumUserRole.operator, EnumUserRole.admin])),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk CSV Import for operator data feeds (kunjungan, occupancy, stok obat).
    """
    content = await file.read()
    text_data = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_data))

    inserted_count = 0

    if tipe_data == "occupancy":
        for row in reader:
            faskes_id = row.get("faskes_id", "").strip()
            check_faskes_permission(current_user, faskes_id)
            rec = TrxOccupancy(
                faskes_id=faskes_id,
                periode=row["periode"].strip(),
                bor=float(row["bor"]),
                alos=float(row.get("alos") or 0.0),
                toi=float(row.get("toi") or 0.0),
                bto=float(row.get("bto") or 0.0),
                total_tempat_tidur=int(row["total_tempat_tidur"]),
            )
            db.add(rec)
            inserted_count += 1

    elif tipe_data == "stok_obat":
        for row in reader:
            faskes_id = row.get("faskes_id", "").strip()
            check_faskes_permission(current_user, faskes_id)
            stok = int(row["stok_tersedia"])
            min_stok = int(row.get("stok_minimum") or 100)
            status_stk = "kritis" if stok < (min_stok * 0.5) else ("waspada" if stok < min_stok else "aman")

            rec = TrxStokObat(
                faskes_id=faskes_id,
                kode_obat=row["kode_obat"].strip(),
                nama_obat=row["nama_obat"].strip(),
                satuan=row.get("satuan", "tablet").strip(),
                stok_tersedia=stok,
                stok_minimum=min_stok,
                pemakaian_bulanan=int(row.get("pemakaian_bulanan") or 0),
                status_stok=status_stk,
            )
            db.add(rec)
            inserted_count += 1

    await db.commit()

    return APIResponse(
        success=True,
        message=f"Successfully imported {inserted_count} records for '{tipe_data}'.",
        data={"inserted_count": inserted_count, "tipe_data": tipe_data},
    )
