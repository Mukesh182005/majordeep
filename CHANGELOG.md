# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] — 2026-10-31

Every number below is from a file in `evaluation/`; rules fixed before training in `evaluation/ROUND3-RULES.md`.

### Added
- Video: AI-generated video detector (CLIP ViT-L/14 frame features + logistic regression, trained here). On the
  held-out generator Veo 3 it flags 265 of 266 clips and 0 of 176 real test clips (`evaluation/AIVIDEO-01`).
  Its score is shown on every video result. In the full pipeline it raised Veo 3 called MANIPULATED from 10/40 to
  40/40 and face swaps 29/40 -> 30/40, but real DFD clips 1/40 -> 2/40, which fails the rule (at most 1/40), so it
  is not in the verdict by default (`AIVIDEO_IN_VERDICT=false`).
- The end-to-end evaluator records the AI-video detector score per video.

### Not done this round
- Image fine-tune v5: not enough disk for new real photos plus the newest-generator images it needs.
- Audio: no change (no phone recordings of the user's own to test against).

## [Unreleased] — 2026-10-29

Every number below is from a file in `evaluation/`; details in `docs/research/EVALUATION.md`.

### Added
- Images: Community Forensics (original + a copy fine-tuned on FLUX.2 / GPT Image 2 / Nano Banana 2) in the scene
  ensemble; TruFor edit-localisation heatmap (shown, not in the verdict). COCO + Synthbuster test half: AI images
  called MANIPULATED 74.5 % -> 98.4 %, called AUTHENTIC 21.5 % -> 0.1 %, real photos called MANIPULATED 2.0 % -> 0 %.
- Audio: pellav2 (pretrained, w2v-BERT 2.0) decides the verdict; the ASVspoof LCNN is the fallback.
- Video: GenD face-swap detector (pretrained, MIT) in the verdict, mean over face frames; per-frame timeline follows
  GenD; scene AI detectors on 8 frames instead of 1. 80 held-out DFD videos: face swaps called MANIPULATED
  2.5 % -> 72.5 %, real videos 0 -> 1 of 40.
- Browser end-to-end tests (Playwright, `npm run e2e`); whole-pipeline evaluator for image, audio and video
  (`backend/scripts/eval_end_to_end.py`).

### Fixed
- Video: unvalidated heuristics (LipForensics, generator profile match) forced 26 of 60 real DFD videos to
  MANIPULATED; they now only label.
- An image with no camera metadata is no longer called an "Authentic Camera Photograph"; AUTHENTIC needs
  P(AI) < 0.02, otherwise INCONCLUSIVE. Video likewise says "No manipulation detected (origin unverified)".
- Sign-out did not clear the httpOnly session cookie; a reload signed the user back in.
- A text file renamed to .jpg was accepted for analysis.
- Unbacked legal and standards claims (Daubert, ISO/IEC 27037/27042, "court-ready") removed from the site.
- Evidence and PDFs showed a local Windows path for the fine-tuned image model.

### Tried and not adopted
- A larger image fine-tune (v4) and a codec-augmented audio fine-tune: each improved one test set and made another
  worse, against rules fixed before testing (`evaluation/COMMFOR-FT-02`, `evaluation/E2E-03`).
- A second audio fine-tune with more genuine speech: fewer false alarms, but fakes caught fell 14 points
  (`evaluation/AUDIO-FT2-01`).

### Measured
- Fully AI-generated video (Veo 3, HunyuanVideo): 14 of 80 called MANIPULATED (`evaluation/VIDEO-AIGEN-01`).
- Two video notes no longer say "confirmed" for unvalidated checks (camera sensor pattern, rPPG pulse).

## [Unreleased] — 2026-10-05

Image detection rebuilt on measurement. On 560 held-out images (200 real
photos; 360 from SD 2.1, SDXL, SD3, DALL-E 3, Midjourney v6, Flux.1-dev and
Gemini Nano Banana / Pro), original files:

| | Before | After |
|---|---|---|
| Analyses that crashed | 23 | 0 |
| Real photos reported MANIPULATED | 41.8% | 2.0% |
| AI images reported MANIPULATED | 80.1% | 88.3% |
| AI images reported AUTHENTIC | 17.6% | 6.7% |

As screenshots: AI images reported AUTHENTIC fell from 25.9% to 0%.

### Fixed

- Primary scene detector `umm-maybe/AI-image-detector` (AUC 0.469, below chance on current generators) replaced by `haywoodsloan/ai-image-detector-deploy`, fused with `Organika/sdxl-detector` in log-odds space (AUC 0.984); max-of-experts fusion, which flagged 26–36% of real photos, removed
- Screenshot viewer borders are cropped before analysis; an unflagged screenshot without camera metadata is reported INCONCLUSIVE instead of AUTHENTIC
- Half-precision face-model inference returned NaN, crashing ~4% of image analyses and writing NaN into evidence JSON; inference is float32 and stored evidence is sanitised
- Video scene-AI score was always 0.0 (ensemble records were called as functions inside a bare `except`)
- Filename rule that capped AI scores below 0.49 for files named "whatsapp", "instagram" or "snapchat" removed
- Training manifest leaked re-encoded training faces into validation, merged the held-out test split into training, and labelled unlabelled uploads as fake (`scripts/expand_training_dataset.py`)

### Changed

- Non-discriminative heuristics report findings but no longer force verdicts: M28 statistical score (AUC 0.26), Fourier/wavelet artifact, missing CFA / EXIF, face-seam heuristic, standalone matte; copy-move alone now yields INCONCLUSIVE
- Face-crop checkpoint (StyleGAN-only) kept out of image and video verdicts by default (`FACE_MODEL_IN_VERDICT`)
- Scene detectors unavailable → never AUTHENTIC
- Model card, image forensics module doc, and report model-audit block describe the actual models and measured performance

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
