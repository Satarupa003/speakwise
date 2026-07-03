from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.video import Video
from app.schemas.schemas import ProgressDashboard, ProgressEntry, ScoreBreakdown

router = APIRouter()


@router.get("/dashboard", response_model=ProgressDashboard)
async def get_progress(db: AsyncSession = Depends(get_db)):
    """Get user progress dashboard."""
    result = await db.execute(
        select(Analysis, Video)
        .join(Video, Analysis.video_id == Video.id)
        .where(Video.is_reference == False)  # noqa: E712
        .order_by(Analysis.created_at.desc())
        .limit(50)
    )
    rows = result.all()

    if not rows:
        return ProgressDashboard(
            total_sessions=0,
            avg_score=0.0,
            best_score=0.0,
            recent_sessions=[],
            score_trend=[],
        )

    scores = [r.Analysis.overall_score for r in rows if r.Analysis.overall_score]
    recent = [
        ProgressEntry(
            video_id=r.Analysis.video_id,
            date=r.Analysis.created_at,
            overall_score=r.Analysis.overall_score or 0,
            scores=ScoreBreakdown(
                overall=r.Analysis.overall_score,
                pace=r.Analysis.pace_score,
                clarity=r.Analysis.clarity_score,
                confidence=r.Analysis.confidence_score,
                engagement=r.Analysis.engagement_score,
                structure=r.Analysis.structure_score,
                body_language=r.Analysis.body_language_score,
            ),
        )
        for r in rows[:10]
    ]

    trend = [
        {"date": str(r.Analysis.created_at.date()), "score": r.Analysis.overall_score or 0}
        for r in reversed(rows)
    ]

    return ProgressDashboard(
        total_sessions=len(rows),
        avg_score=round(sum(scores) / len(scores), 1) if scores else 0,
        best_score=round(max(scores), 1) if scores else 0,
        recent_sessions=recent,
        score_trend=trend,
    )
