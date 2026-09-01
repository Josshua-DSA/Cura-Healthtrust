from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.common import APIResponse
from backend.app.schemas.ask import AskDataRequest, AskDataResponse
from backend.app.services.ask_service import AskDataService

router = APIRouter(prefix="/ask", tags=["Ask Data (AI Insight & Grounding)"])


@router.post("", response_model=APIResponse[AskDataResponse])
async def ask_data_insight(
    payload: AskDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Query grounded health insights with natural language interpretation & cited data sources (Dashboard D10).
    """
    result = await AskDataService.process_query(db, payload)
    return APIResponse(
        success=True,
        message="AI Insight generated successfully.",
        data=result,
    )
