from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse
from backend.app.schemas.monitoring import AlertRuleItem, AlertEventItem
from backend.app.services.monitoring_service import DecisionAlertService

router = APIRouter(prefix="/decision", tags=["Blok 4 — Early Warning & Decision Support"])


@router.get("/rules", response_model=APIResponse[List[AlertRuleItem]])
async def list_alert_rules(db: AsyncSession = Depends(get_db)):
    """
    Daftar rule ambang batas anomali & defisit fasilitas kesehatan.
    """
    service = DecisionAlertService(db)
    data = await service.get_rules()
    return APIResponse(
        success=True,
        message="Active alert rules retrieved successfully.",
        data=data,
    )


@router.get("/alerts", response_model=APIResponse[List[AlertEventItem]])
async def list_alert_events(
    status: Optional[str] = Query(None, description="open, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="low, medium, high, critical"),
    db: AsyncSession = Depends(get_db),
):
    """
    Daftar peringatan dini (early warning alerts) yang terpicu.
    """
    service = DecisionAlertService(db)
    data = await service.get_events(status=status, severity=severity)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(data)} alert events.",
        data=data,
    )
