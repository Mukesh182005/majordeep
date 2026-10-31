# Run DeepSentinel publicly with a Cloudflare Tunnel (no Docker)

The app runs directly on Windows and a free Cloudflare quick tunnel gives it a public
`https://….trycloudflare.com` link. The site is up only while this PC and the three windows below
are running. The link changes every time the tunnel (window 3) is restarted.

Commands assume the project is at `C:\Users\STUDENT\Desktop\deepfake\deepfake` and `cloudflared.exe`
is at `C:\Users\STUDENT\bin\cloudflared.exe`. Change the paths if yours differ.

## Once: install

```powershell
# Python packages (from the project folder)
cd C:\Users\STUDENT\Desktop\deepfake\deepfake
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements-ml.txt

# Website packages
cd frontend
npm install
cd ..

# Settings file (skip if .env already exists)
copy .env.example .env

# Optional: lets you type just "cloudflared" in new PowerShell windows
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\STUDENT\bin", "User")
```

## Once: settings in `.env`

Make a secret key and copy what it prints:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then set these lines in `.env` (edit them if present, add them if not):

```
DEVICE=cuda                   # cpu if there is no NVIDIA GPU, or while training runs on it
DEBUG=false
JWT_SECRET_KEY=<the key printed above>
AUTH_COOKIE_SECURE=true
GUEST_RATE_LIMIT_PER_HOUR=30  # every guest arrives through the tunnel, so they share this limit
```

Never commit `.env` or share the key.

## Every time the code changes (after `git pull`): build the website

```powershell
cd C:\Users\STUDENT\Desktop\deepfake\deepfake\frontend
npm run build
```

## Every time: start the site (three PowerShell windows)

Window 1, backend (wait for `Application startup complete`):

```powershell
cd C:\Users\STUDENT\Desktop\deepfake\deepfake\backend
..\.venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Window 2, website (serves the built site and passes `/api` to the backend):

```powershell
cd C:\Users\STUDENT\Desktop\deepfake\deepfake\frontend
npm run preview -- --port 4173
```

Window 3, public link (prints `https://<random-words>.trycloudflare.com`):

```powershell
& "C:\Users\STUDENT\bin\cloudflared.exe" tunnel --url http://localhost:4173 --http-host-header localhost:4173
```

## Check it

```powershell
curl.exe -s http://127.0.0.1:8000/api/health                        # backend: "status":"ok"
curl.exe -s -o NUL -w "%{http_code}" http://localhost:4173/          # website: 200
curl.exe -s https://<your-link>.trycloudflare.com/api/health         # through the tunnel: "status":"ok"
```

Then open the link on a phone using mobile data, upload a photo, wait for the verdict and download
the PDF.

## Stop

Press `Ctrl+C` in each of the three windows.

## Problems

| Message | Fix |
|---|---|
| `cloudflared : The term 'cloudflared' is not recognized` | Use the full path as in window 3, or run the `SetEnvironmentVariable` line above and reopen PowerShell |
| Page loads but uploads fail | Window 1 is not running or not ready yet; check `http://127.0.0.1:8000/api/health` |
| `Blocked request. This host is not allowed` | Start the tunnel with `--http-host-header localhost:4173` as above |
| `Refusing to start: unsafe production configuration` | `.env` has `ENVIRONMENT=production`; for a quick tunnel keep `ENVIRONMENT=development` with `DEBUG=false` and a real `JWT_SECRET_KEY` |
| Out of GPU memory | Set `DEVICE=cpu` in `.env` and restart window 1 |

## A fixed address instead of a random one

Quick tunnels are for trying things out and have no uptime guarantee. For a permanent address, add a
domain to a free Cloudflare account and create a named tunnel:

```powershell
cloudflared tunnel login
cloudflared tunnel create deepsentinel
cloudflared tunnel route dns deepsentinel deepsentinel.<your-domain>
cloudflared tunnel run --url http://localhost:4173 deepsentinel
```

Then set `CORS_ORIGINS=https://deepsentinel.<your-domain>` in `.env`.
