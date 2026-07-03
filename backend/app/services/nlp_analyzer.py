"""
NLPAnalyzer
===========
Analyzes the transcript of a speech for language quality,
structure, and storytelling using spaCy + Claude API.

What it analyzes:
  1. Sentence structure   — avg length, complexity, variety
  2. Vocabulary richness  — unique words, rare words ratio
  3. Filler phrases       — "basically", "literally", "you know"
  4. Emotional arc        — sentiment per segment (positive/negative/neutral)
  5. Storytelling quality — Claude API rates the narrative structure
  6. Clarity score        — Claude API rates how easy to understand
  7. Persuasion score     — Claude API rates persuasive language

Output dict shape:
{
    "sentence_structure":   dict,
    "vocabulary":           dict,
    "filler_phrases":       dict,
    "emotional_arc":        list,
    "storytelling_score":   float,
    "clarity_score":        float,
    "persuasion_score":     float,
    "nlp_feedback":         str,
    "key_themes":           list,
    "opening_strength":     float,
    "closing_strength":     float,
}
"""

import os
import re
from typing import Any

import anthropic

from app.core.config import settings


# Filler phrases to detect in transcript (beyond single words already
# caught by the audio analyzer)
FILLER_PHRASES = [
    "basically", "literally", "actually", "honestly", "obviously",
    "you know what i mean", "at the end of the day", "to be honest",
    "kind of", "sort of", "in terms of", "the thing is",
    "what i mean is", "if you will", "as it were",
]


class NLPAnalyzer:

    def __init__(self):
        self._nlp = None          # spaCy model (lazy loaded)
        self._client = None       # Anthropic client (lazy loaded)

    # ── Public API ──────────────────────────────────────────────────────────

    async def analyze(
        self,
        transcript: str,
        segments: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Main entry point.
        transcript: full speech text
        segments:   list of {start, end, text} from Whisper
        """
        if not transcript or not transcript.strip():
            return self._empty_result()

        print(f"[NLPAnalyzer] Analyzing transcript ({len(transcript)} chars)")

        self._load_spacy()
        self._load_anthropic()

        doc = self._nlp(transcript)

        # Run local analyses (fast, no API call)
        sentence_structure = self._analyze_sentences(doc)
        vocabulary         = self._analyze_vocabulary(doc)
        filler_phrases     = self._detect_filler_phrases(transcript)
        emotional_arc      = self._analyze_emotional_arc(segments or [], doc)
        opening_strength   = self._score_opening(transcript)
        closing_strength   = self._score_closing(transcript)

        # Run Claude API analysis (richer insights)
        print("[NLPAnalyzer] Calling Claude API for deep analysis...")
        claude_analysis = await self._claude_analyze(transcript)

        result = {
            "sentence_structure":  sentence_structure,
            "vocabulary":          vocabulary,
            "filler_phrases":      filler_phrases,
            "emotional_arc":       emotional_arc,
            "opening_strength":    opening_strength,
            "closing_strength":    closing_strength,
            **claude_analysis,
        }

        print(
            f"[NLPAnalyzer] ✓ Done — "
            f"clarity: {result['clarity_score']:.0f}/100, "
            f"storytelling: {result['storytelling_score']:.0f}/100, "
            f"persuasion: {result['persuasion_score']:.0f}/100"
        )
        return result

    # ── Lazy loaders ─────────────────────────────────────────────────────────

    def _load_spacy(self):
        if self._nlp is None:
            import spacy
            print("[NLPAnalyzer] Loading spaCy model...")
            self._nlp = spacy.load("en_core_web_sm")

    def _load_anthropic(self):
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )

    # ── Sentence structure ───────────────────────────────────────────────────

    def _analyze_sentences(self, doc) -> dict:
        """
        Analyze sentence length, complexity, and variety.
        Good speakers vary sentence length — mix of short punchy
        sentences and longer explanatory ones.
        """
        sentences = list(doc.sents)
        if not sentences:
            return {}

        lengths = [len(sent) for sent in sentences]
        avg_len = sum(lengths) / len(lengths)

        # Count sentence types by ending punctuation
        questions    = sum(1 for s in sentences if str(s).strip().endswith("?"))
        exclamations = sum(1 for s in sentences if str(s).strip().endswith("!"))
        statements   = len(sentences) - questions - exclamations

        # Variety score — good if std dev is high (mix of short + long)
        import statistics
        variety = statistics.stdev(lengths) if len(lengths) > 1 else 0

        # Count clauses (rough proxy: count subordinating conjunctions)
        clause_markers = {"because", "although", "while", "when", "if",
                          "since", "unless", "after", "before", "until"}
        clause_count = sum(
            1 for token in doc
            if token.text.lower() in clause_markers
        )

        return {
            "total_sentences":      len(sentences),
            "avg_sentence_length":  round(avg_len, 1),
            "sentence_length_std":  round(variety, 1),
            "questions":            questions,
            "exclamations":         exclamations,
            "statements":           statements,
            "clause_count":         clause_count,
            "variety_score":        min(100, round(variety * 5, 1)),
        }

    # ── Vocabulary ───────────────────────────────────────────────────────────

    def _analyze_vocabulary(self, doc) -> dict:
        """
        Analyze vocabulary richness.
        Type-Token Ratio (TTR) = unique words / total words.
        Higher TTR = more varied vocabulary.
        """
        # Filter to real words only (no punctuation, no stop words for TTR)
        all_words    = [t.text.lower() for t in doc if t.is_alpha]
        content_words = [t.lemma_.lower() for t in doc
                         if t.is_alpha and not t.is_stop]

        if not all_words:
            return {}

        unique_words = set(all_words)
        ttr = len(unique_words) / len(all_words)

        # Most common content words = key themes
        from collections import Counter
        word_freq = Counter(content_words)
        top_words = [w for w, _ in word_freq.most_common(10)]

        return {
            "total_words":    len(all_words),
            "unique_words":   len(unique_words),
            "ttr":            round(ttr, 3),       # 0–1, higher is better
            "ttr_score":      round(min(100, ttr * 150), 1),
            "top_words":      top_words,
            "avg_word_length": round(
                sum(len(w) for w in all_words) / len(all_words), 1
            ),
        }

    # ── Filler phrase detection ───────────────────────────────────────────────

    def _detect_filler_phrases(self, transcript: str) -> dict:
        """
        Detect multi-word filler phrases in transcript.
        Single filler words (um, uh) are already caught by AudioAnalyzer.
        This catches phrase-level fillers like "at the end of the day".
        """
        text_lower = transcript.lower()
        found = {}

        for phrase in FILLER_PHRASES:
            count = text_lower.count(phrase)
            if count > 0:
                found[phrase] = count

        total = sum(found.values())
        return {
            "phrases_found": found,
            "total_count":   total,
        }

    # ── Emotional arc ────────────────────────────────────────────────────────

    def _analyze_emotional_arc(
        self, segments: list[dict], doc
    ) -> list[dict]:
        """
        Estimate sentiment per segment using simple lexicon approach.
        Returns a timeline of emotional tone across the speech.

        Good speeches often follow: neutral → build → peak → resolution
        """
        # Simple positive/negative word lists
        positive_words = {
            "great", "amazing", "excellent", "wonderful", "fantastic",
            "love", "best", "incredible", "powerful", "inspiring",
            "success", "achieve", "dream", "hope", "believe", "win",
            "opportunity", "grow", "transform", "change", "better",
        }
        negative_words = {
            "bad", "terrible", "awful", "fail", "problem", "difficult",
            "hard", "struggle", "fear", "worry", "crisis", "wrong",
            "never", "can't", "won't", "impossible", "weak", "lose",
        }

        if not segments:
            # Fall back to splitting doc into thirds
            text = doc.text
            third = len(text) // 3
            segments = [
                {"start": 0, "end": 1, "text": text[:third]},
                {"start": 1, "end": 2, "text": text[third:2*third]},
                {"start": 2, "end": 3, "text": text[2*third:]},
            ]

        arc = []
        for seg in segments:
            words = seg.get("text", "").lower().split()
            if not words:
                continue

            pos = sum(1 for w in words if w in positive_words)
            neg = sum(1 for w in words if w in negative_words)
            total = len(words)

            sentiment_score = (pos - neg) / max(total, 1) * 100
            if sentiment_score > 2:
                tone = "positive"
            elif sentiment_score < -2:
                tone = "negative"
            else:
                tone = "neutral"

            arc.append({
                "start":           seg.get("start", 0),
                "end":             seg.get("end", 0),
                "tone":            tone,
                "sentiment_score": round(sentiment_score, 2),
            })

        return arc

    # ── Opening / closing strength ────────────────────────────────────────────

    def _score_opening(self, transcript: str) -> float:
        """
        Score the opening of the speech (first 15% of words).
        Strong openings: questions, bold statements, stories, statistics.
        """
        words = transcript.split()
        opening = " ".join(words[:max(1, len(words) // 7)]).lower()

        score = 50.0  # baseline

        # Question hook
        if "?" in opening:
            score += 20
        # Story signal
        if any(w in opening for w in ["imagine", "picture", "story", "once", "year"]):
            score += 15
        # Statistic
        if any(c.isdigit() for c in opening):
            score += 10
        # Bold claim
        if any(w in opening for w in ["never", "always", "every", "most", "best"]):
            score += 10
        # Weak opener
        if opening.startswith(("hi ", "hello ", "my name", "today i", "i'm going")):
            score -= 20

        return round(min(100, max(0, score)), 1)

    def _score_closing(self, transcript: str) -> float:
        """
        Score the closing of the speech (last 15% of words).
        Strong closings: call to action, callback to opening, memorable quote.
        """
        words = transcript.split()
        closing = " ".join(words[-max(1, len(words) // 7):]).lower()

        score = 50.0

        # Call to action
        if any(w in closing for w in ["start", "begin", "try", "join", "share", "act"]):
            score += 20
        # Thank you (weak closer)
        if "thank you" in closing:
            score -= 10
        # Question to audience
        if "?" in closing:
            score += 15
        # Strong closing words
        if any(w in closing for w in ["together", "future", "change", "now", "today"]):
            score += 15

        return round(min(100, max(0, score)), 1)

    # ── Claude API analysis ───────────────────────────────────────────────────

    async def _claude_analyze(self, transcript: str) -> dict:
        """
        Use Claude to deeply analyze the speech transcript.
        Returns scores + feedback for storytelling, clarity, persuasion.
        """
        # Truncate very long transcripts to save tokens
        max_chars = 4000
        text = transcript[:max_chars]
        if len(transcript) > max_chars:
            text += "\n[transcript truncated for analysis]"

        prompt = f"""You are an expert public speaking coach analyzing a speech transcript.

Analyze this speech transcript and respond with ONLY a JSON object (no markdown, no explanation):

TRANSCRIPT:
{text}

Respond with exactly this JSON structure:
{{
    "storytelling_score": <0-100 integer>,
    "clarity_score": <0-100 integer>,
    "persuasion_score": <0-100 integer>,
    "key_themes": [<list of 3-5 main topics as short strings>],
    "nlp_feedback": "<2-3 sentences of specific, actionable language feedback>",
    "structure_feedback": "<1-2 sentences about speech structure>",
    "strongest_moment": "<quote or describe the strongest moment in the speech>",
    "weakest_moment": "<quote or describe the weakest moment in the speech>"
}}

Scoring guide:
- storytelling_score: Does it have narrative arc, vivid details, emotional connection?
- clarity_score: Is it easy to follow? Clear transitions? No confusing jargon?
- persuasion_score: Does it use evidence, emotion, credibility effectively?"""

        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"```\s*", "", raw)

            import json
            data = json.loads(raw)

            return {
                "storytelling_score": float(data.get("storytelling_score", 50)),
                "clarity_score":      float(data.get("clarity_score", 50)),
                "persuasion_score":   float(data.get("persuasion_score", 50)),
                "key_themes":         data.get("key_themes", []),
                "nlp_feedback":       data.get("nlp_feedback", ""),
                "structure_feedback": data.get("structure_feedback", ""),
                "strongest_moment":   data.get("strongest_moment", ""),
                "weakest_moment":     data.get("weakest_moment", ""),
            }

        except Exception as e:
            print(f"[NLPAnalyzer] Claude API error: {e}")
            return self._fallback_claude_result()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _empty_result(self) -> dict:
        """Return when transcript is empty."""
        return {
            "sentence_structure":  {},
            "vocabulary":          {},
            "filler_phrases":      {"phrases_found": {}, "total_count": 0},
            "emotional_arc":       [],
            "opening_strength":    0.0,
            "closing_strength":    0.0,
            "storytelling_score":  0.0,
            "clarity_score":       0.0,
            "persuasion_score":    0.0,
            "key_themes":          [],
            "nlp_feedback":        "No transcript available.",
            "structure_feedback":  "",
            "strongest_moment":    "",
            "weakest_moment":      "",
        }

    def _fallback_claude_result(self) -> dict:
        """Return when Claude API call fails."""
        return {
            "storytelling_score": 50.0,
            "clarity_score":      50.0,
            "persuasion_score":   50.0,
            "key_themes":         [],
            "nlp_feedback":       "AI analysis unavailable. Check your API key.",
            "structure_feedback": "",
            "strongest_moment":   "",
            "weakest_moment":     "",
        }
