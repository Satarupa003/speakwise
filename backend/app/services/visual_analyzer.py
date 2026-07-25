"""
VisualAnalyzer — DISABLED stub (body language turned off)
Returns neutral values so the rest of the pipeline keeps working.
Re-enable later by restoring the OpenCV implementation.
"""
from typing import Any


class VisualAnalyzer:
    async def analyze(self, video_path: str) -> dict[str, Any]:
        print("[VisualAnalyzer] Disabled - skipping body language analysis")
        return {
            "eye_contact_score": None, "gesture_frequency": None, "posture_score": None,
            "camera_engagement": None, "looking_away_count": None, "confidence_signal": None,
            "behavioral_patterns": [], "facial_expression_data": {}, "disabled": True,
        }
