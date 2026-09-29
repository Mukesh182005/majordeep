# System Architecture

## Overview

Deepfake Detective follows a layered, modular architecture separating presentation, application logic, forensic inference, and data persistence.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                         │
│                                                                     │
│  React 18 SPA  ─  Vite  ─  Tailwind CSS  ─  WebSocket client      │
│  Pages: Landing, Upload, Result, Report, History, Login             │
│  Components: ImageForensicsView, AudioForensicsView,                │
│              VideoForensicsView, PipelineAuditVisualizer            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP REST + WebSocket
┌───────────────────────────────┴─────────────────────────────────────┐
│                         APPLICATION LAYER                           │
│                                                                     │
│  FastAPI  ─  Pydantic  ─  SQLAlchemy  ─  Alembic                   │
│                                                                     │
│  Routers:                                                           │
│    /api/auth/*      — JWT authentication (register, login, me)     │
│    /api/upload      — File upload with validation + hashing        │
│    /api/jobs/*      — Job lifecycle (status, result, report, WS)   │
│    /api/history     — User analysis history                        │
│    /api/health      — System health check                          │
│    /api/reports/*   — Report integrity verification                │
│                                                                     │
│  Middleware:                                                        │
│    CORS, Security Headers, Request Context (tracing), Rate Limits  │
│                                                                     │
│  Security:                                                          │
│    JWT (HS256), bcrypt, production config validation                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                           QUEUE LAYER                               │
│                                                                     │
│  Celery 5  +  Redis 7  (optional — inline eager mode available)    │
│                                                                     │
│  Tasks: analyze_media_task                                          │
│  Concurrency: configurable (default: 2 workers)                    │
│  WebSocket: real-time status push to connected clients              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                        INFERENCE LAYER                              │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    IMAGE     │  │    AUDIO     │  │    VIDEO     │              │
│  │  PIPELINE    │  │   PIPELINE   │  │   PIPELINE   │              │
│  │             │  │              │  │              │              │
│  │ EfficientNet│  │ LCNN         │  │ Frame-agg    │              │
│  │ Grad-CAM    │  │ Signal Intel │  │ Optical Flow │              │
│  │ ELA         │  │ Glottal/IAIF │  │ Face Track   │              │
│  │ PRNU        │  │ ENF          │  │ Lip Sync     │              │
│  │ Stegano     │  │ File DNA     │  │ Compress DNA │              │
│  │ Tampering   │  │ Splicing     │  │ AV CrossMod  │              │
│  │ Metadata    │  │ Provenance   │  │ Container    │              │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘              │
│         └────────────────┼──────────────────┘                      │
│                          │                                          │
│              ┌───────────┴───────────┐                              │
│              │   EVIDENCE FUSION     │                              │
│              │                       │                              │
│              │ Calibrated prob       │                              │
│              │ Multi-signal weight   │                              │
│              │ OOD detection         │                              │
│              │ Uncertainty band      │                              │
│              └───────────┬───────────┘                              │
│                          │                                          │
│              ┌───────────┴───────────┐                              │
│              │   REPORT GENERATOR    │                              │
│              │                       │                              │
│              │ ReportLab PDF         │                              │
│              │ SHA-256 integrity     │                              │
│              │ Evidence embedding    │                              │
│              └───────────────────────┘                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                       PERSISTENCE LAYER                             │
│                                                                     │
│  Database:  SQLite (dev) / PostgreSQL 16 (prod)                    │
│  Tables:    users, jobs, reports, upload_events                    │
│  ORM:       SQLAlchemy 2 mapped columns                            │
│  Migrations: Alembic                                                │
│                                                                     │
│  File Storage:                                                      │
│    storage/uploads/    — uploaded media files                       │
│    storage/evidence/   — generated heatmaps, forensic artifacts    │
│    storage/reports/    — generated PDF reports                     │
│                                                                     │
│  Model Storage:                                                     │
│    checkpoints/        — trained model weights (.pt files)          │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Upload:** Frontend → `POST /api/upload` → file validation → SHA-256 hash → store to disk → create Job record (status: QUEUED)
2. **Queue:** Job dispatched to Celery worker (or executed inline in eager mode)
3. **Analysis:** Worker routes to appropriate pipeline based on `media_type` (image/audio/video)
4. **Pipeline:** Neural inference + forensic signal analysis → evidence dict
5. **Fusion:** Multiple signals combined into calibrated probability → verdict
6. **Storage:** Results written to Job record (verdict, probability, evidence JSON, heatmap paths)
7. **Delivery:** WebSocket push or HTTP poll delivers result to frontend
8. **Report:** On request, PDF generated from stored evidence → hashed → stored → delivered

## Key Design Decisions

- **Inline vs. queued execution:** Without Redis, inference runs inline (Celery eager mode). This simplifies development setup while the architecture remains queue-ready for production.
- **Evidence as JSON:** Forensic evidence is stored as a JSON column in the Job table, allowing flexible, schema-less storage of modality-specific evidence without separate tables.
- **Stateless API:** The backend API is stateless. All state is in the database and file storage. This allows horizontal scaling of API instances behind a load balancer.
- **Model isolation:** ML models are loaded once at startup and held in memory (GPU VRAM when available). The model registry validates checkpoint integrity at load time.
