from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    def __init__(self, db: AsyncSession, model: Any):
        self.db = db
        self.model = model

    async def get_by_id(self, id_val: Any) -> Optional[T]:
        return await self.db.get(self.model, id_val)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
