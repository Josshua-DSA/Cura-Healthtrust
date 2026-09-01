from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_

from backend.app.models.indikator import TblIndikatorKesehatan
from backend.app.models.referensi import RefICD10
from backend.app.models.wilayah import RefWilayah
from backend.app.schemas.indikator import (
    IndikatorItem,
    IndikatorTrendPoint,
    IndikatorTrendResponse,
    SDMSummaryItem,
)


class IndikatorService:
    @staticmethod
    async def get_indikator_list(
        db: AsyncSession,
        topik: Optional[str] = None,
        search: Optional[str] = None,
        kode_bps: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[IndikatorItem]:
        stmt = (
            select(TblIndikatorKesehatan, RefWilayah.nama_wilayah)
            .outerjoin(RefWilayah, TblIndikatorKesehatan.kode_bps == RefWilayah.kode_bps)
        )

        if topik:
            stmt = stmt.where(TblIndikatorKesehatan.topik.ilike(f"%{topik}%"))
        if search:
            stmt = stmt.where(
                or_(
                    TblIndikatorKesehatan.topik.ilike(f"%{search}%"),
                    TblIndikatorKesehatan.nama_indikator.ilike(f"%{search}%"),
                )
            )
        if kode_bps:
            stmt = stmt.where(TblIndikatorKesehatan.kode_bps == kode_bps)
        if tahun:
            stmt = stmt.where(TblIndikatorKesehatan.tahun == tahun)

        stmt = stmt.order_by(TblIndikatorKesehatan.kode_bps, TblIndikatorKesehatan.topik)
        result = await db.execute(stmt)
        rows = result.all()

        items: List[IndikatorItem] = []
        for ind, nama_wilayah in rows:
            items.append(
                IndikatorItem(
                    id=ind.id,
                    kode_bps=ind.kode_bps,
                    nama_wilayah=nama_wilayah,
                    tahun=ind.tahun,
                    topik=ind.topik,
                    nama_indikator=ind.nama_indikator,
                    nilai=ind.nilai,
                    satuan=ind.satuan,
                    coverage_periode=ind.coverage_periode,
                    sumber_data=ind.sumber_data,
                )
            )
        return items

    @staticmethod
    async def get_sdm_summary(db: AsyncSession) -> List[SDMSummaryItem]:
        query = text("""
            SELECT 
                w.kode_bps,
                w.nama_wilayah,
                COALESCE(MAX(CASE WHEN ind.nama_indikator ILIKE '%Dokter%' THEN ind.nilai END), 0)::int as total_dokter,
                COALESCE(c.total_puskesmas, 0)::int as total_puskesmas,
                COALESCE(c.total_rs, 0)::int as total_rs,
                COALESCE(c.jumlah_penduduk_2021, 0)::int as jumlah_penduduk_2021,
                COALESCE(c.proyeksi_penduduk_2026, 0)::int as proyeksi_penduduk_2026,
                ROUND(CASE 
                    WHEN COALESCE(c.proyeksi_penduduk_2026, 0) > 0 
                    THEN (COALESCE(MAX(CASE WHEN ind.nama_indikator ILIKE '%Dokter%' THEN ind.nilai END), 0) / c.proyeksi_penduduk_2026 * 1000.0)::numeric 
                    ELSE 0.0 
                END, 2)::float as rasio_dokter_per_1000
            FROM ref_wilayah w
            LEFT JOIN v_choropleth_wilayah c ON c.kode_bps = w.kode_bps
            LEFT JOIN tbl_indikator_kesehatan ind ON ind.kode_bps = w.kode_bps AND ind.topik = 'Tenaga Medis'
            GROUP BY w.kode_bps, w.nama_wilayah, c.total_puskesmas, c.total_rs, c.jumlah_penduduk_2021, c.proyeksi_penduduk_2026
            ORDER BY w.kode_bps;
        """)

        result = await db.execute(query)
        rows = result.mappings().all()

        return [
            SDMSummaryItem(
                kode_bps=r["kode_bps"],
                nama_wilayah=r["nama_wilayah"],
                total_dokter=int(r["total_dokter"] or 0),
                total_puskesmas=int(r["total_puskesmas"] or 0),
                total_rs=int(r["total_rs"] or 0),
                jumlah_penduduk_2021=int(r["jumlah_penduduk_2021"] or 0),
                proyeksi_penduduk_2026=int(r["proyeksi_penduduk_2026"] or 0),
                rasio_dokter_per_1000=float(r["rasio_dokter_per_1000"] or 0.0),
            )
            for r in rows
        ]

    @staticmethod
    async def get_icd10_catalog(db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(RefICD10).where(RefICD10.is_active == 1).order_by(RefICD10.kode)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "kode": r.kode,
                "nama_en": r.nama_en,
                "nama_id": r.nama_id,
                "kategori": r.kategori,
            }
            for r in rows
        ]
