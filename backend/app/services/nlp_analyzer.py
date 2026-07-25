"""
NLPAnalyzer — MINIMAL pure-Python text stats
=============================================
No spaCy, no LanguageTool, no numpy. Just sentence/vocabulary stats
computed with the standard library. Deep language judgement is left
to the LLM in FeedbackEngine.
"""
import re
import statistics
from collections import Counter
from typing import Any

POSITIVE = {"great","amazing","excellent","wonderful","love","best","powerful",
            "inspiring","success","achieve","hope","believe","opportunity","grow"}
NEGATIVE = {"bad","terrible","awful","fail","problem","difficult","hard",
            "struggle","fear","worry","crisis","wrong","never","impossible"}
STOP = {"the","a","an","and","or","but","is","are","was","were","to","of","in",
        "on","for","with","that","this","it","i","you","we","they","he","she",
        "be","as","at","by","from","so","if","my","me","have","has","had","do"}


class NLPAnalyzer:

    async def analyze(self, transcript: str, segments: list[dict] | None = None) -> dict[str, Any]:
        if not transcript or not transcript.strip():
            return self._empty()
        print(f"[NLPAnalyzer] Analyzing transcript ({len(transcript)} chars)")

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if s.strip()]
        words = re.findall(r"[a-zA-Z']+", transcript.lower())

        lengths = [len(s.split()) for s in sentences] or [0]
        variety = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
        unique = set(words)
        ttr = len(unique) / len(words) if words else 0.0
        content = [w for w in words if w not in STOP]

        result = {
            "sentence_structure": {
                "total_sentences": len(sentences),
                "avg_sentence_length": round(statistics.fmean(lengths), 1) if lengths else 0,
                "sentence_length_std": round(variety, 1),
                "questions": sum(1 for s in sentences if s.endswith("?")),
                "exclamations": sum(1 for s in sentences if s.endswith("!")),
                "variety_score": min(100.0, round(variety * 5, 1)),
            },
            "vocabulary": {
                "total_words": len(words),
                "unique_words": len(unique),
                "ttr": round(ttr, 3),
                "ttr_score": round(min(100.0, ttr * 150), 1),
                "top_words": [w for w, _ in Counter(content).most_common(10)],
            },
            "repeated_words": [w for w, c in Counter(content).most_common(5) if c >= 4],
            "emotional_arc": self._arc(segments, transcript),
            "opening_strength": self._opening(transcript),
            "closing_strength": self._closing(transcript),
            "grammar_errors": {"error_count": 0, "errors": []},
            "clarity_score": 60.0, "storytelling_score": 60.0, "persuasion_score": 60.0,
            "key_themes": [], "nlp_feedback": "", "structure_feedback": "",
            "strongest_moment": "", "weakest_moment": "",
        }
        print(f"[NLPAnalyzer] Done - {len(sentences)} sentences, {len(unique)} unique words")
        return result

    def _arc(self, segments, transcript):
        if not segments:
            third = max(len(transcript) // 3, 1)
            segments = [{"start": 0, "end": 1, "text": transcript[:third]},
                        {"start": 1, "end": 2, "text": transcript[third:2 * third]},
                        {"start": 2, "end": 3, "text": transcript[2 * third:]}]
        arc = []
        for seg in segments:
            ws = (seg.get("text") or "").lower().split()
            if not ws:
                continue
            score = (sum(w in POSITIVE for w in ws) - sum(w in NEGATIVE for w in ws)) / len(ws) * 100
            arc.append({"start": seg.get("start", 0), "end": seg.get("end", 0),
                        "tone": "positive" if score > 2 else "negative" if score < -2 else "neutral",
                        "sentiment_score": round(score, 2)})
        return arc

    def _opening(self, t):
        w = t.split()
        head = " ".join(w[:max(1, len(w) // 7)]).lower()
        s = 50.0
        if "?" in head: s += 20
        if any(k in head for k in ("imagine", "picture", "story")): s += 15
        if any(c.isdigit() for c in head): s += 10
        if head.startswith(("hi ", "hello ", "my name", "today i")): s -= 20
        return round(min(100, max(0, s)), 1)

    def _closing(self, t):
        w = t.split()
        tail = " ".join(w[-max(1, len(w) // 7):]).lower()
        s = 50.0
        if any(k in tail for k in ("start", "begin", "try", "join")): s += 20
        if "thank you" in tail: s -= 10
        if "?" in tail: s += 15
        if any(k in tail for k in ("together", "future", "now")): s += 15
        return round(min(100, max(0, s)), 1)

    def _empty(self):
        return {"sentence_structure": {}, "vocabulary": {}, "repeated_words": [],
                "emotional_arc": [], "opening_strength": 0.0, "closing_strength": 0.0,
                "grammar_errors": {"error_count": 0, "errors": []},
                "clarity_score": 0.0, "storytelling_score": 0.0, "persuasion_score": 0.0,
                "key_themes": [], "nlp_feedback": "No transcript available.",
                "structure_feedback": "", "strongest_moment": "", "weakest_moment": ""}
