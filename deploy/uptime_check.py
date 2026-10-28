#!/usr/bin/env python3
"""Uptime check probe for DeepSentinel /api/health."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.request


def check_health(url: str, timeout: float = 10.0) -> dict:
    start_time = time.time()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DeepSentinel-UptimeCheck/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start_time
            code = resp.getcode()
            body_bytes = resp.read()
            data = json.loads(body_bytes.decode("utf-8"))
            is_ok = code == 200 and data.get("status") == "ok"
            return {
                "ok": is_ok,
                "status_code": code,
                "latency_ms": round(elapsed * 1000, 2),
                "data": data,
            }
    except urllib.error.HTTPError as he:
        elapsed = time.time() - start_time
        return {
            "ok": False,
            "status_code": he.code,
            "latency_ms": round(elapsed * 1000, 2),
            "error": str(he),
        }
    except Exception as exc:
        elapsed = time.time() - start_time
        return {
            "ok": False,
            "status_code": 0,
            "latency_ms": round(elapsed * 1000, 2),
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser(description="DeepSentinel /api/health Uptime Probe")
    parser.add_argument("--url", default="http://localhost:8080/api/health", help="Health endpoint URL")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a daemon probe")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for daemon mode")
    args = parser.parse_args()

    while True:
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        res = check_health(args.url, args.timeout)
        if res["ok"]:
            print(f"[{ts}] [HEALTHY] 200 OK | Latency: {res['latency_ms']}ms | URL: {args.url} | Version: {res['data'].get('version')}")
        else:
            print(f"[{ts}] [ALERT-DOWN] Status: {res.get('status_code')} | Latency: {res['latency_ms']}ms | URL: {args.url} | Error: {res.get('error')}", file=sys.stderr)
            if not args.daemon:
                sys.exit(1)

        if not args.daemon:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
