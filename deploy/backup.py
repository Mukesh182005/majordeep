#!/usr/bin/env python3
"""Cross-platform backup and disk space monitor for DeepSentinel.

Functions:
1. Performs PostgreSQL database backup via pg_dump or docker compose exec.
2. Enforces strict 7-day retention window on backup archives.
3. Checks storage volume disk utilization and raises an alert if usage exceeds 80%.
"""

from __future__ import annotations

import datetime
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "./backups"))
MEDIA_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))
RETENTION_DAYS = 7
DISK_ALERT_THRESHOLD = 80.0
POSTGRES_USER = os.getenv("POSTGRES_USER", "deepfake")
POSTGRES_DB = os.getenv("POSTGRES_DB", "deepfake")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")


def perform_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"deepsentinel_{timestamp}.sql.gz"

    print(f"[*] Dumping PostgreSQL database to {backup_file}...")
    try:
        # Attempt docker compose exec first
        proc = subprocess.Popen(
            ["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", POSTGRES_USER, POSTGRES_DB],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"docker compose pg_dump failed: {stderr.decode(errors='ignore')}")

        with gzip.open(backup_file, "wb") as gz:
            gz.write(stdout)

    except Exception as exc:
        print(f"[-] Docker compose backup failed ({exc}). Trying local pg_dump...", file=sys.stderr)
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError(f"Backup failed and DATABASE_URL is not set: {exc}")
        proc = subprocess.run(["pg_dump", db_url], capture_output=True, check=True)
        with gzip.open(backup_file, "wb") as gz:
            gz.write(proc.stdout)

    size = backup_file.stat().st_size
    print(f"[OK] Database backup written successfully ({size} bytes).")
    return backup_file


def prune_old_backups() -> int:
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=RETENTION_DAYS)
    pruned = 0
    for path in BACKUP_DIR.glob("deepsentinel_*.sql.gz"):
        mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc)
        if mtime < cutoff:
            path.unlink()
            pruned += 1
            print(f"[OK] Deleted expired backup ({RETENTION_DAYS}+ days old): {path.name}")
    print(f"[i] Backup retention check complete. Pruned: {pruned} archive(s).")
    return pruned


def check_disk_usage() -> float:
    media_path = MEDIA_DIR if MEDIA_DIR.exists() else Path(".")
    total, used, free = shutil.disk_usage(str(media_path))
    pct_used = (used / total) * 100.0
    print(f"[i] Storage disk usage on {media_path}: {pct_used:.1f}% ({used // (1024**3)}GB / {total // (1024**3)}GB)")

    if pct_used >= DISK_ALERT_THRESHOLD:
        alert_msg = f"CRITICAL: Storage disk usage is at {pct_used:.1f}% (threshold: {DISK_ALERT_THRESHOLD}%)!"
        print(f"[-] {alert_msg}", file=sys.stderr)
        if ALERT_WEBHOOK_URL:
            import urllib.request
            import json
            req = urllib.request.Request(
                ALERT_WEBHOOK_URL,
                data=json.dumps({"text": alert_msg}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                print(f"[!] Webhook dispatch failed: {e}", file=sys.stderr)
    else:
        print(f"[OK] Disk usage is nominal (< {DISK_ALERT_THRESHOLD}%).")

    return pct_used


if __name__ == "__main__":
    print(f"=== DeepSentinel Nightly Backup & Disk Monitor [{datetime.datetime.now(datetime.timezone.utc).isoformat()}] ===")
    try:
        perform_backup()
        prune_old_backups()
        check_disk_usage()
        print("[✓] All backup & monitoring tasks completed.")
    except Exception as exc:
        print(f"[-] Fatal error during backup run: {exc}", file=sys.stderr)
        sys.exit(1)
