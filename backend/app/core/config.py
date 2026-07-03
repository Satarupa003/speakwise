from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SpeakWise"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/speakwise.db"

    # Storage paths
    SPEAKER_VIDEOS_DIR: Path = BASE_DIR / "data" / "speaker_videos"
    USER_UPLOADS_DIR: Path = BASE_DIR / "data" / "user_uploads"
    ANALYSIS_OUTPUT_DIR: Path = BASE_DIR / "data" / "analysis_output"
    KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "data" / "knowledge_base"

    # API Keys
    ANTHROPIC_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Whisper model size: tiny / base / small / medium / large
    # Start with "base" — fast and accurate enough for dev
    WHISPER_MODEL: str = "base"

    # ChromaDB collection names
    CHROMA_SPEAKER_COLLECTION: str = "speaker_patterns"
    CHROMA_USER_COLLECTION: str = "user_analyses"

    # Max video file size in MB
    MAX_VIDEO_SIZE_MB: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directories exist on startup
for d in [
    settings.SPEAKER_VIDEOS_DIR,
    settings.USER_UPLOADS_DIR,
    settings.ANALYSIS_OUTPUT_DIR,
    settings.KNOWLEDGE_BASE_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)
