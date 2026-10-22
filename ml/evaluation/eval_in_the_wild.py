#!/usr/bin/env python3
"""Score In-the-Wild with the frozen ASVspoof 2019 LA LCNNs (cross-dataset test).

The models were trained on ASVspoof 2019 LA train, with the epoch, front end,
served seed and calibration all chosen on LA dev. In-the-Wild is a different
corpus (public figures, internet audio), so this measures how the LA result
transfers; expect a much higher EER. Nothing here is tuned on it.

* Audio is read and featurised exactly as the backend serves it
  (``app.ml.preprocessing.load_audio`` at 16 kHz, no peak normalisation, then
  ``app.ml.asvspoof_frontend.utterance_lfcc``: every 4 s window), and every
  checkpoint scores the same features: score = minus the mean window spoof
  logit (higher = bona fide).
* Inference is strict float32 (TF32 off for convolutions and matrix products).
* Only the checkpoints frozen in ``paper/config/audio_model_selection.json``
  are accepted, and scoring needs ``--confirm-final-eval``; each run is
  appended to ``eval_log.csv``.
* Resumable: rows are appended per utterance; a restart skips what is done.

Writes, in ``paper_results/audio_in_the_wild/`` (or ``--output-dir``):
``<checkpoint>_scores.csv`` (utt_id, label, score), ``metrics.json`` (EER and
AUC per checkpoint, mean and SD over seeds, the served checkpoint marked) and
``config.json`` (provenance).

Usage (PowerShell; about 31,800 files)::

    python ml/preprocessing/build_in_the_wild.py --licence-confirmed
    python ml/evaluation/eval_in_the_wild.py --confirm-final-eval
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ml.common import REPO_ROOT  # noqa: E402

SELECTION_FILE = REPO_ROOT / "paper/config/audio_model_selection.json"
CALIBRATION_FILE = REPO_ROOT / "paper/config/audio_calibration.json"
DEFAULT_MANIFEST = REPO_ROOT / "data/processed/in_the_wild/manifest.csv"
DEFAULT_OUTPUT = REPO_ROOT / "paper_results/audio_in_the_wild"
SAMPLE_RATE = 16000


def read_manifest(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return [{"utt_id": r["utt_id"], "relative_path": r["relative_path"], "label": int(r["label"])}
                for r in csv.DictReader(handle)]


def frozen_checkpoints(selection_file: Path = SELECTION_FILE) -> list[dict]:
    selection = json.loads(selection_file.read_text(encoding="utf-8"))
    return [{"path": REPO_ROOT / c["checkpoint"], "sha256": c["sha256"], "seed": c.get("seed")}
            for c in selection["selected_checkpoints"]]


def served_checkpoint_name(calibration_file: Path = CALIBRATION_FILE) -> str | None:
    if not calibration_file.is_file():
        return None
    return Path(json.loads(calibration_file.read_text(encoding="utf-8"))["checkpoint"]).name


def strict_float32() -> None:
    import torch

    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False


def load_models(checkpoints: list[dict], device):
    import torch
    from app.ml.models_arch import build_audio_model

    from ml.provenance import sha256_file

    models = []
    for entry in checkpoints:
        sha = sha256_file(entry["path"])
        if sha != entry["sha256"]:
            raise SystemExit(f"{entry['path'].name}: sha256 {sha[:12]}... is not the frozen checkpoint")
        payload = torch.load(entry["path"], map_location="cpu", weights_only=True)
        if payload.get("frontend") != "lfcc":
            raise SystemExit(f"{entry['path'].name}: front end {payload.get('frontend')!r}; this script feeds LFCC")
        model = build_audio_model()
        model.load_state_dict(payload["state_dict"])
        models.append((entry["path"].stem, model.to(device).float().eval()))
    return models


def score_file(path: Path, models, device) -> dict[str, float]:
    """CM score (minus the mean window spoof logit) of one file for every model."""
    import torch
    from app.ml.asvspoof_frontend import utterance_lfcc
    from app.ml.preprocessing import load_audio

    waveform, _ = load_audio(path, SAMPLE_RATE)
    features = torch.from_numpy(utterance_lfcc(np.asarray(waveform, dtype=np.float32))).unsqueeze(1)
    features = features.to(device, dtype=torch.float32)
    with torch.no_grad():
        return {stem: -float(model(features).float().mean()) for stem, model in models}


def done_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    with open(path, newline="", encoding="utf-8") as handle:
        return {r["utt_id"] for r in csv.DictReader(handle)}


def compute_metrics(output_dir: Path, stems: list[str], rows: list[dict], served: str | None) -> dict:
    from ml.evaluation.asvspoof_metrics import eer
    from ml.evaluation.metrics import roc_auc

    labels = {r["utt_id"]: r["label"] for r in rows}
    per_checkpoint = {}
    for stem in stems:
        with open(output_dir / f"{stem}_scores.csv", newline="", encoding="utf-8") as handle:
            scored = list(csv.DictReader(handle))
        y = np.array([labels[r["utt_id"]] for r in scored])
        s = np.array([float(r["score"]) for r in scored])
        value, threshold = eer(s[y == 0], s[y == 1])
        per_checkpoint[stem] = {
            "n_bonafide": int((y == 0).sum()),
            "n_spoof": int((y == 1).sum()),
            "eer": value,
            "eer_threshold": threshold,
            "auc_bonafide_vs_spoof": roc_auc((y == 0).astype(int), s),
            "served": stem == served,
        }
    eers = np.array([m["eer"] * 100 for m in per_checkpoint.values()])
    aucs = np.array([m["auc_bonafide_vs_spoof"] for m in per_checkpoint.values()])

    def sd(values: np.ndarray) -> float | None:
        return float(values.std(ddof=1)) if values.size > 1 else None

    return {
        "dataset": "In-the-Wild (external test; models trained and chosen on ASVspoof 2019 LA only)",
        "score_convention": "higher = bona fide; score = -mean window spoof logit",
        "per_checkpoint": per_checkpoint,
        "summary": {
            "eer_percent": {"mean": float(eers.mean()), "sd": sd(eers), "n": int(eers.size)},
            "auc_bonafide_vs_spoof": {"mean": float(aucs.mean()), "sd": sd(aucs), "n": int(aucs.size)},
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from ml.preprocessing.build_in_the_wild import default_root

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--selection", type=Path, default=SELECTION_FILE, help=argparse.SUPPRESS)
    parser.add_argument("--confirm-final-eval", action="store_true")
    parser.add_argument("--limit", type=int, default=None,
                        help="score only the first N files (smoke test; needs a --output-dir outside paper_results)")
    parser.add_argument("--device", default=None)
    parser.add_argument("--log-every", type=int, default=500)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict | None:
    import torch

    from ml.provenance import collect_provenance

    args = parse_args(argv)
    if not args.confirm_final_eval:
        raise SystemExit("In-the-Wild is a final test set: pass --confirm-final-eval.")
    if args.limit is not None and args.output_dir.resolve().is_relative_to((REPO_ROOT / "paper_results").resolve()):
        raise SystemExit("--limit is for smoke tests: write them outside paper_results with --output-dir.")
    if args.root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --root.")
    if not args.manifest.is_file():
        raise SystemExit(f"{args.manifest} not found: run ml/preprocessing/build_in_the_wild.py first.")

    strict_float32()
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoints = frozen_checkpoints(args.selection)
    models = load_models(checkpoints, device)
    stems = [stem for stem, _ in models]
    rows = read_manifest(args.manifest)
    if args.limit is not None:
        rows = rows[: args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {stem: args.output_dir / f"{stem}_scores.csv" for stem in stems}
    finished = set.intersection(*(done_ids(p) for p in paths.values())) if paths else set()
    todo = [r for r in rows if r["utt_id"] not in finished]
    print(f"{len(rows) - len(todo):,} of {len(rows):,} already scored; scoring {len(todo):,} on {device} "
          f"with {', '.join(stems)}", flush=True)

    already = {stem: done_ids(path) for stem, path in paths.items()}
    t0 = time.perf_counter()
    with contextlib.ExitStack() as stack:
        handles = {}
        for stem, path in paths.items():
            new = not path.is_file()
            handles[stem] = stack.enter_context(open(path, "a", newline="", encoding="utf-8"))
            if new:
                csv.writer(handles[stem]).writerow(["utt_id", "label", "score"])
        for i, row in enumerate(todo, start=1):
            scores = score_file(args.root / row["relative_path"], models, device)
            for stem, score in scores.items():
                if row["utt_id"] not in already[stem]:
                    csv.writer(handles[stem]).writerow([row["utt_id"], row["label"], f"{score:.6f}"])
            if i % args.log_every == 0 or i == len(todo):
                for handle in handles.values():
                    handle.flush()
                rate = i / (time.perf_counter() - t0)
                print(f"  {i:,}/{len(todo):,} files, {rate:.1f}/s, ETA {(len(todo) - i) / rate / 60:.1f} min", flush=True)

    served = served_checkpoint_name()
    metrics = compute_metrics(args.output_dir, stems, rows, Path(served).stem if served else None)
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    config = {
        "manifest": args.manifest.name,
        "checkpoints": [{"name": c["path"].name, "sha256": c["sha256"], "seed": c["seed"]} for c in checkpoints],
        "served_checkpoint": served,
        "limit": args.limit,
        "features": "app.ml.preprocessing.load_audio (16 kHz, no peak normalisation) + app.ml.asvspoof_frontend.utterance_lfcc",
        "inference": "float32, TF32 disabled",
        "provenance": collect_provenance(args.manifest, seeds=[c["seed"] for c in checkpoints]),
    }
    (args.output_dir / "config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    log = args.output_dir / "eval_log.csv"
    new_log = not log.is_file()
    with open(log, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_log:
            writer.writerow(["utc_time", "n_files", "checkpoints", "git_commit", "limit"])
        writer.writerow([datetime.now(UTC).isoformat(timespec="seconds"), len(rows), " ".join(stems),
                         config["provenance"].get("git_commit"), args.limit])
    print(json.dumps(metrics["summary"], indent=2))
    return metrics


if __name__ == "__main__":
    main()
