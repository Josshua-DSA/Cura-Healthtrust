from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.penyakit_sdm import TblTenagaKesehatan, TblPasienPenyakitWilayah
from backend.app.repositories.base_repository import BaseRepository


class TenagaKesehatanRepository(BaseRepository[TblTenagaKesehatan]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, TblTenagaKesehatan)

    async def get_by_wilayah_and_jenis(
        self,
        kode_bps: Optional[str] = None,
        jenis_nakes: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[TblTenagaKesehatan]:
        stmt = select(TblTenagaKesehatan)
        if kode_bps:
            stmt = stmt.where(TblTenagaKesehatan.kode_bps == kode_bps)
        if jenis_nakes:
            stmt = stmt.where(TblTenagaKesehatan.jenis_nakes == jenis_nakes)
        if tahun:
            stmt = stmt.where(TblTenagaKesehatan.tahun == tahun)
        stmt = stmt.order_by(TblTenagaKesehatan.kode_bps, TblTenagaKesehatan.jenis_nakes)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class PasienPenyakitRepository(BaseRepository[TblPasienPenyakitWilayah]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, TblPasienPenyakitWilayah)

    async def get_morbidity_records(
        self,
        kode_bps: Optional[str] = None,
        nama_penyakit: Optional[str] = None,
        kode_icd10: Optional[str] = None,
        tipe_pelayanan: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[TblPasienPenyakitWilayah]:
        stmt = select(TblPasienPenyakitWilayah)
        if kode_bps:
            stmt = stmt.where(TblPasienPenyakitWilayah.kode_bps == kode_bps)
        if nama_penyakit:
            stmt = stmt.where(TblPasienPenyakitWilayah.nama_penyakit.ilike(f"%{nama_penyakit}%"))
        if kode_icd10:
            stmt = stmt.where(TblPasienPenyakitWilayah.kode_icd10 == kode_icd10)
        if tipe_pelayanan:
            stmt = stmt.where(TblPasienPenyakitWilayah.tipe_pelayanan == tipe_pelayanan)
        if tahun:
            stmt = stmt.where(TblPasienPenyakitWilayah.tahun == tahun)
        stmt = stmt.order_by(TblPasienPenyakitWilayah.tahun.desc(), TblPasienPenyakitWilayah.triwulan.desc(), TblPasienPenyakitWilayah.jumlah_pasien.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
