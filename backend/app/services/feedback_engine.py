"""
FeedbackEngine
==============
Generates personalized, actionable feedback for a speaker
by combining their analysis scores with reference clips from
great speakers in the knowledge base.

Flow:
  1. Identify weak areas from scores (below threshold)
  2. Query ChromaDB for great speakers who excel in those areas
  3. Send everything to Claude API to write specific, kind feedback
  4. Return structured improvement points + reference clips

Output dict shape:
{
    "summary":            str,
    "improvement_points": list[dict],  # [{area, issue, tip, reference}]
    "reference_clips":    list[dict],  # [{video_id, speaker, timestamp, reason}]
    "strengths":          list[str],
    "priority_focus":     str,         # the single most important thing to work on
}
"""

import json
import re
from typing import Any

import anthropic

from app.core.config import settings
from app.services.knowledge_base import KnowledgeBase


# Areas scoring below this threshold get improvement points
WEAK_THRESHOLD  = 70.0
# Areas scoring above this get called out as strengths
STRONG_THRESHOLD = 80.0

# Human-readable labels for each dimension
DIMENSION_LABELS = {
    "pace":          "Speaking Pace",
    "clarity":       "Clarity & Filler Words",
    "confidence":    "Confidence",
    "engagement":    "Audience Engagement",
    "structure":     "Speech Structure",
    "body_language": "Body Language",
}


class FeedbackEngine:

    def __init__(self):
        self._client = None
        self._kb     = KnowledgeBase()

    def _load_anthropic(self):
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )

    # ── Public API ──────────────────────────────────────────────────────────

    async def generate(
        self,
        audio:  dict[str, Any],
        visual: dict[str, Any],
        nlp:    dict[str, Any],
        scores: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Main entry point.
        Takes all analyzer outputs + scores.
        Returns structured feedback with reference clips.
        """
        print("[FeedbackEngine] Generating personalized feedback...")
        self._load_anthropic()

        # 1. Find weak and strong areas
        weak_areas   = self._find_weak_areas(scores)
        strong_areas = self._find_strong_areas(scores)

        print(f"[FeedbackEngine] Weak areas: {weak_areas}")
        print(f"[FeedbackEngine] Strong areas: {strong_areas}")

        # 2. Find reference speakers for weak areas from knowledge base
        reference_clips = await self._get_reference_clips(weak_areas, audio)

        # 3. Build context for Claude
        context = self._build_context(audio, visual, nlp, scores)

        # 4. Generate feedback with Claude
        feedback = await self._claude_feedback(
            context, weak_areas, strong_areas, reference_clips
        )

        # 5. Attach reference clips to improvement points
        feedback["reference_clips"] = reference_clips

        print(f"[FeedbackEngine] ✓ Generated {len(feedback['improvement_points'])} "
              f"improvement points, {len(reference_clips)} reference clips")
        return feedback

    # ── Weak / Strong area detection ─────────────────────────────────────────

    def _find_weak_areas(self, scores: dict) -> list[str]:
        """Return dimension names scoring below WEAK_THRESHOLD."""
        dimensions = ["pace", "clarity", "confidence",
                      "engagement", "structure", "body_language"]
        weak = [
            dim for dim in dimensions
            if scores.get(dim, 100) < WEAK_THRESHOLD
        ]
        # Sort by score ascending — worst areas first
        weak.sort(key=lambda d: scores.get(d, 0))
        return weak

    def _find_strong_areas(self, scores: dict) -> list[str]:
        """Return dimension names scoring above STRONG_THRESHOLD."""
        dimensions = ["pace", "clarity", "confidence",
                      "engagement", "structure", "body_language"]
        return [
            dim for dim in dimensions
            if scores.get(dim, 0) >= STRONG_THRESHOLD
        ]

    # ── Reference clips ──────────────────────────────────────────────────────

    async def _get_reference_clips(
        self,
        weak_areas: list[str],
        audio: dict,
    ) -> list[dict]:
        """
        Query knowledge base for reference speakers
        for each weak area. Returns up to 3 clips total.
        """
        clips = []

        for area in weak_areas[:3]:  # max 3 areas
            speakers = await self._kb.find_by_skill(area, n_results=1)
            for sp in speakers:
                clips.append({
                    "video_id":     sp["video_id"],
                    "speaker_name": sp["speaker_name"],
                    "title":        sp["title"],
                    "file_path":    sp.get("file_path", ""),
                    "timestamp":    sp.get("timestamp", 0.0),
                    "duration":     30.0,
                    "skill":        area,
                    "reason":       sp.get("reason", ""),
                })

        return clips

    # ── Context builder ──────────────────────────────────────────────────────

    def _build_context(
        self,
        audio:  dict,
        visual: dict,
        nlp:    dict,
        scores: dict,
    ) -> str:
        """Build a concise context string for Claude."""
        breakdown = scores.get("breakdown", {})

        return f"""
SCORES:
- Overall: {scores.get('overall')}/100
- Pace: {scores.get('pace')}/100
- Clarity: {scores.get('clarity')}/100
- Confidence: {scores.get('confidence')}/100
- Engagement: {scores.get('engagement')}/100
- Structure: {scores.get('structure')}/100
- Body Language: {scores.get('body_language')}/100

AUDIO METRICS:
- Speaking pace: {audio.get('words_per_minute')} WPM (ideal: 120-160)
- Filler words: {audio.get('filler_word_count')} total, {audio.get('filler_word_rate')}/min
- Filler breakdown: {json.dumps(audio.get('filler_words_detail', {}))}
- Pauses: {audio.get('pause_count')} pauses, avg {audio.get('avg_pause_duration')}s
- Pitch variation: {audio.get('pitch_variation')} Hz std dev
- Duration: {audio.get('duration_seconds')}s

VISUAL METRICS:
- Eye contact: {visual.get('eye_contact_score')}/100
- Posture: {visual.get('posture_score')}/100
- Gesture frequency: {visual.get('gesture_frequency')} per minute

NLP ANALYSIS:
- Storytelling: {nlp.get('storytelling_score')}/100
- Clarity: {nlp.get('clarity_score')}/100
- Persuasion: {nlp.get('persuasion_score')}/100
- Opening strength: {nlp.get('opening_strength')}/100
- Closing strength: {nlp.get('closing_strength')}/100
- NLP feedback: {nlp.get('nlp_feedback', '')}
- Strongest moment: {nlp.get('strongest_moment', '')}
- Weakest moment: {nlp.get('weakest_moment', '')}
""".strip()

    # ── Claude feedback generation ────────────────────────────────────────────

    async def _claude_feedback(
        self,
        context:        str,
        weak_areas:     list[str],
        strong_areas:   list[str],
        reference_clips: list[dict],
    ) -> dict:
        """
        Use Claude to generate warm, specific, actionable feedback.
        """
        # Describe available reference clips
        clips_desc = ""
        if reference_clips:
            clips_desc = "\nAVAILABLE REFERENCE SPEAKERS:\n"
            for clip in reference_clips:
                clips_desc += (
                    f"- {clip['speaker_name']} ({clip['title']}) "
                    f"for skill: {clip['skill']}\n"
                )

        weak_labels  = [DIMENSION_LABELS.get(a, a) for a in weak_areas]
        strong_labels = [DIMENSION_LABELS.get(a, a) for a in strong_areas]

        prompt = f"""You are a warm, encouraging public speaking coach analyzing a speaker's performance.

ANALYSIS DATA:
{context}
{clips_desc}

WEAK AREAS (need improvement): {weak_labels}
STRONG AREAS (doing well): {strong_labels}

Generate coaching feedback. Respond with ONLY a JSON object (no markdown):

{{
    "summary": "<2-3 sentence overall assessment, warm and encouraging tone>",
    "priority_focus": "<single most important thing to work on, one sentence>",
    "strengths": [<list of 2-3 specific things they did well>],
    "improvement_points": [
        {{
            "area": "<dimension name from: pace/clarity/confidence/engagement/structure/body_language>",
            "issue": "<specific problem observed, one sentence, reference actual numbers>",
            "tip": "<specific actionable fix, 1-2 sentences, practical and concrete>",
            "exercise": "<a quick practice exercise they can do today>"
        }}
    ]
}}

Rules:
- improvement_points should cover the {len(weak_areas)} weak areas: {weak_labels}
- Reference specific numbers from the data (e.g. "your 185 WPM is above the ideal 120-160")
- Tips must be actionable (not vague like "be more confident")
- Tone: like a supportive coach, not a critic
- Each tip should reference what great speakers do differently"""

        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"```\s*",     "", raw)

            data = json.loads(raw)

            # Attach reference clip to matching improvement point
            improvement_points = data.get("improvement_points", [])
            for point in improvement_points:
                area = point.get("area", "")
                matching_clip = next(
                    (c for c in reference_clips if c["skill"] == area), None
                )
                if matching_clip:
                    point["reference_video_id"] = matching_clip["video_id"]
                    point["reference_speaker"]  = matching_clip["speaker_name"]
                    point["reference_timestamp"] = matching_clip["timestamp"]

            return {
                "summary":            data.get("summary", ""),
                "priority_focus":     data.get("priority_focus", ""),
                "strengths":          data.get("strengths", []),
                "improvement_points": improvement_points,
            }

        except Exception as e:
            print(f"[FeedbackEngine] Claude API error: {e}")
            return self._fallback_feedback(weak_areas, strong_areas)

    # ── Fallback ─────────────────────────────────────────────────────────────

    def _fallback_feedback(
        self,
        weak_areas:   list[str],
        strong_areas: list[str],
    ) -> dict:
        """Return basic feedback when Claude API fails."""
        return {
            "summary": (
                "Analysis complete. "
                f"Your strongest areas are {', '.join(strong_areas) or 'being assessed'}. "
                f"Focus on improving {', '.join(weak_areas) or 'consistency'}."
            ),
            "priority_focus": weak_areas[0] if weak_areas else "overall consistency",
            "strengths": [f"Good {a}" for a in strong_areas[:3]],
            "improvement_points": [
                {
                    "area":    area,
                    "issue":   f"Your {DIMENSION_LABELS.get(area, area)} needs attention.",
                    "tip":     f"Practice improving your {DIMENSION_LABELS.get(area, area)}.",
                    "exercise": "Record yourself and review.",
                }
                for area in weak_areas[:3]
            ],
        }
