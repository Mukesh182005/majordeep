# Environment Variables

All configuration is managed through environment variables. Copy `.env.example` to `.env` and modify as needed.

## Application

| Variable | Default | Required | Description |
|---|---|---|---|
| `APP_NAME` | `Deepfake Detection Platform` | No | Display name |
| `API_V1_PREFIX` | `/api` | No | API route prefix |
| `ENVIRONMENT` | `development` | Yes (prod) | `development` or `production` |
| `DEBUG` | `true` | Yes (prod) | Must be `false` in production |

## Authentication

| Variable | Default | Required | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | `change-me-in-production` | **Yes** | Token signing key. Generate with: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | No | Token validity duration |

## Database

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./storage/deepfake.db` | No | SQLAlchemy connection string. Use `postgresql+psycopg://user:pass@host:5432/db` for production |

## Queue (Celery)

| Variable | Default | Required | Description |
|---|---|---|---|
| `CELERY_BROKER_URL` | *(empty)* | No | Redis URL for Celery broker. Leave empty for inline/eager execution |
| `CELERY_RESULT_BACKEND` | *(empty)* | No | Redis URL for Celery results |

**Note:** When both are empty, inference runs synchronously (inline). Set both to enable background job processing.

## Storage

| Variable | Default | Required | Description |
|---|---|---|---|
| `STORAGE_DIR` | `./storage/uploads` | No | Uploaded media file storage |
| `EVIDENCE_DIR` | `./storage/evidence` | No | Generated forensic evidence (heatmaps, etc.) |
| `REPORT_DIR` | `./storage/reports` | No | Generated PDF reports |
| `MAX_UPLOAD_MB` | `100` | No | Maximum upload file size in megabytes |

## Rate Limiting

| Variable | Default | Required | Description |
|---|---|---|---|
| `UPLOAD_RATE_LIMIT_PER_HOUR` | `20` | No | Maximum uploads per user per hour |
| `GUEST_RATE_LIMIT_PER_HOUR` | `3` | No | Maximum uploads per unauthenticated IP per hour |

## Models

| Variable | Default | Required | Description |
|---|---|---|---|
| `CHECKPOINT_DIR` | `./checkpoints` | No | Directory containing trained model weights |
| `IMAGE_MODEL_BACKBONE` | `efficientnet_b4` | No | Image model architecture: `efficientnet_b0`, `efficientnet_b4`, or `xception` |
| `IMAGE_MODEL_VERSION` | `image-detector-v1.0.0` | No | Image model version identifier |
| `AUDIO_MODEL_VERSION` | `audio-lcnn-v1.0.0` | No | Audio model version identifier |
| `VIDEO_MODEL_VERSION` | `video-frame-agg-v1.0.0` | No | Video model version identifier |
| `DEVICE` | `cpu` | No | Inference device: `cpu` or `cuda` |

## Video Processing

| Variable | Default | Required | Description |
|---|---|---|---|
| `VIDEO_SAMPLE_FPS` | `1.0` | No | Frame sampling rate for video analysis |
| `VIDEO_MAX_FRAMES` | `32` | No | Maximum frames to analyze per video |

## Audio Processing

| Variable | Default | Required | Description |
|---|---|---|---|
| `AUDIO_SAMPLE_RATE` | `16000` | No | Audio resampling rate (Hz) |
| `AUDIO_WINDOW_SECONDS` | `4.0` | No | Analysis window duration |

## Decision Thresholds

| Variable | Default | Required | Description |
|---|---|---|---|
| `FAKE_THRESHOLD` | `0.5` | No | Probability threshold for MANIPULATED verdict |
| `UNCERTAIN_BAND` | `0.15` | No | Width of the uncertainty band around threshold (values within ±band → INCONCLUSIVE) |

## CORS

| Variable | Default | Required | Description |
|---|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Yes (prod) | Comma-separated allowed origins. Never use `*` in production |
