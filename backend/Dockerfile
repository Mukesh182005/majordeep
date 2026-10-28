# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib

# libgl/libglib: OpenCV runtime; ffmpeg: video and compressed-audio decoding.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.lock requirements-gpu.txt ./
# Every package pinned to the tested version (scripts/compile_requirements_lock.ps1).
# The lock takes torch from the PyTorch CPU index: the GPU wheels are several
# GB and pointless without a GPU. TORCH_VARIANT=gpu (docker-compose.gpu.yml)
# swaps in the CUDA build from requirements-gpu.txt; the wheels bundle the CUDA
# runtime, so only the host's NVIDIA driver is needed. The CPU build is removed
# first: pip counts 2.12.0+cpu as satisfying torch==2.12.0 and would keep it.
ARG TORCH_VARIANT=cpu
RUN pip install -r requirements.lock \
    && if [ "$TORCH_VARIANT" = "gpu" ]; then \
        pip uninstall -y torch torchvision && pip install -r requirements-gpu.txt; \
    fi

COPY . .

# Run as a non-root user: this service accepts arbitrary uploads from the
# internet, so the process should not own the filesystem it writes to.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/storage /app/checkpoints \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
