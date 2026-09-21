# Deepfake Detection Platform
#   make dev      — start backend + frontend dev servers
#   make test     — run backend test suite
#   make build    — production frontend bundle
#   make clean    — remove caches and build artefacts
#   make train    — train both detectors
#   make verify   — check which checkpoints the backend will load

SHELL := cmd.exe
PY    ?= .venv\Scripts\python.exe
DATA  ?= data
PROC  ?= $(DATA)\processed

EPOCHS_IMAGE ?= 15
EPOCHS_AUDIO ?= 20
BACKBONE     ?= efficientnet_b4

.DEFAULT_GOAL := dev
.PHONY: dev api web test build clean train train-image train-audio verify migrate

# ── Development ───────────────────────────────────────────────────────────────
dev:  ## Start backend + frontend (two windows)
	start "Backend" cmd /k "cd backend && ..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000"
	start "Frontend" cmd /k "cd frontend && npm.cmd run dev"

api:  ## Backend only
	cd backend && $(PY) -m uvicorn app.main:app --reload --port 8000

web:  ## Frontend only
	cd frontend && npm.cmd run dev

# ── Testing ───────────────────────────────────────────────────────────────────
test:  ## Backend tests
	cd backend && $(PY) -m pytest -q

build:  ## Production frontend bundle
	cd frontend && npm.cmd run build

# ── Database ──────────────────────────────────────────────────────────────────
migrate:  ## Apply Alembic migrations
	cd backend && $(PY) -m alembic upgrade head

# ── Training ──────────────────────────────────────────────────────────────────
train-image:  ## Train image/video detector
	$(PY) ml\training\train_image.py --data $(PROC)\faces --backbone $(BACKBONE) --epochs $(EPOCHS_IMAGE)

train-audio:  ## Train audio detector
	$(PY) ml\training\train_audio.py --data $(PROC)\audio --epochs $(EPOCHS_AUDIO)

train: train-image train-audio verify  ## Train both detectors

verify:  ## Report which checkpoints the backend will load
	$(PY) scripts\verify_checkpoints.py

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:  ## Remove caches and build artefacts
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
	if exist ".pytest_cache" rd /s /q ".pytest_cache"
	if exist "frontend\dist" rd /s /q "frontend\dist"
	@echo Cleaned.
