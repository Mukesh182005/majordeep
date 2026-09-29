# Release Checklist — Deepfake Detective v1.0.0

This document tracks all acceptance gates for release readiness of the Deepfake Detective platform.

## Pre-Release Verification Checklist

- [x] **Clean repository** — Root clutter separated into `research_archive/`; no dangling scratch artifacts in production paths.
- [x] **No secrets committed** — Config uses environment variable overrides with secure `.env.example` templates; no hardcoded API keys or private certificates in version control.
- [x] **README complete** — Professional, academic-ready documentation without internal phase jargon; includes quick start, system overview, and architecture diagram.
- [x] **Installation tested** — Manual virtualenv and Docker setup pathways verified.
- [x] **Backend starts** — FastAPI server initializes cleanly on port 8000; OpenAPI documentation accessible at `/docs`.
- [x] **Frontend builds** — Vite production bundle compiles cleanly with zero syntax or bundling errors.
- [x] **Workers start** — Celery task runner and in-process fallback task runners verified for asynchronous media jobs.
- [x] **Models load** — PyTorch models (`image_detector.pt`, `image_detector_b0.pt`, `audio_detector.pt`) verify against recorded SHA-256 hashes.
- [x] **Database works** — SQLAlchemy ORM initializes schema, manages SQLite/PostgreSQL connections, handles migrations.
- [x] **Authentication works** — JWT authentication with bcrypt password hashing and token expiry controls validated.
- [x] **RBAC works** — Role-based access control enforces permissions between analysts, investigators, and system administrators.
- [x] **Upload works** — Multi-modal file upload endpoint validates MIME types, enforces file size caps, and computes immutable SHA-256 digests.
- [x] **Image analysis works** — Multi-stage image forensic pipeline (CFA, ELA, noise residual, PRNU, synthetic frequency analysis, deep CNN) executes deterministically.
- [x] **Audio analysis works** — LCNN deep audio classifier, 120+ signal descriptors, glottal inverse filtering, and ENF forensic analyzers run cleanly.
- [x] **Video analysis works** — Frame-by-frame deep aggregation, facial landmark stability, optical flow consistency, and cross-modal AV sync analyzers function.
- [x] **Provenance works** — Media genealogy graph, perceptual hashing (pHash, dHash, aHash), and source discovery logic operational.
- [x] **Investigation works** — Case management, evidence item linking, timeline collation, and hypothesis tracking operate reliably.
- [x] **Report generation works** — Timestamped, tamper-evident PDF forensic reports generated via ReportLab with cryptographic file hashes and confidence scores.
- [x] **Audit logging works** — Structured audit logger records all case mutations, user actions, model inferences, and system errors with ISO 8601 timestamps.
- [x] **E2E PASS** — End-to-end user journey from upload to analysis, visualization, case association, and PDF report export validated.
- [x] **Security PASS** — Input sanitization, MIME verification, path traversal guards, and secure HTTP headers active.
- [x] **Regression PASS** — 100% of backend pytest unit/integration tests and 100% of frontend Vitest component tests pass.
- [x] **Model hashes PASS** — SHA-256 checksums of all model checkpoints match release baseline.
- [x] **Documentation audited** — Limitations, known issues, tech stack, API endpoints, and model cards fully written and audited for factual claims.
- [x] **Limitations documented** — Honest boundaries (JPEG compression degradation, unseen generator generalization, short audio limits) documented in `docs/LIMITATIONS.md`.
- [x] **Demo prepared** — Step-by-step 10–12 minute live demonstration script and test case preparation guide provided in `docs/demo/DEMO_PLAN.md` and `docs/demo/DEMO_SCRIPT.md`.
- [x] **Demo tested** — Interactive workflow validated against sample media items.
- [x] **Viva preparation complete** — 25+ comprehensive questions and answers covering neural architectures, signal processing, fusion methods, and forensic validity in `docs/college/VIVA_QUESTIONS.md`.
