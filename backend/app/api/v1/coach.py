from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.analysis import Analysis
from app.schemas.schemas import CoachMessage, CoachResponse
from app.services.coach_engine import CoachEngine
from app.services.memory_service import build_comparison

router = APIRouter()

# Per-video coach sessions (in-memory, keeps short conversation context)
_sessions: dict[str, CoachEngine] = {}


@router.post("/chat", response_model=CoachResponse)
async def coach_chat(payload: CoachMessage, db: AsyncSession = Depends(get_db)):
    video_id = payload.video_id or payload.analysis_id
    if not video_id:
        raise HTTPException(400, "video_id is required")

    result = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
    analysis = result.scalar_one_or_none()

    # History summary from stored comparison (progress trends)
    history_summary = ""
    if analysis and analysis.comparison and analysis.comparison.get("has_previous"):
        history_summary = analysis.comparison.get("summary", "")

    engine = _sessions.setdefault(video_id, CoachEngine())
    return await engine.chat(payload.message, analysis=analysis, history_summary=history_summary)


@router.post("/reset/{video_id}")
async def reset_coach(video_id: str):
    if video_id in _sessions:
        _sessions[video_id].reset_conversation()
    return {"status": "reset"}
