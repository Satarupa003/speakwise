"""
CoachEngine — long-term AI communication mentor
================================================
History-aware chat backed by local Ollama (llama3.2).
Matches the same Ollama pattern used in feedback_engine.py.

Conversation history is kept as a list of {role, content} messages and
replayed on every call — the Ollama Python client has no stateful start_chat().
The system prompt + analysis context are injected once on the first turn;
subsequent turns send only the accumulated history so the 3B model stays focused.
"""

import re
from typing import Any

from app.schemas.schemas import CoachResponse

OLLAMA_MODEL = "llama3.2"

SYSTEM_PROMPT = (
    "You are SpeakWise Coach — a warm, expert communication mentor (not a generic chatbot). "
    "You know the speaker's full analysis: scores, delivery, body language, emotions, framework "
    "performance, and progress trends. Be supportive and specific. Reference their actual data. "
    "Give concrete exercises. Keep replies to 2-4 short paragraphs. "
    "You can: explain why they appeared nervous/uncertain, give confidence/eye-contact drills, "
    "rewrite answers using STAR/PREP, simulate a manager interview, and track progress over time. "
    "Always end with encouragement or a clear next step."
)

MAX_HISTORY = 20   # messages (role pairs) to keep in context


def _ollama_chat(messages: list[dict], temperature: float = 0.5) -> str:
    """Call local Ollama. Works with both new (Pydantic) and old (dict) client returns."""
    import ollama
    resp = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature},
    )
    try:
        return resp.message.content.strip()
    except AttributeError:
        return resp["message"]["content"].strip()


class CoachEngine:

    def __init__(self):
        self._history: list[dict] = []   # [{role, content}, ...]
        self._context_injected = False

    async def chat(self, message: str, analysis: Any = None, history_summary: str = "") -> CoachResponse:
        try:
            # Build the full message list for this turn
            messages = []

            # System prompt always first
            messages.append({"role": "system", "content": SYSTEM_PROMPT})

            # On very first turn, prepend the analysis context into the user message
            if not self._context_injected:
                ctx = self._build_context(analysis, history_summary)
                user_content = f"{ctx}\n\n{message}" if ctx else message
                self._context_injected = True
            else:
                user_content = message

            # Replay existing history, then append this new user turn
            messages.extend(self._history)
            messages.append({"role": "user", "content": user_content})

            # Trim if too long (keep system + last MAX_HISTORY entries)
            if len(messages) > MAX_HISTORY + 1:
                messages = [messages[0]] + messages[-(MAX_HISTORY):]

            print(f"[CoachEngine] Sending {len(messages)} messages to Ollama ({OLLAMA_MODEL})")
            reply = _ollama_chat(messages)

            # Persist history (without system prompt — it's always prepended fresh)
            self._history.append({"role": "user",      "content": user_content})
            self._history.append({"role": "assistant",  "content": reply})
            if len(self._history) > MAX_HISTORY:
                self._history = self._history[-MAX_HISTORY:]

            return CoachResponse(
                reply=reply,
                suggestions=self._suggestions(reply),
            )

        except Exception as e:
            print(f"[CoachEngine] error: {e}")
            return CoachResponse(
                reply=(
                    "I'm having trouble connecting right now — make sure Ollama is running "
                    "(`ollama serve`) and that the llama3.2 model is pulled (`ollama pull llama3.2`)."
                ),
                suggestions=[
                    "Why did I appear nervous?",
                    "Give me a confidence exercise",
                    "Rewrite my answer using STAR",
                    "Simulate a manager interview",
                ],
            )

    def reset_conversation(self):
        self._history = []
        self._context_injected = False

    # ── helpers ──────────────────────────────────────────────────────────────

    def _build_context(self, a: Any, history_summary: str) -> str:
        if a is None:
            return ""
        parts = ["[YOUR ANALYSIS RESULTS]"]
        if a.overall_score is not None:
            parts.append(
                f"Overall {a.overall_score}/100 | Confidence {a.confidence_score} | "
                f"Delivery {a.delivery_score} | Body Language {a.body_language_score} | "
                f"Emotional Presence {a.emotional_presence_score}"
            )
        if a.words_per_minute is not None:
            parts.append(
                f"{a.words_per_minute} WPM, {a.filler_word_count} filler words "
                f"({a.filler_word_rate}/min), {a.pause_count} pauses"
            )
        if a.emotions:
            parts.append(
                "Signals: " + "; ".join(
                    f"{e.get('emotion')} ({e.get('level')})" for e in (a.emotions or [])[:4]
                )
            )
        if a.feedback_summary:
            parts.append(f"Assessment: {a.feedback_summary}")
        if a.scenario:
            parts.append(f"Scenario: {a.scenario}  |  Topic: {a.topic or 'not specified'}")
        if history_summary:
            parts.append(f"[PROGRESS HISTORY]\n{history_summary}")
        return "\n".join(parts)

    def _suggestions(self, reply: str) -> list[str]:
        out = []
        for line in reply.split("\n"):
            line = line.strip()
            if re.match(r"^[\d]+[.)]\s+", line):
                c = re.sub(r"^[\d]+[.)]\s+", "", line)
                if 10 < len(c) < 120:
                    out.append(c)
        if not out:
            out = [
                "Why did I appear nervous?",
                "Give me a confidence drill",
                "Rewrite my answer using STAR",
                "Simulate a tough interview question",
            ]
        return out[:4]

