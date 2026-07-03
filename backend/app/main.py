from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import videos, analyses, coach, progress, pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("✓ Database initialized")
    yield
    # Shutdown
    print("Server shutting down")


app = FastAPI(
    title="SpeakWise API",
    description="AI-powered public speaking coach backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(videos.router,   prefix="/api/v1/videos",   tags=["Videos"])
app.include_router(analyses.router, prefix="/api/v1/analyses", tags=["Analyses"])
app.include_router(coach.router,    prefix="/api/v1/coach",    tags=["Coach"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["Progress"])
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pipeline"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
