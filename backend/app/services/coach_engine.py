"""
CoachEngine
===========
Conversational AI public speaking coach powered by Claude.

The coach:
  - Knows your full analysis results (scores, feedback, metrics)
  - Answers questions about your speech
  - Suggests targeted exercises
  - Gives encouragement and motivation
  - Recommends what to focus on next

Usage:
  engine = CoachEngine()
  response = await engine.chat("Why did I score low on clarity?", analysis)
  response = await engine.chat("Give me an exercise to reduce filler words", analysis)
"""

import json
import re
from typing import Any

import anthropic

from app.core.config import settings
from app.schemas.schemas import CoachResponse


# System prompt that defines the coach's personality and knowledge
COACH_SYSTEM_PROMPT = """You are SpeakWise Coach — a warm, encouraging, expert public speaking coach.

Your personality:
- Supportive and motivating, never harsh or discouraging
- Specific and practical — give concrete exercises, not vague advice
- Data-driven — reference actual numbers from the analysis when relevant
- Conversational — talk like a real coach, not a textbook
- Concise — keep responses focused and actionable (2-4 paragraphs max)

Your expertise covers:
- Speaking pace, rhythm, and pauses
- Filler word reduction techniques
- Vocal variety (pitch, volume, tone)
- Body language and eye contact
- Speech structure (opening, narrative arc, closing)
- Storytelling and audience engagement
- Confidence and stage presence

When suggesting exercises:
- Make them specific and time-bound ("Practice this for 5 minutes today")
- Make them immediately actionable (no equipment needed)
- Explain WHY the exercise helps

Always end with encouragement or a forward-looking statement."""


class CoachEngine:

    def __init__(self):
        self._client = None
        self._conversation_history = []  # maintains context within a session

    def _load_anthropic(self):
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )

    # ── Public API ──────────────────────────────────────────────────────────

    async def chat(
        self,
        message: str,
        analysis: Any = None,  # Analysis DB model or None
    ) -> CoachResponse:
        """
        Main entry point — send a message to the coach.

        message:  user's question or request
        analysis: optional Analysis DB object for context
        """
        self._load_anthropic()

        # Build context from analysis if available
        context = self._build_analysis_context(analysis)

        # Build the full message with context injected
        user_message = self._build_user_message(message, context)

        # Add to conversation history
        self._conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        # Keep history manageable (last 10 exchanges)
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=COACH_SYSTEM_PROMPT,
                messages=self._conversation_history,
            )

            reply_text = response.content[0].text.strip()

            # Add assistant reply to history for multi-turn context
            self._conversation_history.append({
                "role": "assistant",
                "content": reply_text,
            })

            # Extract any exercise suggestions from the reply
            suggestions = self._extract_suggestions(reply_text)

            return CoachResponse(
                reply=reply_text,
                suggestions=suggestions,
                referenced_clips=None,
            )

        except Exception as e:
            print(f"[CoachEngine] Claude API error: {e}")
            return CoachResponse(
                reply=(
                    "I'm having trouble connecting right now. "
                    "Please check your API key and try again."
                ),
                suggestions=None,
                referenced_clips=None,
            )

    def reset_conversation(self):
        """Clear conversation history — start fresh session."""
        self._conversation_history = []

    # ── Context builder ──────────────────────────────────────────────────────

    def _build_analysis_context(self, analysis: Any) -> str:
        """
        Convert Analysis DB model into a concise context string
        for Claude to reference during coaching.
        """
        if analysis is None:
            return ""

        lines = ["[SPEAKER ANALYSIS CONTEXT]"]

        # Scores
        if analysis.overall_score is not None:
            lines.append(f"Overall score: {analysis.overall_score}/100")
        if analysis.pace_score is not None:
            lines.append(f"Pace: {analysis.pace_score}/100")
        if analysis.clarity_score is not None:
            lines.append(f"Clarity: {analysis.clarity_score}/100")
        if analysis.confidence_score is not None:
            lines.append(f"Confidence: {analysis.confidence_score}/100")
        if analysis.engagement_score is not None:
            lines.append(f"Engagement: {analysis.engagement_score}/100")
        if analysis.structure_score is not None:
            lines.append(f"Structure: {analysis.structure_score}/100")
        if analysis.body_language_score is not None:
            lines.append(f"Body language: {analysis.body_language_score}/100")

        # Key audio metrics
        if analysis.words_per_minute is not None:
            lines.append(f"Speaking pace: {analysis.words_per_minute} WPM")
        if analysis.filler_word_count is not None:
            lines.append(f"Filler words: {analysis.filler_word_count} total "
                         f"({analysis.filler_word_rate}/min)")
        if analysis.filler_words_detail:
            lines.append(f"Filler breakdown: {json.dumps(analysis.filler_words_detail)}")

        # AI feedback summary
        if analysis.feedback_summary:
            lines.append(f"Feedback summary: {analysis.feedback_summary}")

        # Improvement points
        if analysis.improvement_points:
            lines.append("Improvement areas:")
            for point in analysis.improvement_points[:3]:
                lines.append(f"  - {point.get('area')}: {point.get('issue')}")

        # Transcript snippet
        if analysis.transcript:
            snippet = analysis.transcript[:300]
            lines.append(f"Transcript preview: {snippet}...")

        return "\n".join(lines)

    def _build_user_message(self, message: str, context: str) -> str:
        """
        Inject analysis context into the first message only.
        Subsequent messages are sent as-is (context already in history).
        """
        if context and len(self._conversation_history) == 0:
            return f"{context}\n\n[USER QUESTION]: {message}"
        return message

    # ── Suggestion extraction ────────────────────────────────────────────────

    def _extract_suggestions(self, reply: str) -> list[str] | None:
        """
        Extract quick-action suggestions from the coach reply.
        These are shown as tappable buttons in the UI.
        """
        # Look for numbered lists or bullet points in the reply
        suggestions = []

        # Pattern: lines starting with number or bullet
        lines = reply.split("\n")
        for line in lines:
            line = line.strip()
            if re.match(r"^[\d]+[.)]\s+", line):
                # Remove the number prefix
                clean = re.sub(r"^[\d]+[.)]\s+", "", line)
                if 10 < len(clean) < 100:
                    suggestions.append(clean)

        # If no list found, suggest common follow-up questions
        if not suggestions:
            suggestions = [
                "Give me a practice exercise",
                "What should I focus on first?",
                "How do I reduce filler words?",
                "Explain my pace score",
            ]

        return suggestions[:4]  # max 4 suggestions
