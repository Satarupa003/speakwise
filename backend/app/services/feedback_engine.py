"""
FeedbackEngine — local Ollama mentor (text-only pipeline)
==========================================================
Runs 3 SMALL focused calls instead of one giant prompt — small local
models (llama3.2 3B) handle short prompts far more reliably.

Call 1: professional rewrite (the star feature)
Call 2: framework breakdown + what worked + challenge questions
Call 3: coaching points + micro-feedback + next topic
"""

import json
import re
from typing import Any

OLLAMA_MODEL = "llama3.2"

FRAMEWORKS = {
    "interview":    {"name": "STAR",                     "parts": ["Situation", "Task", "Action", "Result"]},
    "presentation": {"name": "Pyramid Principle",        "parts": ["Main Message", "Key Arguments", "Supporting Evidence"]},
    "speech":       {"name": "Storytelling Arc",         "parts": ["Hook", "Context", "Conflict", "Resolution", "Call to Action"]},
    "storytelling": {"name": "Storytelling Arc",         "parts": ["Hook", "Context", "Conflict", "Resolution", "Call to Action"]},
    "discussion":   {"name": "PREP",                     "parts": ["Point", "Reason", "Example", "Point (restate)"]},
    "debate":       {"name": "Claim-Evidence-Rebuttal",  "parts": ["Claim", "Evidence", "Rebuttal"]},
    "pitch":        {"name": "Problem-Solution-Benefit", "parts": ["Problem", "Solution", "Benefit", "Call to Action"]},
    "leadership":   {"name": "Vision-Story-Action",      "parts": ["Vision", "Why It Matters", "Story", "Action"]},
    "corporate":    {"name": "Pyramid Principle",        "parts": ["Main Message", "Key Arguments", "Supporting Evidence"]},
    "social":       {"name": "Storytelling Arc",         "parts": ["Hook", "Context", "Conflict", "Resolution", "Call to Action"]},
    "humor":        {"name": "Setup-Punchline-Callback", "parts": ["Setup", "Punchline", "Callback"]},
    "custom":       {"name": "Opening-Body-Closing",     "parts": ["Opening", "Body", "Closing"]},
}

YOUTUBE = {
    "structure":  {"speaker": "Nancy Duarte", "title": "The Secret Structure of Great Talks",
                   "url": "https://www.youtube.com/watch?v=1nYFpuc2Umk",
                   "why": "The hero's-journey structure behind every great speech."},
    "delivery":   {"speaker": "Julian Treasure", "title": "How to Speak so People Want to Listen",
                   "url": "https://www.youtube.com/watch?v=eIho2S0ZahI",
                   "why": "Masterclass in pace, pause and vocal register."},
    "clarity":    {"speaker": "Ken Robinson", "title": "Do Schools Kill Creativity",
                   "url": "https://www.youtube.com/watch?v=iG9CE55wbtY",
                   "why": "Short sentences and concrete examples keep ideas clear."},
    "engagement": {"speaker": "Hans Rosling", "title": "The Best Stats You've Ever Seen",
                   "url": "https://www.youtube.com/watch?v=hVimVzgtD6w",
                   "why": "Turning dry material into gripping storytelling."},
    "interview":  {"speaker": "Linda Raynier", "title": "How to Answer Tell Me About Yourself",
                   "url": "https://www.youtube.com/watch?v=kayOhGRcNt4",
                   "why": "A structured, confident interview answer demonstrated."},
    "discussion": {"speaker": "Conor Neill", "title": "The Secret to Great Speeches",
                   "url": "https://www.youtube.com/watch?v=9-Doa51RErM",
                   "why": "PREP demonstrated - Point, Reason, Example, Point."},
}


def _chat(prompt: str, temperature: float = 0.4) -> str:
    """Call local Ollama. Works with both new (Pydantic) and old (dict) clients."""
    import ollama
    resp = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    try:
        return resp.message.content
    except AttributeError:
        return resp["message"]["content"]


def _json(raw: str):
    """Robust JSON extraction from a small model's output."""
    raw = re.sub(r"```json\s*|```\s*", "", (raw or "").strip())
    try:
        return json.loads(raw)
    except Exception:
        pass
    # fall back: grab the outermost {...}
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except Exception:
            pass
    return None


class FeedbackEngine:

    async def generate(self, audio: dict, visual: dict, nlp: dict, scores: dict,
                       emotions: list, content_type: str = "speech",
                       topic: str = "", slides_text: str = "",
                       comparison: dict | None = None) -> dict[str, Any]:

        scenario = content_type if content_type in FRAMEWORKS else "speech"
        fw = FRAMEWORKS[scenario]
        transcript = (audio.get("transcript") or "").strip()
        print(f"[FeedbackEngine] {content_type} -> {fw['name']} (Ollama {OLLAMA_MODEL})")

        stats = (f"{audio.get('duration_seconds', 0):.0f}s, "
                 f"{audio.get('words_per_minute', 0):.0f} WPM (ideal 120-160), "
                 f"{audio.get('filler_word_count', 0)} filler words "
                 f"({audio.get('filler_word_rate', 0):.1f}/min), "
                 f"{audio.get('pause_count', 0)} pauses")

        out: dict[str, Any] = {}
        out.update(self._rewrite(transcript, fw, topic, scenario))
        out.update(self._breakdown(transcript, fw, stats, scenario))
        out.update(self._coaching(transcript, stats, scenario))

        clips = [YOUTUBE[k] for k in (scenario, "structure", "delivery") if k in YOUTUBE]
        seen, uniq = set(), []
        for c in clips:
            if c["url"] not in seen:
                uniq.append(c); seen.add(c["url"])

        out.update({
            "scenario": scenario, "content_type": content_type,
            "framework": fw, "reference_clips": uniq[:3],
            "feedback_summary": out.get("overall_assessment", ""),
            "audience_perception": out.get("audience_perception", ""),
            "framework_recommendation": {}, "emotional_presence": {},
            "delivery_observations": [], "body_language_observations": [],
        })
        print(f"[FeedbackEngine] Done - rewrite {len(out.get('polished_version',''))} chars, "
              f"{len(out.get('improvement_points', []))} coaching points")
        return out

    # ── Call 1 — the professional rewrite ────────────────────────────────
    def _rewrite(self, transcript, fw, topic, scenario) -> dict:
        prompt = f"""You are an expert communication coach.

A speaker gave a {scenario} on: {topic or "an unspecified topic"}

THEIR SPEECH:
{transcript[:1800]}

Rewrite this speech the way a highly effective professional communicator would deliver it.
Keep the same topic, same argument, same intent. Improve structure, wording, flow and persuasion.
Apply the {fw['name']} framework ({" -> ".join(fw['parts'])}).
Write at least 150 words. Write ONLY the rewritten speech - no preamble, no notes, no quotes."""
        try:
            text = _chat(prompt, 0.5).strip()
            text = re.sub(r'^(here\'?s|here is)[^\n:]*:\s*', '', text, flags=re.I).strip('"\n ')
            if len(text) < 80:
                raise ValueError("rewrite too short")
            return {"polished_version": text}
        except Exception as e:
            print(f"[FeedbackEngine] rewrite failed: {e}")
            return {"polished_version": "Rewrite unavailable - the local model did not return usable output. Try re-running the analysis."}

    # ── Call 2 — framework breakdown + strengths + challenges ────────────
    def _breakdown(self, transcript, fw, stats, scenario) -> dict:
        parts = ", ".join(fw["parts"])
        prompt = f"""You are a communication coach reviewing a {scenario}.

SPEECH: {transcript[:1200]}
SPEAKING DATA: {stats}

Framework: {fw['name']} with parts: {parts}

Reply with ONLY this JSON, no other text:
{{"overall_assessment":"2 warm sentences about how they did",
"overall_score_label":"e.g. Solid attempt - 7/10",
"framework_breakdown":[{{"part":"<one of: {parts}>","status":"present or weak or missing","observation":"what they did for this part","verdict":"one of: OK Strong | Needs work | Missing"}}],
"what_worked_well":["specific strength 1","strength 2","strength 3"],
"challenge_questions":["tough question an interviewer would ask","another"],
"audience_perception":"2 sentences on how listeners likely perceived them"}}

Include one framework_breakdown entry for EACH part: {parts}"""
        d = _json(_chat(prompt, 0.3)) or {}
        if not d.get("framework_breakdown"):
            d["framework_breakdown"] = [{"part": p, "status": "weak",
                                         "observation": "Not clearly identified in this attempt.",
                                         "verdict": "Needs work"} for p in fw["parts"]]
        return {
            "overall_assessment": d.get("overall_assessment", "Good practice attempt - keep going."),
            "overall_score_label": d.get("overall_score_label", ""),
            "framework_breakdown": d.get("framework_breakdown", []),
            "what_worked_well": d.get("what_worked_well", []),
            "challenge_questions": d.get("challenge_questions", []),
            "audience_perception": d.get("audience_perception", ""),
        }

    # ── Call 3 — coaching points + micro-feedback + next topic ───────────
    def _coaching(self, transcript, stats, scenario) -> dict:
        prompt = f"""You are a communication coach.

SPEECH: {transcript[:1200]}
SPEAKING DATA: {stats}

Reply with ONLY this JSON, no other text:
{{"improvement_points":[{{"area":"clarity or structure or delivery or confidence or engagement","what_happened":"specific observation using the data","why_it_matters":"impact on the listener","how_to_fix":"concrete technique","practice_exercise":"a 5-10 minute exercise"}}],
"micro_feedback":[{{"observation":"a repeated word, vague claim or weak transition you noticed","before":"their actual phrasing","after":"improved phrasing"}}],
"next_practice_topic":"a harder related topic and why it helps",
"motivational_close":"one encouraging sentence"}}

Give 2-3 improvement_points and 2 micro_feedback items."""
        d = _json(_chat(prompt, 0.3)) or {}
        return {
            "improvement_points": d.get("improvement_points", []),
            "micro_feedback": d.get("micro_feedback", []),
            "next_practice_topic": d.get("next_practice_topic", ""),
            "motivational_close": d.get("motivational_close", "Every practice session makes you sharper."),
        }
