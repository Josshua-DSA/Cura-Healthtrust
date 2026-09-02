from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.monitoring import IndikatorKia, AlertRule, AlertEvent
from backend.app.repositories.base_repository import BaseRepository


class KiaRepository(BaseRepository[IndikatorKia]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, IndikatorKia)

    async def get_by_wilayah(self, kode_bps: str, tahun: Optional[int] = None) -> Optional[IndikatorKia]:
        stmt = select(IndikatorKia).where(IndikatorKia.kode_bps == kode_bps)
        if tahun:
            stmt = stmt.where(IndikatorKia.tahun == tahun)
        stmt = stmt.order_by(IndikatorKia.tahun.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_kia_data(self, tahun: Optional[int] = None) -> List[IndikatorKia]:
        stmt = select(IndikatorKia)
        if tahun:
            stmt = stmt.where(IndikatorKia.tahun == tahun)
        stmt = stmt.order_by(IndikatorKia.kode_bps)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class AlertRepository(BaseRepository[AlertRule]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, AlertRule)

    async def list_active_rules(self) -> List[AlertRule]:
        stmt = select(AlertRule).where(AlertRule.is_active == 1).order_by(AlertRule.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_events(self, status: Optional[str] = None, severity: Optional[str] = None) -> List[AlertEvent]:
        stmt = select(AlertEvent)
        if status:
            stmt = stmt.where(AlertEvent.status == status)
        if severity:
            stmt = stmt.where(AlertEvent.severity == severity)
        stmt = stmt.order_by(AlertEvent.triggered_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
