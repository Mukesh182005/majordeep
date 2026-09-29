# Installation Guide

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for backend |
| Node.js | 18+ | Required for frontend |
| npm | 9+ | Included with Node.js |
| Git | 2.x | For cloning the repository |
| GPU (optional) | CUDA 12.x | Accelerates ML inference significantly |
| Redis (optional) | 7.x | Required for background job queue; without it, inference runs inline |
| PostgreSQL (optional) | 16.x | Production database; SQLite is used by default |

## Step 1 — Clone the Repository

```bash
git clone <repository-url>
cd deepfake
```

## Step 2 — Python Virtual Environment

```bash
python -m venv .venv
```

Activate:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

## Step 3 — Install Backend Dependencies

For **CPU-only** (no NVIDIA GPU):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
cd backend
pip install -r requirements.txt
cd ..
```

For **GPU (CUDA)**:

```bash
cd backend
pip install -r requirements-ml.txt
cd ..
```

## Step 4 — Configure Environment

```bash
copy .env.example .env
```

The default `.env` works for local development with SQLite and inline inference (no Redis needed).

For production, you must set:
- `JWT_SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `ENVIRONMENT=production`
- `DEBUG=false`
- `DATABASE_URL` — PostgreSQL connection string

## Step 5 — Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Step 6 — Verify Installation

### Backend

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

Visit `http://localhost:8000/docs` — you should see the Swagger API documentation.

### Frontend

```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000` — you should see the landing page.

## Step 7 — Start Both (Development)

Using the Makefile (Windows):

```bash
make dev
```

This opens two terminal windows: one for the backend (port 8000) and one for the frontend (port 3000).

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: torch` | Install PyTorch separately: see Step 3 |
| `CUDA out of memory` | Set `DEVICE=cpu` in `.env` |
| Frontend can't reach backend | Check that backend is on port 8000; Vite proxies `/api` to it |
| `alembic` errors | Run `cd backend && python -m alembic upgrade head` |
| Port 8000 already in use | Change port: `--port 8001` and update `VITE_API_TARGET` |
