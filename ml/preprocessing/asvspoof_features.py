#!/usr/bin/env python3
"""Feature extraction and on-disk cache for ASVspoof 2019 LA.

Front ends (fixed before any training; never tuned on the eval split):

* ``logmel``: the serving front end, ``log_mel_spectrogram`` from
  ``backend/app/ml/preprocessing.py`` (64 mel bands, 512-point FFT, hop 160 at
  16 kHz, dB relative to the window maximum). Shape (64, 401) per window.
* ``lfcc``: 20 linear-frequency cepstral coefficients plus deltas and double
  deltas. 20 ms Hamming window (320 samples) zero-padded to a 512-point FFT,
  10 ms hop, centred frames, 20 triangular filters equally spaced from 0 to
  8 kHz, natural log with a 1e-10 floor, orthonormal DCT-II keeping c0..c19,
  deltas over a 3-frame window. Shape (60, 401) per window.

Windows: every utterance is cut into 4-second windows (64,000 samples).
An utterance of at most 4 s is repeated until it fills one window. A longer
one gives consecutive non-overlapping windows from the start, plus a final
window holding its last 4 s when a remainder is left. Window 0 is therefore
"the first 4 seconds, repeated if short": the training input. Evaluation
scores every window and averages the logits per utterance.

Cache layout, per front end and split::

    <features>/<frontend>/<split>.npy             float16 [windows, bands, 401]
    <features>/<frontend>/<split>_index.csv       utt_id,label,attack_id,row_start,n_windows
    <features>/<frontend>/<split>.progress.json   resume point
    <features>/<frontend>/frontend.json           parameters and provenance

Features are stored as float16 to halve the disk footprint. Models always
receive float32 (cast at load time); the serving path reproduces the same
rounding by casting through float16.

Usage (PowerShell, from the repository root)::

    python ml/preprocessing/asvspoof_features.py --workers 16
    python ml/preprocessing/asvspoof_features.py --splits train dev --features lfcc
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402  (also puts backend/ on sys.path)

# Windows and LFCC live in the backend so that serving computes the same features.
from app.ml.asvspoof_frontend import (  # noqa: E402,F401
    FRAMES_PER_WINDOW,
    HOP,
    LFCC_COEFFS,
    N_FFT,
    SAMPLE_RATE,
    WINDOW_SAMPLES,
    lfcc_features,
    linear_filterbank,
    utterance_windows,
    window_count,
)

CACHE_DTYPE = np.float16

FRONTENDS = {
    "logmel": {"bands": 64, "description": "log-mel, 64 bands, n_fft 512, hop 160, dB re window max"},
    "lfcc": {
        "bands": 3 * LFCC_COEFFS,
        "description": (
            "LFCC c0-c19 + delta + delta-delta; 20 ms Hamming, n_fft 512, hop 160, "
            "20 linear triangular filters 0-8 kHz, ln floor 1e-10, DCT-II ortho, delta width 3"
        ),
    },
}


# --------------------------------------------------------------------------- front ends
def logmel_features(window: np.ndarray) -> np.ndarray:
    from app.ml.preprocessing import log_mel_spectrogram

    return log_mel_spectrogram(
        window, sample_rate=SAMPLE_RATE, n_mels=64, n_fft=N_FFT, hop_length=HOP
    ).astype(np.float32)


FRONTEND_FUNCTIONS = {"logmel": logmel_features, "lfcc": lfcc_features}


def load_waveform(path: Path) -> np.ndarray:
    import soundfile as sf

    waveform, rate = sf.read(str(path), dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"{path.name}: expected {SAMPLE_RATE} Hz, got {rate}")
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    return waveform


def utterance_features(waveform: np.ndarray, frontends: list[str]) -> dict[str, np.ndarray]:
    """Features of every window of one utterance, per front end: (n_windows, bands, 401)."""
    windows = utterance_windows(waveform)
    out: dict[str, np.ndarray] = {}
    for name in frontends:
        feats = np.stack([FRONTEND_FUNCTIONS[name](w) for w in windows])
        expected = (len(windows), FRONTENDS[name]["bands"], FRAMES_PER_WINDOW)
        if feats.shape != expected:
            raise ValueError(f"{name}: shape {feats.shape}, expected {expected}")
        if not np.isfinite(feats).all():
            raise ValueError(f"{name}: non-finite feature values")
        out[name] = feats
    return out


def _worker(task: tuple[str, list[str]]) -> dict[str, np.ndarray]:
    path, frontends = task
    return utterance_features(load_waveform(Path(path)), frontends)


# --------------------------------------------------------------------------- cache
def _progress_path(frontend_dir: Path, split: str) -> Path:
    return frontend_dir / f"{split}.progress.json"


def write_index(frontend_dir: Path, split: str, rows: list[dict]) -> int:
    """Write the row index for a split; returns the total number of windows."""
    row_start = 0
    with open(frontend_dir / f"{split}_index.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "label", "attack_id", "row_start", "n_windows"])
        for row in rows:
            n = window_count(int(row["num_samples"]))
            writer.writerow([row["utt_id"], row["label"], row["attack_id"], row_start, n])
            row_start += n
    return row_start


def build_cache(
    rows: list[dict],
    la_root: Path,
    features_dir: Path,
    split: str,
    frontends: list[str],
    workers: int = 8,
    manifest_sha256: str | None = None,
    flush_every: int = 2000,
) -> None:
    """Extract (or resume extracting) one split's features for each front end."""
    from multiprocessing import Pool

    rows = [r for r in rows if r["split"] == split]
    if not rows:
        print(f"[{split}] no rows; skipped")
        return

    arrays: dict[str, np.memmap] = {}
    start = len(rows)
    for name in frontends:
        frontend_dir = features_dir / name
        frontend_dir.mkdir(parents=True, exist_ok=True)
        total_windows = write_index(frontend_dir, split, rows)
        shape = (total_windows, FRONTENDS[name]["bands"], FRAMES_PER_WINDOW)
        array_path = frontend_dir / f"{split}.npy"
        progress_path = _progress_path(frontend_dir, split)
        progress = json.loads(progress_path.read_text()) if progress_path.exists() else None
        if (
            progress
            and array_path.exists()
            and progress.get("manifest_sha256") == manifest_sha256
            and progress.get("utterances") == len(rows)
        ):
            arrays[name] = np.lib.format.open_memmap(array_path, mode="r+")
            if arrays[name].shape != shape:
                raise SystemExit(f"{array_path}: shape {arrays[name].shape} != {shape}; delete it to rebuild")
            done = int(progress["done"])
        else:
            arrays[name] = np.lib.format.open_memmap(array_path, mode="w+", dtype=CACHE_DTYPE, shape=shape)
            done = 0
        start = min(start, done)
        (frontend_dir / "frontend.json").write_text(
            json.dumps(
                {
                    "frontend": name,
                    **FRONTENDS[name],
                    "sample_rate": SAMPLE_RATE,
                    "window_samples": WINDOW_SAMPLES,
                    "frames_per_window": FRAMES_PER_WINDOW,
                    "window_rule": "<=4 s: repeat to 4 s; >4 s: consecutive 4 s windows + last 4 s if remainder",
                    "training_input": "window 0 (first 4 s, repeated if short)",
                    "evaluation": "mean of per-window logits",
                    "cache_dtype": str(np.dtype(CACHE_DTYPE)),
                    "manifest_sha256": manifest_sha256,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    if start >= len(rows):
        print(f"[{split}] {', '.join(frontends)}: already complete ({len(rows):,} utterances)")
        return

    starts = np.cumsum([0] + [window_count(int(r["num_samples"])) for r in rows])
    tasks = [(str(la_root / r["relative_path"]), frontends) for r in rows[start:]]
    print(f"[{split}] {', '.join(frontends)}: {len(rows) - start:,} of {len(rows):,} utterances to do "
          f"(resuming at {start:,}) with {workers} workers", flush=True)

    def save_progress(done: int) -> None:
        for name in frontends:
            arrays[name].flush()
            _progress_path(features_dir / name, split).write_text(
                json.dumps(
                    {
                        "done": done,
                        "utterances": len(rows),
                        "complete": done == len(rows),
                        "manifest_sha256": manifest_sha256,
                    }
                ),
                encoding="utf-8",
            )

    t0 = time.perf_counter()
    index = start

    def consume(results) -> None:
        nonlocal index
        for result in results:
            lo, hi = starts[index], starts[index + 1]
            for name in frontends:
                arrays[name][lo:hi] = result[name].astype(CACHE_DTYPE)
            index += 1
            if (index - start) % flush_every == 0 or index == len(rows):
                save_progress(index)
                rate = (index - start) / max(time.perf_counter() - t0, 1e-6)
                eta = (len(rows) - index) / max(rate, 1e-6)
                print(f"  [{split}] {index:,}/{len(rows):,} utterances | {rate:.0f}/s | ETA {eta/60:.1f} min",
                      flush=True)

    if workers <= 1:
        consume(map(_worker, tasks))
    else:
        with Pool(processes=workers) as pool:
            consume(pool.imap(_worker, tasks, chunksize=8))
    save_progress(index)


def parse_args() -> argparse.Namespace:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    parser.add_argument("--asvspoof-root", type=Path, default=default_la_root())
    parser.add_argument("--output", type=Path, default=None, help="default: <manifest folder>/features")
    parser.add_argument("--features", nargs="+", choices=sorted(FRONTENDS), default=["logmel", "lfcc"])
    parser.add_argument("--splits", nargs="+", choices=["train", "dev", "eval"], default=["train", "dev", "eval"])
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 4))
    return parser.parse_args()


def main() -> None:
    from ml.preprocessing.build_asvspoof2019_la import read_manifest, sha256_file

    args = parse_args()
    if args.asvspoof_root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root (the extracted LA folder).")
    if not args.manifest.is_file():
        raise SystemExit(f"No manifest at {args.manifest}; run build_asvspoof2019_la.py first.")
    features_dir = args.output or args.manifest.parent / "features"
    rows = read_manifest(args.manifest)
    manifest_sha = sha256_file(args.manifest)
    for split in args.splits:
        build_cache(rows, args.asvspoof_root, features_dir, split, args.features, args.workers, manifest_sha)
    print(f"Features in {features_dir}")


if __name__ == "__main__":
    main()
