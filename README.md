# Deepfake Detective — Forensic Media Intelligence Platform

A multi-modal forensic analysis platform that detects manipulated and AI-generated media (images, audio, video), generates technical evidence, and produces timestamped PDF reports suitable for documentation and review.

> **Disclaimer:** This platform produces automated technical assessments only. It does not file complaints with any authority and is not a certified forensic or legal opinion.

---

## Overview

The rise of AI-generated deepfakes, voice cloning, and synthetic media has created a growing need for tools that can determine whether digital media is authentic. Deepfake Detective addresses this by combining deep neural network inference with signal-level forensic analysis across three modalities — image, audio, and video — to produce explainable, evidence-backed assessments rather than bare confidence scores.

The system is designed around forensic principles: every finding is supported by technical evidence, every uploaded file is cryptographically hashed for integrity, and every analysis result is preserved in an auditable chain.

## Key Capabilities

| Module | Description |
|---|---|
| **Image Forensics** | EfficientNet-B4 neural detector, Grad-CAM attention maps, Error Level Analysis (ELA), PRNU sensor noise, edge tampering, steganography analysis, metadata inspection |
| **Audio Forensics** | LCNN neural detector, signal intelligence (120+ descriptors), glottal/voice quality analysis, ENF grid forensics, file container DNA, splicing timeline |
| **Video Forensics** | Frame-aggregated neural detection, optical flow analysis, face temporal consistency, lip-sync forensics, compression DNA, container forensics, AV cross-modal analysis |
| **Evidence Engine** | Calibrated probability fusion, multi-signal evidence weighting, OOD detection, structured forensic evidence generation |
| **Reporting** | Timestamped PDF forensic reports with SHA-256 integrity hashing, evidence visualization, and chain-of-custody metadata |

## System Architecture

```
                    USER
                     │
              ┌──────┴──────┐
              │   FRONTEND   │  React + Vite + Tailwind
              └──────┬──────┘
                     │ REST API + WebSocket
              ┌──────┴──────┐
              │   BACKEND    │  FastAPI + SQLAlchemy + Celery
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   IMAGE         AUDIO         VIDEO
   PIPELINE      PIPELINE     PIPELINE
   (PyTorch)     (PyTorch)    (PyTorch + OpenCV)
        │            │            │
        └────────────┼────────────┘
                     │
              EVIDENCE FUSION
                     │
        ┌────────────┼────────────┐
        │            │            │
   FORENSIC      DATABASE      REPORT
   HEATMAPS     (SQLite /     GENERATOR
   & EVIDENCE    Postgres)    (ReportLab)
```

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3, Recharts, Framer Motion, WebSocket |
| **Backend API** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| **ML / Inference** | PyTorch 2, EfficientNet-B4, LCNN, MTCNN, OpenCV, torchvision |
| **Queue** | Celery + Redis (optional — runs inline without Redis) |
| **Database** | SQLite (development), PostgreSQL 16 (production) |
| **Reporting** | ReportLab, Matplotlib |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **Deployment** | Docker Compose (API + Worker + Frontend + PostgreSQL + Redis) |

## How It Works

```
UPLOAD MEDIA  →  VALIDATION + SHA-256 HASHING  →  JOB QUEUE
                                                      │
              ┌───────────────────────────────────────┘
              ▼
     FORENSIC ANALYSIS (neural + signal-level)
              │
              ▼
     EVIDENCE FUSION (calibrated probability + multi-signal weighting)
              │
              ▼
     VERDICT: AUTHENTIC │ MANIPULATED │ INCONCLUSIVE
              │
              ▼
     PDF REPORT GENERATION (SHA-256 signed, timestamped)
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- (Optional) CUDA-capable GPU for accelerated inference
- (Optional) Redis for background job queue
- (Optional) PostgreSQL 16 for production database

### Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone <repository-url>
cd deepfake

# 2. Create Python virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install backend dependencies
cd backend
pip install -r requirements-ml.txt
cd ..

# 4. Configure environment
copy .env.example .env
# Edit .env if needed (defaults work for local development)

# 5. Install frontend
cd frontend
npm install
cd ..

# 6. Start both servers
make dev
```

The backend API will be available at `http://localhost:8000` (docs at `/docs`).

The frontend will be available at `http://localhost:3000`.

### Docker Setup

```bash
# 1. Configure environment
copy .env.example .env
# Set JWT_SECRET_KEY and POSTGRES_PASSWORD in .env

# 2. Build and start all services
docker compose up --build

# Frontend: http://localhost:8080
# API docs: http://localhost:8000/docs
```

## Project Structure

```
deepfake/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── main.py             # Application entry point
│   │   ├── config.py           # Environment configuration
│   │   ├── models.py           # Database ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── security.py         # JWT authentication
│   │   ├── storage.py          # File storage & hashing
│   │   ├── observability.py    # Logging, request tracing, security headers
│   │   ├── routers/            # API route handlers
│   │   ├── ml/                 # ML inference pipelines
│   │   │   ├── image_pipeline.py
│   │   │   ├── audio_pipeline.py
│   │   │   ├── video_pipeline.py
│   │   │   ├── forensics/      # Signal-level forensic analyzers
│   │   │   ├── audio/          # Audio signal intelligence
│   │   │   └── video/          # Video temporal/spatial analysis
│   │   ├── report/             # PDF report generator
│   │   └── worker/             # Celery task queue
│   ├── tests/                  # Backend test suite
│   └── requirements*.txt       # Python dependencies
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── pages/              # Route pages
│   │   ├── components/         # UI components
│   │   └── lib/                # API client, auth, utilities
│   └── package.json
├── checkpoints/                # Trained model weights
├── ml/                         # Training & evaluation code
├── docker-compose.yml          # Production deployment
├── Makefile                    # Development commands
└── .env.example                # Environment template
```

## API

Interactive API documentation is available at `/docs` (Swagger UI) when the backend is running.

### Core Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | System health check |
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | JWT authentication |
| `/api/auth/me` | GET | Current user profile |
| `/api/upload` | POST | Upload media for analysis |
| `/api/upload/limits` | GET | Upload size/format limits |
| `/api/jobs/{id}/status` | GET | Job processing status |
| `/api/jobs/{id}/result` | GET | Analysis results |
| `/api/jobs/{id}/ws` | WebSocket | Real-time job status stream |
| `/api/jobs/{id}/report` | POST | Generate PDF forensic report |
| `/api/jobs/{id}/report` | GET | Download generated report |
| `/api/reports/{ref}/verify` | GET | Verify report integrity |
| `/api/history` | GET | User analysis history |

## Models

| Model | Architecture | Purpose | Checkpoint |
|---|---|---|---|
| Image Detector | EfficientNet-B4 (fine-tuned) | AI/synthetic image detection | `image_detector.pt` (67 MB) |
| Image Detector (light) | EfficientNet-B0 (fine-tuned) | Lightweight alternative | `image_detector_b0.pt` (16 MB) |
| Audio Detector | LCNN | AI/synthetic voice detection | `audio_detector.pt` (0.6 MB) |
| Video Detector | Frame-aggregated EfficientNet | Video deepfake detection | Uses image detector weights |

All model weights are stored in `checkpoints/` with SHA-256 integrity validation at load time.

## Security

- **Authentication:** JWT-based with bcrypt password hashing
- **Production safety:** Refuses to start with placeholder secrets or debug mode enabled
- **Upload validation:** File type verification, size limits, rate limiting per user/IP
- **CORS:** Configurable origins (locked down in production)
- **Request tracing:** Every request receives a unique ID for audit correlation
- **Security headers:** HSTS, X-Content-Type-Options, X-Frame-Options in production
- **Report integrity:** PDF reports are SHA-256 hashed for chain-of-custody verification
- **Evidence hashing:** All uploaded media is SHA-256 hashed at ingestion

## Limitations

- **False positives/negatives:** No detector achieves 100% accuracy. Heavy JPEG compression, social media processing, and screenshots can affect results.
- **Unseen generators:** Models are trained on specific AI generators. Completely novel generators may not be detected.
- **Metadata dependency:** Some forensic signals (EXIF, container format) can be stripped or forged.
- **Source attribution:** The system cannot prove who created or first published media.
- **Audio quality:** Low-bitrate, heavily compressed, or very short audio clips reduce detection reliability.
- **Video processing:** Long videos are sampled at configurable FPS; manipulation in unsampled frames may be missed.
- **Single-device scope:** This is a standalone analysis tool, not a distributed monitoring system.

## Testing

```bash
# Backend tests
cd backend
python -m pytest -q

# Frontend tests
cd frontend
npm test
```

## License

MIT License — see [LICENSE](LICENSE).
