"""
KnowledgeBase
=============
Stores great speaker patterns in ChromaDB vector database.
Enables semantic search to find reference clips matching
specific improvement areas.

How it works:
  1. When a great speaker video is ingested, we extract
     audio features and store them with metadata in ChromaDB.
  2. When a user needs feedback, we query ChromaDB to find
     the most similar great speaker moments for each weakness.

Collections:
  - speaker_patterns: one entry per reference video
    stored with: speaker name, title, metrics, transcript summary
"""

import json
from typing import Any

import chromadb
from chromadb.config import Settings

from app.core.config import settings as app_settings


class KnowledgeBase:

    def __init__(self):
        self._client = None
        self._collection = None

    # ── Setup ────────────────────────────────────────────────────────────────

    def _get_collection(self):
        """Lazy-init ChromaDB client and collection."""
        if self._collection is not None:
            return self._collection

        self._client = chromadb.PersistentClient(
            path=str(app_settings.KNOWLEDGE_BASE_DIR),
        )

        self._collection = self._client.get_or_create_collection(
            name=app_settings.CHROMA_SPEAKER_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    # ── Ingest ───────────────────────────────────────────────────────────────

    async def add_speaker(
        self,
        video_id: str,
        speaker_name: str,
        title: str,
        audio_data: dict[str, Any],
        file_path: str,
    ) -> None:
        """
        Store a great speaker's analysis in the knowledge base.
        Creates a searchable entry with their metrics as the embedding vector.
        """
        collection = self._get_collection()

        # Build a feature vector from audio metrics
        # This is what ChromaDB uses to find similar speakers
        embedding = self._build_embedding(audio_data)

        # Store rich metadata for retrieval
        metadata = {
            "video_id":         video_id,
            "speaker_name":     speaker_name,
            "title":            title,
            "file_path":        file_path,
            "words_per_minute": audio_data.get("words_per_minute", 0),
            "filler_rate":      audio_data.get("filler_word_rate", 0),
            "pause_count":      audio_data.get("pause_count", 0),
            "pitch_variation":  audio_data.get("pitch_variation", 0),
            "volume_variation": audio_data.get("volume_variation", 0),
            "duration":         audio_data.get("duration_seconds", 0),
            "transcript_preview": (audio_data.get("transcript", "")[:500]),
        }

        # Document text — used for text-based search
        document = (
            f"Speaker: {speaker_name}. "
            f"Talk: {title}. "
            f"WPM: {metadata['words_per_minute']:.0f}. "
            f"Filler rate: {metadata['filler_rate']:.1f}/min. "
            f"Pitch variation: {metadata['pitch_variation']:.1f}Hz. "
            f"Preview: {metadata['transcript_preview']}"
        )

        collection.upsert(
            ids=[video_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata],
        )

        print(f"[KnowledgeBase] ✓ Added: {speaker_name} — {title}")

    # ── Query ────────────────────────────────────────────────────────────────

    async def find_similar_speakers(
        self,
        target_metrics: dict[str, float],
        n_results: int = 3,
    ) -> list[dict]:
        """
        Find great speakers whose metrics are similar to the target.
        Used to find reference clips for specific improvement areas.

        target_metrics: dict with keys matching the embedding features
        """
        collection = self._get_collection()

        if collection.count() == 0:
            print("[KnowledgeBase] No speakers in knowledge base yet")
            return []

        query_embedding = self._build_embedding(target_metrics)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        speakers = []
        for i, meta in enumerate(results["metadatas"][0]):
            speakers.append({
                "video_id":     meta["video_id"],
                "speaker_name": meta["speaker_name"],
                "title":        meta["title"],
                "file_path":    meta["file_path"],
                "similarity":   round(1 - results["distances"][0][i], 3),
                "metrics": {
                    "words_per_minute": meta["words_per_minute"],
                    "filler_rate":      meta["filler_rate"],
                    "pitch_variation":  meta["pitch_variation"],
                },
            })

        return speakers

    async def find_by_skill(
        self,
        skill: str,
        n_results: int = 3,
    ) -> list[dict]:
        """
        Find great speakers who excel at a specific skill.

        skill: one of "pace", "clarity", "confidence",
                       "engagement", "storytelling", "body_language"
        """
        collection = self._get_collection()

        if collection.count() == 0:
            return []

        # Build a query embedding representing ideal metrics for this skill
        ideal = self._ideal_metrics_for_skill(skill)
        query_embedding = self._build_embedding(ideal)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        speakers = []
        for i, meta in enumerate(results["metadatas"][0]):
            speakers.append({
                "video_id":     meta["video_id"],
                "speaker_name": meta["speaker_name"],
                "title":        meta["title"],
                "file_path":    meta["file_path"],
                "skill":        skill,
                "similarity":   round(1 - results["distances"][0][i], 3),
                "timestamp":    0.0,  # start of video as default
                "reason": (
                    f"{meta['speaker_name']} is a great reference "
                    f"for {skill} in '{meta['title']}'"
                ),
            })

        return speakers

    async def get_all_speakers(self) -> list[dict]:
        """Return all speakers in the knowledge base."""
        collection = self._get_collection()

        if collection.count() == 0:
            return []

        results = collection.get(include=["metadatas"])
        return [
            {
                "video_id":     m["video_id"],
                "speaker_name": m["speaker_name"],
                "title":        m["title"],
                "duration":     m.get("duration", 0),
            }
            for m in results["metadatas"]
        ]

    async def remove_speaker(self, video_id: str) -> None:
        """Remove a speaker from the knowledge base."""
        collection = self._get_collection()
        collection.delete(ids=[video_id])
        print(f"[KnowledgeBase] Removed speaker: {video_id}")

    def count(self) -> int:
        """Return number of speakers in knowledge base."""
        return self._get_collection().count()

    # ── Embedding ────────────────────────────────────────────────────────────

    def _build_embedding(self, metrics: dict) -> list[float]:
        """
        Convert analysis metrics into a fixed-size embedding vector.
        ChromaDB uses this to compute similarity between speakers.

        We normalize each metric to 0-1 range so no single metric
        dominates the similarity calculation.
        """
        def clamp(val, min_val, max_val):
            return max(0.0, min(1.0, (val - min_val) / (max_val - min_val)))

        wpm       = metrics.get("words_per_minute", 130)
        filler    = metrics.get("filler_word_rate", 0)
        pauses    = metrics.get("pause_count", 5)
        pitch_var = metrics.get("pitch_variation", 30)
        vol_var   = metrics.get("volume_variation", 0.03)
        duration  = metrics.get("duration_seconds", 60)

        embedding = [
            clamp(wpm,       60,   220),   # speaking pace
            clamp(filler,    0,    20),    # filler rate (inverted below)
            clamp(pauses,    0,    30),    # pause frequency
            clamp(pitch_var, 0,    100),   # pitch expressiveness
            clamp(vol_var,   0,    0.1),   # volume dynamics
            clamp(duration,  30,   3600),  # talk length
            # Inverted filler (high score = low fillers = good)
            1.0 - clamp(filler, 0, 20),
        ]

        return embedding

    def _ideal_metrics_for_skill(self, skill: str) -> dict:
        """
        Return ideal metric values for each skill.
        Used to query for the best reference speakers per skill.
        """
        ideals = {
            "pace": {
                "words_per_minute": 140,
                "pause_count":      8,
                "filler_word_rate": 1,
            },
            "clarity": {
                "filler_word_rate": 0.5,
                "words_per_minute": 130,
            },
            "confidence": {
                "volume_variation": 0.03,
                "pitch_variation":  35,
            },
            "engagement": {
                "pitch_variation":  60,
                "words_per_minute": 145,
            },
            "storytelling": {
                "words_per_minute": 135,
                "pause_count":      10,
                "pitch_variation":  45,
            },
            "body_language": {
                "words_per_minute": 130,
                "pitch_variation":  40,
            },
        }
        return ideals.get(skill, ideals["pace"])
