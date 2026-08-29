# SpeakWise

An AI-powered communication coaching platform. Upload a video of yourself speaking, select the scenario, and get feedback on your communication.

Runs fully locally — no external API keys, no cost.

---

## What it does

- **Video upload** with scenario selection (interview, presentation, group discussion, etc.) and an optional topic field
- **Local transcription** of the speech using faster-whisper
- **Automatic scenario detection** that maps your speech to the right communication framework (STAR for interviews, PREP for discussions, Pyramid Principle for presentations, etc.)
- **Text-based scoring** across pace, clarity, structure, and delivery
- **AI-generated coaching feedback** — a framework breakdown, a rewritten version of your speech, and coaching points — produced by a locally-hosted LLM (Ollama)
- **Coach chat** to ask follow-up questions about your feedback
- **Progress tracking** across multiple practice sessions

Body language analysis and detailed audio features (pitch, volume, energy) are not currently part of the pipeline — only speaking pace, filler words, and pauses are measured from audio.

---

## Architecture

```
Video upload
    │
    ▼
faster-whisper (local, CPU)  →  transcript + word timings
    │
    ▼
Text analysis                →  sentence variety, vocabulary, opening/closing strength
    │
    ▼
Scoring engine                →  pace, clarity, structure, delivery, confidence, engagement
    │
    ▼
Ollama (local LLM, llama3.2)  →  framework breakdown, coaching feedback, rewritten speech
    │
    ▼
FastAPI + SQLite              →  stores results
    │
    ▼
React dashboard               →  displays feedback
```

**Backend:** FastAPI, SQLAlchemy (async), SQLite
**Frontend:** React, Vite, Tailwind CSS
**Transcription:** faster-whisper
**LLM:** Ollama running `llama3.2`, entirely local

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20.19+ or 22.12+
- [Ollama](https://ollama.com/download) installed
- FFmpeg installed and on PATH

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

ollama pull llama3.2

uvicorn app.main:app --reload
```
Runs at `http://localhost:8000` (docs at `/docs`).

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`.
