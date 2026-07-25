"""
MemoryService — Communication Memory Profile
=============================================
Compares the current analysis against the user's previous attempts and
builds a performance comparison ("Filler words reduced by 34%", etc.).
"""

from sqlalchemy import select
from app.models.analysis import Analysis
from app.models.video import Video


async def build_comparison(db, current: Analysis) -> dict:
    """Compare with the most recent previous completed analysis."""
    result = await db.execute(
        select(Analysis).join(Video, Analysis.video_id == Video.id)
        .where(Analysis.id != current.id, Video.is_reference == False)  # noqa: E712
        .order_by(Analysis.created_at.desc()).limit(1)
    )
    prev = result.scalar_one_or_none()
    if not prev:
        return {"has_previous": False, "changes": [],
                "summary": "This is your first recorded session — future sessions will show your progress here."}

    changes = []

    def pct_change(cur, old):
        if old in (None, 0) or cur is None:
            return None
        return round((cur - old) / abs(old) * 100, 1)

    def add(metric, cur, old, lower_is_better=False, unit=""):
        if cur is None or old is None:
            return
        delta = pct_change(cur, old)
        if delta is None:
            return
        improved = (delta < 0) if lower_is_better else (delta > 0)
        if abs(delta) < 2:
            direction, text = "same", f"{metric} unchanged ({cur}{unit})"
        elif improved:
            direction = "improved"
            verb = "reduced" if lower_is_better else "improved"
            text = f"{metric} {verb} by {abs(delta):.0f}% ({old}{unit} → {cur}{unit})"
        else:
            direction = "regressed"
            verb = "increased" if lower_is_better else "dropped"
            text = f"{metric} {verb} by {abs(delta):.0f}% ({old}{unit} → {cur}{unit})"
        changes.append({"metric": metric, "from": old, "to": cur,
                        "change_pct": delta, "direction": direction, "text": text})

    add("Filler word rate", current.filler_word_rate, prev.filler_word_rate, lower_is_better=True, unit="/min")
    add("Eye contact", current.eye_contact_score, prev.eye_contact_score, unit="%")
    add("Overall score", current.overall_score, prev.overall_score)
    add("Confidence", current.confidence_score, prev.confidence_score)
    add("Body language", current.body_language_score, prev.body_language_score)
    add("Emotional presence", current.emotional_presence_score, prev.emotional_presence_score)
    add("Posture", current.posture_score, prev.posture_score)

    improved = [c for c in changes if c["direction"] == "improved"]
    regressed = [c for c in changes if c["direction"] == "regressed"]
    summary_bits = []
    if improved:  summary_bits.append(f"{len(improved)} area(s) improved since your last session")
    if regressed: summary_bits.append(f"{len(regressed)} area(s) need renewed attention")
    summary = ". ".join(summary_bits) + "." if summary_bits else "Performance is stable compared with your last session."

    return {"has_previous": True,
            "previous_date": str(prev.created_at)[:16] if prev.created_at else None,
            "changes": changes, "summary": summary}
