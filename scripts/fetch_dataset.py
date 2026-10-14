#!/usr/bin/env python3
"""Download a large dataset file over several resumable connections and verify it.

Some servers slow down long single connections (the ASVspoof DataShare record
and Zenodo both did on 2026-10-14). This fetches N byte ranges in parallel into
``<out>.parts/part<i>``, reconnects any connection that stalls, resumes from
the existing parts when rerun, joins them in order, and checks the size and the
published MD5 before removing the parts.

Usage (PowerShell)::

    python scripts/fetch_dataset.py --url "https://zenodo.org/api/records/10066460/files/synthbuster.zip/content" `
        --out C:\\deepsentinel_data\\downloads\\synthbuster.zip --size 12372557226 `
        --md5 0695bd328e16ea21c5c9cc2ae1d994ff
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import threading
import time
import urllib.request
from pathlib import Path

READ_TIMEOUT_S = 30
BLOCK = 1 << 20


def fetch_range(url: str, part: Path, start: int, end: int, stop: threading.Event) -> None:
    want = end - start + 1
    for _attempt in range(500):
        have = part.stat().st_size if part.exists() else 0
        if have >= want or stop.is_set():
            return
        request = urllib.request.Request(url, headers={"Range": f"bytes={start + have}-{end}"})
        try:
            with urllib.request.urlopen(request, timeout=READ_TIMEOUT_S) as response, open(part, "ab") as out:
                if response.status != 206:
                    raise RuntimeError(f"server ignored the byte range (HTTP {response.status})")
                while chunk := response.read(BLOCK):
                    out.write(chunk)
        except RuntimeError:
            stop.set()
            raise
        except Exception:
            time.sleep(2)  # timeout or reset: reconnect and resume


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        while chunk := handle.read(BLOCK * 8):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True, help="expected size in bytes")
    parser.add_argument("--md5", required=True, help="published MD5")
    parser.add_argument("--connections", type=int, default=8)
    parser.add_argument("--parts-dir", type=Path, default=None, help="default: <out>.parts")
    args = parser.parse_args()

    if args.out.exists() and args.out.stat().st_size == args.size and md5_file(args.out) == args.md5:
        print(f"{args.out} already complete and verified")
        return 0
    parts_dir = args.parts_dir or Path(str(args.out) + ".parts")
    parts_dir.mkdir(parents=True, exist_ok=True)
    chunk = -(-args.size // args.connections)
    ranges = [(i, i * chunk, min((i + 1) * chunk, args.size) - 1) for i in range(args.connections)]
    stop = threading.Event()
    threads = [
        threading.Thread(target=fetch_range, args=(args.url, parts_dir / f"part{i}", s, e, stop), daemon=True)
        for i, s, e in ranges
        if s < args.size
    ]
    for thread in threads:
        thread.start()
    while any(t.is_alive() for t in threads):
        got = sum(p.stat().st_size for p in parts_dir.glob("part*"))
        print(f"  {got / 1e9:.2f} / {args.size / 1e9:.2f} GB", flush=True)
        time.sleep(30)
    sizes = {i: (parts_dir / f"part{i}").stat().st_size for i, _, _ in ranges}
    if any(sizes[i] != e - s + 1 for i, s, e in ranges):
        raise SystemExit(f"incomplete parts {sizes}; rerun to resume")
    with open(args.out, "wb") as out:
        for i, _, _ in ranges:
            with open(parts_dir / f"part{i}", "rb") as part:
                shutil.copyfileobj(part, out, BLOCK * 8)
    got_md5 = md5_file(args.out)
    if args.out.stat().st_size != args.size or got_md5 != args.md5:
        raise SystemExit(f"verification failed: size {args.out.stat().st_size}, md5 {got_md5}; parts kept")
    shutil.rmtree(parts_dir)
    print(f"{args.out}: {args.size:,} bytes, MD5 {got_md5} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
