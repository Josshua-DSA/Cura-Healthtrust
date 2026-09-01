from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.wilayah import RefWilayah
from backend.app.repositories.base_repository import BaseRepository


class WilayahRepository(BaseRepository[RefWilayah]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, RefWilayah)

    async def get_by_kode_bps(self, kode_bps: str) -> Optional[RefWilayah]:
        stmt = select(RefWilayah).where(RefWilayah.kode_bps == kode_bps)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_districts(self) -> List[RefWilayah]:
        stmt = select(RefWilayah).order_by(RefWilayah.kode_bps)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
