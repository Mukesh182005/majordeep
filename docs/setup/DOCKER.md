# Docker Setup

## Prerequisites

- Docker Engine 24+
- Docker Compose v2

## Quick Start

```bash
# 1. Configure environment
copy .env.example .env

# 2. Set required production secrets in .env:
#    JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(48))">
#    POSTGRES_PASSWORD=<your-database-password>

# 3. Build and start
docker compose up --build
```

## Services

| Service | Port | Description |
|---|---|---|
| `frontend` | 8080 | Nginx serving the React SPA |
| `api` | 8000 | FastAPI backend (runs Alembic migrations on startup) |
| `worker` | — | Celery worker for background ML inference |
| `db` | 5432 (internal) | PostgreSQL 16 database |
| `redis` | 6379 (internal) | Redis 7 message broker |

## Access

- **Frontend:** http://localhost:8080
- **API docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/api/health

## Common Commands

```bash
# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f worker

# Stop all services
docker compose down

# Stop and remove volumes (DELETES DATA)
docker compose down -v

# Rebuild a single service
docker compose build api

# Restart a service
docker compose restart worker
```

## Health Checks

All services include health checks:

- **db:** `pg_isready` every 10s
- **redis:** `redis-cli ping` every 10s
- **worker:** Celery `inspect ping` every 60s

The API and worker services wait for healthy db and redis before starting.

## Volumes

| Volume | Purpose |
|---|---|
| `db_data` | PostgreSQL data persistence |
| `redis_data` | Redis persistence (AOF snapshots) |
| `media` | Shared upload/evidence/report storage between API and worker |

Model checkpoints are mounted read-only from `./checkpoints`.

## Troubleshooting

| Problem | Solution |
|---|---|
| `set POSTGRES_PASSWORD in .env` | Add `POSTGRES_PASSWORD=yourpassword` to `.env` |
| `set JWT_SECRET_KEY in .env` | Generate and add a secure key to `.env` |
| Worker not processing jobs | Check `docker compose logs worker` — model loading may be slow on first start |
| Out of disk space | Large model weights + media can consume significant space |
| GPU support | Requires nvidia-docker runtime; set `DEVICE=cuda` in `.env` |
