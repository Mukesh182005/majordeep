# Deploy DeepSentinel (Docker + Cloudflare Tunnel)

Verified on 2026-11-02 on the lab PC (Windows 11, Docker Desktop 29.9, WSL 2): a fresh clone of `main`
started with these steps passed the image / audio / video smoke test and 22/22 browser tests, and
production mode was checked (health 200, sign-up, `HttpOnly; Secure; SameSite=lax` session cookie).

The site is public only while this PC, Docker and the tunnel are running. Analysis runs on the CPU
inside Docker: images take seconds, a video one to several minutes.

## 1. Once: get the code and settings

```powershell
git clone https://github.com/Mukesh182005/majordeep.git
cd majordeep
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # copy the output
python -c "import secrets; print(secrets.token_urlsafe(24))"   # copy the output
```

Edit `.env`:

```
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=<first output>
POSTGRES_PASSWORD=<second output>          # add this line if it is not there
GUEST_RATE_LIMIT_PER_HOUR=30               # every visitor arrives through the tunnel and shares this limit
CORS_ORIGINS=https://placeholder.example   # replaced in step 3
```

`.env` holds secrets: never commit or share it (git ignores it).

## 2. Start the site

```powershell
docker compose up --build -d
docker compose ps        # wait until api, worker and frontend show "healthy" (first start: ~10 min, models download)
```

Check locally: open `http://localhost:8080/api/health` -> `"status":"ok"`.

## 3. Make it public

In a separate PowerShell window (keep it open):

```powershell
& "C:\Users\STUDENT\bin\cloudflared.exe" tunnel --url http://localhost:8080
```

It prints `https://<random-words>.trycloudflare.com`. Put that address in `.env`
(`CORS_ORIGINS=https://<random-words>.trycloudflare.com`), then:

```powershell
docker compose up -d api worker
```

Open the link on a phone with mobile data: upload an image, wait for the verdict, download the PDF.

## Every later start

```powershell
cd majordeep
docker compose up -d
& "C:\Users\STUDENT\bin\cloudflared.exe" tunnel --url http://localhost:8080
```

The quick-tunnel address changes every time: update `CORS_ORIGINS` and run `docker compose up -d api worker`.

## Update to the newest code

```powershell
git pull
docker compose up --build -d
```

## Stop

`Ctrl+C` in the tunnel window, then `docker compose down` (data is kept; `down -v` would delete it).

## A fixed address

With a domain on a free Cloudflare account:

```powershell
cloudflared tunnel login
cloudflared tunnel create deepsentinel
cloudflared tunnel route dns deepsentinel deepsentinel.<your-domain>
cloudflared tunnel run --url http://localhost:8080 deepsentinel
```

and set `CORS_ORIGINS=https://deepsentinel.<your-domain>`.

## Problems

| Symptom | Fix |
|---|---|
| `docker` not recognised | Start Docker Desktop; or use `C:\Users\<you>\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe` |
| `Pool overlaps with other one` | Another copy of the stack is running: `docker compose down` in that folder first |
| `Refusing to start: unsafe production configuration` | Set `DEBUG=false`, a real `JWT_SECRET_KEY` and a real `CORS_ORIGINS` (not `*`) |
| Sign-in does not stick on `http://localhost:8080` | Production cookies are Secure (HTTPS only): use the tunnel link, or `ENVIRONMENT=development` for local use |
| Uploads refused after 3 | `GUEST_RATE_LIMIT_PER_HOUR` in `.env`, then `docker compose up -d api` |

`deploy/docker-compose.prod.yml`, `deploy/cloudflare-tunnel.yml` and the backup / uptime scripts in this
folder come from an earlier session and were not tested with these steps.
