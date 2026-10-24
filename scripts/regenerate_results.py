#!/usr/bin/env python3
"""Rebuild every file in results/ from the per-item files committed under paper_results/.

No model runs and no dataset is read: each step below is a summariser over
saved scores, so a clean checkout regenerates results/ on any machine.

1. ml/evaluation/eval_audio.py        -> results/audio_eval.json, figures/audio_roc.png
2. scripts/eval_pipeline.py summarise -> results/pipeline_eval.json, figures/audio_pipeline_verdicts.png
3. scripts/robustness.py summarise    -> results/robustness.json, figures/audio_codec_robustness.png
4. scripts/eval_image.py summarise    -> results/image_eval.json (not run until H560 exists)
5. scripts/benchmark_latency.py summarise -> results/latency.json, figures/latency.png

The measurements behind them (re-scoring, timing) are separate commands, each
documented in its script; they need DEEPSENTINEL_DATA and, for eval scoring,
--confirm-final-eval.

``--check`` compares the regenerated files with the committed ones: JSON files
ignoring their top-level ``provenance`` (which records when and where the
summary ran), figures byte for byte. It exits 1 on any difference.

Usage (PowerShell)::

    python scripts/regenerate_results.py
    python scripts/regenerate_results.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ["ml/evaluation/eval_audio.py"],
    ["scripts/eval_pipeline.py", "summarise"],
    ["scripts/robustness.py", "summarise"],
    ["scripts/eval_image.py", "summarise"],
    ["scripts/benchmark_latency.py", "summarise"],
]


def _git_show(path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=REPO_ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def compare(path: Path, committed: bytes | None) -> str | None:
    """None when ``path`` matches the committed version, else what differs."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    if committed is None:
        return f"{rel}: not committed"
    current = path.read_bytes()
    if path.suffix == ".json":
        a, b = json.loads(current), json.loads(committed)
        a.pop("provenance", None)
        b.pop("provenance", None)
        if a != b:
            keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            return f"{rel}: differs in {', '.join(keys)}"
        return None
    if hashlib.sha256(current).digest() != hashlib.sha256(committed).digest():
        return f"{rel}: bytes differ"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare with the committed results/")
    args = parser.parse_args(argv)

    tracked = subprocess.run(["git", "ls-files", "results"], cwd=REPO_ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
    before = {p: (REPO_ROOT / p).stat().st_mtime_ns for p in tracked if (REPO_ROOT / p).is_file()}
    for step in STEPS:
        print(f"> python {' '.join(step)}", flush=True)
        # Relative paths, so provenance records no local absolute path.
        subprocess.run([sys.executable, step[0], *step[1:]], cwd=REPO_ROOT, check=True)
    if not args.check:
        return 0

    problems = []
    produced = sorted(p for p in (REPO_ROOT / "results").rglob("*") if p.is_file())
    for path in produced:
        problem = compare(path, _git_show(path.relative_to(REPO_ROOT).as_posix()))
        if problem:
            problems.append(problem)
    problems += [f"{p}: committed but not regenerated" for p in tracked
                 if not (REPO_ROOT / p).is_file() or (REPO_ROOT / p).stat().st_mtime_ns == before.get(p)]
    for problem in problems:
        print(problem)
    print(f"{len(produced)} files regenerated; {'all match' if not problems else f'{len(problems)} differ'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
