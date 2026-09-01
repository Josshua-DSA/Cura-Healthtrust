from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.repositories.penyakit_sdm_repository import (
    TenagaKesehatanRepository,
    PasienPenyakitRepository,
)
from backend.app.schemas.penyakit_sdm import (
    TenagaKesehatanItem,
    PasienPenyakitItem,
    PenyakitTrendItem,
)


class PenyakitSdmService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nakes_repo = TenagaKesehatanRepository(db)
        self.penyakit_repo = PasienPenyakitRepository(db)

    async def list_tenaga_kesehatan(
        self,
        kode_bps: Optional[str] = None,
        jenis_nakes: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[TenagaKesehatanItem]:
        records = await self.nakes_repo.get_by_wilayah_and_jenis(
            kode_bps=kode_bps,
            jenis_nakes=jenis_nakes,
            tahun=tahun,
        )
        return [TenagaKesehatanItem.model_validate(r) for r in records]

    async def list_pasien_penyakit(
        self,
        kode_bps: Optional[str] = None,
        nama_penyakit: Optional[str] = None,
        kode_icd10: Optional[str] = None,
        tipe_pelayanan: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[PasienPenyakitItem]:
        records = await self.penyakit_repo.get_morbidity_records(
            kode_bps=kode_bps,
            nama_penyakit=nama_penyakit,
            kode_icd10=kode_icd10,
            tipe_pelayanan=tipe_pelayanan,
            tahun=tahun,
        )
        return [PasienPenyakitItem.model_validate(r) for r in records]

    async def get_disease_trends(
        self,
        kode_bps: Optional[str] = None,
        tahun: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}
        if kode_bps:
            where_clauses.append("kode_bps = :kode_bps")
            params["kode_bps"] = kode_bps
        if tahun:
            where_clauses.append("tahun = :tahun")
            params["tahun"] = tahun

        where_sql = " AND ".join(where_clauses)

        query = text(f"""
            SELECT 
                nama_penyakit,
                kode_icd10,
                status_kasus::text as status_kasus,
                SUM(jumlah_pasien)::int as total_pasien
            FROM tbl_pasien_penyakit_wilayah
            WHERE {where_sql}
            GROUP BY nama_penyakit, kode_icd10, status_kasus
            ORDER BY total_pasien DESC
            LIMIT 10;
        """)
        res = await self.db.execute(query, params)
        return [dict(r) for r in res.mappings().all()]
