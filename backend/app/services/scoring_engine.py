"""
ScoringEngine — text/voice-timing only (visual dimensions disabled)
Body-language and emotional-presence scores return None so the UI can hide them.
"""
from typing import Any

IDEAL_MIN, IDEAL_MAX = 120, 160


class ScoringEngine:
    def compute(self, audio: dict, visual: dict, nlp: dict) -> dict[str, Any]:
        print("[ScoringEngine] Computing scores (text + voice timing)...")
        pace = self._pace(audio)
        clarity = self._avg([self._filler(audio),
                             (nlp.get("sentence_structure") or {}).get("variety_score", 50)])
        structure = self._avg([nlp.get("opening_strength", 50), nlp.get("closing_strength", 50),
                               (nlp.get("sentence_structure") or {}).get("variety_score", 50)])
        content = self._avg([(nlp.get("vocabulary") or {}).get("ttr_score", 50), clarity])
        delivery = self._avg([pace, self._filler(audio)])
        engagement = self._avg([(nlp.get("sentence_structure") or {}).get("variety_score", 50), pace])
        professionalism = self._avg([self._filler(audio), pace])
        confidence = self._avg([self._filler(audio), pace, structure])

        overall = round(self._avg([content, structure, delivery, confidence,
                                   engagement, professionalism]), 1)
        s = {
            "overall": overall,
            "content_quality": round(content, 1), "structure": round(structure, 1),
            "delivery": round(delivery, 1), "confidence": round(confidence, 1),
            "engagement": round(engagement, 1), "professionalism": round(professionalism, 1),
            "emotional_presence": None,   # needs audio pitch - disabled
            "body_language": None,        # needs video - disabled
            "pace": round(pace, 1), "clarity": round(clarity, 1),
        }
        print(f"[ScoringEngine] Overall {overall}/100")
        return s

    def _avg(self, vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else 50.0

    def _pace(self, audio):
        wpm = audio.get("words_per_minute", 0) or 0
        if wpm == 0:
            return 50.0
        if IDEAL_MIN <= wpm <= IDEAL_MAX:
            s = 90.0
        elif wpm < IDEAL_MIN:
            s = 90.0 * (wpm / IDEAL_MIN)
        else:
            s = max(20.0, 90.0 - (wpm - IDEAL_MAX) * 0.5)
        if ((audio.get("pace_sections") or {}).get("consistency", 0) or 0) > 60:
            s -= 10
        return min(100.0, max(0.0, s))

    def _filler(self, audio):
        r = audio.get("filler_word_rate", 0) or 0
        if r <= 2:
            return 100.0
        if r <= 5:
            return 100 - (r - 2) * (40 / 3)
        return max(0.0, 60 - (r - 5) * 10)
