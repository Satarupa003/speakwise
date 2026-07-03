from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.schemas.schemas import CoachMessage, CoachResponse, ProgressDashboard, ProgressEntry, ScoreBreakdown, PipelineIngestRequest, PipelineStatus
from app.models.analysis import Analysis
from app.models.video import Video, VideoStatus

router = APIRouter()


@router.post("/chat", response_model=CoachResponse)
async def coach_chat(
    payload: CoachMessage,
    db: AsyncSession = Depends(get_db),
):
    """Chat with the AI coach about your speech."""
    from app.services.coach_engine import CoachEngine
    engine = CoachEngine()

    analysis = None
    if payload.analysis_id:
        result = await db.execute(select(Analysis).where(Analysis.id == payload.analysis_id))
        analysis = result.scalar_one_or_none()

    reply = await engine.chat(payload.message, analysis)
    return reply
