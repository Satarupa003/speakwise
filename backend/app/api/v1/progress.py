from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.video import Video
from app.schemas.schemas import ProgressDashboard, ProgressEntry

router = APIRouter()


@router.get("/", response_model=ProgressDashboard)
async def get_progress(db: AsyncSession = Depends(get_db)):
    """Communication Memory Profile — trends across all sessions."""
    result = await db.execute(
        select(Analysis).join(Video, Analysis.video_id == Video.id)
        .where(Video.is_reference == False)  # noqa: E712
        .order_by(Analysis.created_at.asc()))
    rows = result.scalars().all()

    entries = [ProgressEntry(
        video_id=a.video_id,
        date=str(a.created_at)[:16] if a.created_at else None,
        scenario=a.scenario, topic=a.topic,
        overall=a.overall_score, confidence=a.confidence_score,
        body_language=a.body_language_score, emotional_presence=a.emotional_presence_score,
        filler_word_rate=a.filler_word_rate, eye_contact=a.eye_contact_score,
    ) for a in rows]

    improving, regressing = [], []
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        checks = [("Overall", first.overall_score, last.overall_score, False),
                  ("Confidence", first.confidence_score, last.confidence_score, False),
                  ("Body language", first.body_language_score, last.body_language_score, False),
                  ("Emotional presence", first.emotional_presence_score, last.emotional_presence_score, False),
                  ("Filler rate", first.filler_word_rate, last.filler_word_rate, True),
                  ("Eye contact", first.eye_contact_score, last.eye_contact_score, False)]
        for name, old, new, lower_better in checks:
            if old is None or new is None:
                continue
            better = (new < old) if lower_better else (new > old)
            worse  = (new > old) if lower_better else (new < old)
            if better and abs(new - old) >= 2:  improving.append(name)
            elif worse and abs(new - old) >= 2: regressing.append(name)

    summary = (f"{len(rows)} session(s) recorded. "
               + (f"Improving: {', '.join(improving)}. " if improving else "")
               + (f"Needs attention: {', '.join(regressing)}." if regressing else ""))

    return ProgressDashboard(entries=entries, total_sessions=len(rows),
                             improving=improving, regressing=regressing, summary=summary.strip())
