# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] — 2026-09-29

### Core Platform

- Multi-modal forensic analysis platform for images, audio, and video
- EfficientNet-B4 image detector with Grad-CAM attention visualization
- LCNN audio detector with 120+ signal intelligence descriptors
- Frame-aggregated video detector with temporal analysis
- Calibrated evidence fusion with configurable uncertainty band
- INCONCLUSIVE verdict for ambiguous cases
- SHA-256 integrity hashing of all uploads and reports
- Timestamped PDF forensic report generation with chain-of-custody metadata

### Image Forensics

- Error Level Analysis (ELA)
- PRNU sensor noise analysis
- Steganography (LSB entropy) analysis
- Edge tampering detection (Sobel/Canny)
- EXIF/metadata inspection
- AI synthetic content detection
- Camera CFA pattern analysis
- Watermark detection

### Audio Forensics

- Signal intelligence extraction (MFCC, spectral, time-domain)
- Glottal voice quality analysis (IAIF)
- ENF (Electrical Network Frequency) forensics
- File container DNA analysis
- Splicing timeline detection
- Speech semantics analysis
- Audio provenance and security analysis

### Video Forensics

- Optical flow anomaly detection
- Face temporal consistency analysis
- Lip-sync forensics
- Compression DNA analysis
- Container format forensics
- Audio-video cross-modal correlation
- Scene segmentation
- Face/speaker temporal jitter measurement

### Backend

- FastAPI REST API with OpenAPI documentation
- JWT authentication with bcrypt password hashing
- SQLAlchemy 2 ORM with Alembic migrations
- Celery + Redis async task queue (optional — inline mode available)
- WebSocket real-time job status streaming
- Upload validation, rate limiting, and security headers
- Production safety enforcement (refuses unsafe configuration)
- Request ID tracing and structured logging

### Frontend

- React 18 SPA with Vite 5
- Real-time job status via WebSocket with HTTP polling fallback
- Image, audio, and video forensic result viewers
- Pipeline audit visualizer
- Analysis history with search and filtering
- Responsive design with dark/light theme support
- PDF report generation and download

### Deployment

- Docker Compose with PostgreSQL, Redis, API, Worker, and Frontend services
- Health checks for all services
- Shared media volume between API and worker
- Read-only checkpoint mounting
- Nginx frontend serving with API proxying

### Security

- JWT token authentication with configurable expiry
- bcrypt password hashing
- CORS configuration with production lockdown
- HSTS and security headers in production
- Upload file type and size validation
- Per-user and per-IP rate limiting
- SHA-256 evidence and report integrity verification
- Request tracing with unique request IDs
