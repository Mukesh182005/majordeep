# DeepSentinel Beta Deployment Guide (Image-Only Beta)

This guide documents the exact steps and configuration used to deploy the DeepSentinel image-only beta platform.

---

## 1. Target Architecture & Environment

The deployment supports two production environments:

### Target A: Lab Machine with NVIDIA RTX 5070 (12 GB) behind Cloudflare Tunnel (Recommended)
* **Compute**: Intel/AMD Host + NVIDIA GeForce RTX 5070 (12 GB VRAM)
* **Operating System**: Ubuntu 24.04 LTS / Debian 12
* **Ingress**: Cloudflare Tunnel (`cloudflared`) — no router port-forwarding or public IP required. Automatic TLS and DDoS protection terminating at the edge.
* **Inference**: GPU-accelerated PyTorch (`--gpus all` via NVIDIA Container Toolkit).

### Target B: Oracle Cloud Always Free ARM VM
* **Compute**: Ampere A1 Compute (2 OCPU, 12 GB RAM)
* **Operating System**: Oracle Linux 9 / Ubuntu 24.04 ARM64
* **Ingress**: Caddy v2 reverse proxy with automatic Let's Encrypt / ZeroSSL TLS.
* **Inference**: Optimized multi-core CPU inference with PyTorch CPU wheels.

---

## 2. Production Environment Configuration

The production environment file is configured in `deploy/.env.production` (template in `deploy/.env.production.example`).

### Critical Production Flags
```ini
ENVIRONMENT=production
DEBUG=false

# Cryptographically random 48-byte secret key (96 hex characters):
JWT_SECRET_KEY=d8bcb64bb108c5008291dd27a2d7bb32f5d9269002896b1c98d96e1cfeec87eccc63ed12994e0f8ebf3b12c6ebd4bc59

# Secure database credentials:
POSTGRES_USER=deepfake
POSTGRES_PASSWORD=TAGP-_k9mkLKnat_TlQu_CUgn3Oc8y9E
POSTGRES_DB=deepfake
DATABASE_URL=postgresql+psycopg://deepfake:TAGP-_k9mkLKnat_TlQu_CUgn3Oc8y9E@db:5432/deepfake

# Celery & Redis:
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Real public beta domain:
CORS_ORIGINS=https://beta.deepsentinel.ai,http://localhost:8080

# Image-Only Beta Restrictions:
ENABLED_MEDIA_TYPES=image
MAX_UPLOAD_MB=100
MAX_VIDEO_SECONDS=0
MAX_AUDIO_SECONDS=0

# Ephemeral guest data retention and rate limiting:
RETENTION_HOURS=72
UPLOAD_RATE_LIMIT_PER_HOUR=20
GUEST_RATE_LIMIT_PER_HOUR=3

# Reverse proxy trust:
TRUSTED_PROXIES=172.28.0.10,127.0.0.1
```

To initialize the environment on the server:
```bash
cp deploy/.env.production.example .env
# Edit .env with your specific secrets if overriding
```

---

## 3. Deployment Steps

### Step 3.1: Host Dependencies & Container Runtime

#### For RTX 5070 Machine:
```bash
# 1. Install Docker Engine and Compose Plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Install NVIDIA Container Toolkit (for GPU passthrough)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. Install cloudflared
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install -y cloudflared
```

#### For Oracle Cloud Always Free ARM VM:
```bash
# 1. Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Open HTTP and HTTPS ports in OS iptables / firewalld
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true
```

---

### Step 3.2: Launch Docker Compose Services

Run the stack in detached mode:
```bash
docker compose --env-file deploy/.env.production up -d --build
```

The stack starts 5 core services:
1. `db`: PostgreSQL 16 Alpine with health check and persistent volume `db_data`.
2. `redis`: Redis 7 Alpine with health check and persistent volume `redis_data`.
3. `api`: FastAPI application (migrations run via `alembic upgrade head`; model warm-up skipped because `CELERY_BROKER_URL` is set).
4. `worker`: Celery worker with `--concurrency=1`, preloads Hugging Face scene detectors into `hf_cache` named volume.
5. `beat`: Celery beat scheduler triggering hourly retention purge of guest jobs older than `RETENTION_HOURS` (72h).
6. `frontend`: Nginx serving the compiled Vite React SPA and proxying `/api/` (with WebSocket upgrade support and 100MB max body size).

Verify container health:
```bash
docker compose ps
```

---

### Step 3.3: Ingress & HTTPS Setup

#### Option A: Cloudflare Tunnel (RTX 5070 Lab)
Authenticate and configure `cloudflared`:
```bash
# Authenticate with Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create deepsentinel-beta

# Route hostname to tunnel
cloudflared tunnel route dns deepsentinel-beta beta.deepsentinel.ai

# Copy credentials and configuration
sudo cp deploy/cloudflare-tunnel.yml /etc/cloudflared/config.yml
# Ensure credentials-file in config.yml points to ~/.cloudflared/<tunnel-uuid>.json

# Install and start cloudflared as a system service
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

#### Option B: Caddy Reverse Proxy (Oracle Cloud ARM VM)
Launch Caddy alongside the stack:
```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml --env-file deploy/.env.production up -d caddy
```
Caddy automatically obtains and renews Let's Encrypt certificates for `beta.deepsentinel.ai`.

---

## 4. Nightly Backup & 80% Disk Usage Alert

The backup script `deploy/backup.sh` enforces:
1. PostgreSQL backup with `pg_dump` compressed with `gzip`.
2. 7-day retention policy: archives older than 7 days are automatically purged.
3. Media storage disk space check: if `/app/storage` or the host volume passes 80% utilization, a high-priority alert is emitted to syslog and webhook.

### Install Cron Job
Add the following line to `/etc/cron.d/deepsentinel-backup` or `crontab -e`:
```cron
# Run nightly at 02:00 AM UTC
0 2 * * * /path/to/majordeep/deploy/backup.sh >> /var/log/deepsentinel_backup.log 2>&1
```

To test the backup immediately:
```bash
chmod +x deploy/backup.sh
./deploy/backup.sh
```
Or with Python:
```bash
python deploy/backup.py
```

---

## 5. Uptime & Health Check Monitoring

The endpoint `/api/health` reports status `ok`, the semantic version, queue status, and active models.

### Install Uptime Probe Cron Job
Monitor `/api/health` every 5 minutes:
```cron
# Check API health every 5 minutes
*/5 * * * * /path/to/majordeep/deploy/uptime_check.sh https://beta.deepsentinel.ai/api/health >> /var/log/deepsentinel_uptime.log 2>&1
```

To run a single probe:
```bash
./deploy/uptime_check.sh https://beta.deepsentinel.ai/api/health
```
Output:
```text
[2026-10-22T12:30:00Z] [HEALTHY] 200 OK | Target: https://beta.deepsentinel.ai/api/health | Latency: 0.042s
```

---

## 6. End-to-End Smoke Test Verification

The automated verification suite in `deploy/smoke_test.py` validates the entire image-only beta pipeline:
1. Registers a new test user (`POST /api/auth/register`).
2. Logs in and validates the `httpOnly` session cookie (`POST /api/auth/login`).
3. Uploads 3 real photos (`golden_test/real/`) and 3 AI images (`golden_test/ai/`).
4. Polls `/api/jobs/{id}/status` until all 6 jobs complete (`status == "done"`).
5. Requests short-lived signed URLs via `POST /api/jobs/{id}/links`.
6. Downloads the forensic PDF report and validates the `%PDF-` binary magic header.
7. Calls `DELETE /api/history/{id}` to delete a scan.
8. Verifies that the source upload, evidence files, and report PDF are completely unlinked from disk.
9. Confirms that `ENABLED_MEDIA_TYPES=image` rejects non-image media.

### Running the Smoke Test:
```bash
# Against local frontend / Caddy proxy:
python deploy/smoke_test.py --base-url http://localhost:8080

# Against live public HTTPS beta:
python deploy/smoke_test.py --base-url https://beta.deepsentinel.ai

# In-process validation:
python deploy/smoke_test.py --in-process
```

### Verification Results Summary:
* Health Check: `[OK] 200 OK`
* Registration & Session Cookie: `[OK]`
* 6 Images Inferred: `[OK] 6/6 jobs settled`
* PDF Report Download: `[OK] Valid PDF generated (starts with %PDF-)`
* Scan Deletion: `[OK] HTTP 204 returned`
* Disk Cleanup: `[OK] Upload file deleted; evidence files erased; report PDF erased`
