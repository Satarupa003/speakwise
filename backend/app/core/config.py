from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    APP_NAME: str = "SpeakWise"
    DEBUG: bool = False

    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/speakwise.db"

    SPEAKER_VIDEOS_DIR: Path = BASE_DIR / "data" / "speaker_videos"
    USER_UPLOADS_DIR: Path = BASE_DIR / "data" / "user_uploads"
    SLIDES_DIR: Path = BASE_DIR / "data" / "slides"
    ANALYSIS_OUTPUT_DIR: Path = BASE_DIR / "data" / "analysis_output"
    KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "data" / "knowledge_base"
    MODELS_DIR: Path = BASE_DIR / "data" / "models"

    # API keys
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"          # falls back automatically
    GEMINI_FALLBACK_MODEL: str = "gemini-2.0-flash"

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    WHISPER_MODEL: str = "base"
    CHROMA_SPEAKER_COLLECTION: str = "speaker_patterns"
    CHROMA_MEMORY_COLLECTION: str = "user_memory"
    MAX_VIDEO_SIZE_MB: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

for d in [settings.SPEAKER_VIDEOS_DIR, settings.USER_UPLOADS_DIR, settings.SLIDES_DIR,
          settings.ANALYSIS_OUTPUT_DIR, settings.KNOWLEDGE_BASE_DIR, settings.MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
