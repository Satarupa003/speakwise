"""
CoachEngine — long-term AI communication mentor
================================================
History-aware chat. Has access to the current analysis plus a summary of
previous sessions/trends, and behaves like a mentor, not a generic bot.
"""

import re
from typing import Any

from app.core.config import settings
from app.schemas.schemas import CoachResponse

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

SYSTEM_PROMPT = """You are SpeakWise Coach — a warm, expert, long-term communication mentor (not a generic chatbot).
You know the speaker's full analysis: scores, delivery, body language, emotions, framework performance, and progress trends.
Be supportive and specific. Reference their actual data. Give concrete exercises. Keep replies to 2-4 short paragraphs.
You can: explain why they appeared nervous/uncertain, give confidence/eye-contact drills, rewrite answers using STAR/PREP, simulate a manager interview, and track progress over time.
Always end with encouragement or a clear next step."""


class CoachEngine:

    def __init__(self):
        self._genai = None
        self._history = []

    def _load(self):
        if self._genai is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._genai = genai

    def _model(self):
        self._load()
        for name in GEMINI_MODELS:
            try:
                return self._genai.GenerativeModel(name, system_instruction=SYSTEM_PROMPT)
            except Exception as e:
                print(f"[CoachEngine] {name} init failed: {e}")
        raise RuntimeError("All Gemini models failed")

    async def chat(self, message: str, analysis: Any = None, history_summary: str = "") -> CoachResponse:
        try:
            model = self._model()
            ctx = self._context(analysis, history_summary)
            user_msg = f"{ctx}\n\nUser: {message}" if (ctx and not self._history) else message
            self._history.append({"role": "user", "parts": [user_msg]})
            if len(self._history) > 20:
                self._history = self._history[-20:]

            chat = model.start_chat(history=self._history[:-1])
            reply = chat.send_message(user_msg).text.strip()
            self._history.append({"role": "model", "parts": [reply]})
            return CoachResponse(reply=reply, suggestions=self._suggestions(reply), referenced_clips=None)
        except Exception as e:
            print(f"[CoachEngine] error: {e}")
            return CoachResponse(
                reply="I'm having trouble connecting right now — please check the Gemini API key and try again.",
                suggestions=None, referenced_clips=None)

    def reset_conversation(self):
        self._history = []

    def _context(self, a, history_summary):
        if a is None:
            return ""
        L = ["[CURRENT ANALYSIS]"]
        if a.overall_score is not None:
            L.append(f"Overall {a.overall_score}/100 | Confidence {a.confidence_score} | "
                     f"Delivery {a.delivery_score} | Body Language {a.body_language_score} | "
                     f"Emotional Presence {a.emotional_presence_score}")
        if a.words_per_minute is not None:
            L.append(f"{a.words_per_minute} WPM, {a.filler_word_count} fillers "
                     f"({a.filler_word_rate}/min), eye contact {a.eye_contact_score}%")
        if a.behavioral_patterns:
            L.append(f"Body-language patterns: {', '.join(a.behavioral_patterns)}")
        if a.emotions:
            L.append("Emotions: " + "; ".join(
                f"{e.get('emotion')} ({e.get('level')})" for e in a.emotions[:6]))
        if a.feedback_summary:
            L.append(f"Assessment: {a.feedback_summary}")
        if a.scenario:
            L.append(f"Scenario: {a.scenario}, topic: {a.topic or 'n/a'}")
        if history_summary:
            L.append(f"[PROGRESS HISTORY]\n{history_summary}")
        return "\n".join(L)

    def _suggestions(self, reply):
        out = []
        for line in reply.split("\n"):
            line = line.strip()
            if re.match(r"^[\d]+[.)]\s+", line):
                c = re.sub(r"^[\d]+[.)]\s+", "", line)
                if 10 < len(c) < 100:
                    out.append(c)
        if not out:
            out = ["Why did I appear nervous?", "Give me a confidence exercise",
                   "Rewrite my answer using STAR", "Simulate a manager interview"]
        return out[:4]
