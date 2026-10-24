#!/usr/bin/env python3
"""Choose, compare and calibrate the codec-trained LCNN on dev only (paper/config/audio_codec_plan.json).

1. Score ``dev`` and ``dev_codec2`` (cached LFCC; plan amendment v2) with every codec-trained seed
   and with the currently served checkpoint, in strict float32 (TF32 off,
   deterministic cuDNN), mean window spoof logit per utterance.
2. Pooled dev EER of each (every re-encoded utterance is its own trial).
3. Served seed = the lowest pooled dev EER (ties: lower seed). It replaces the
   current model only if its pooled dev EER is lower than the current model's.
4. Class-balanced Platt scaling of the served seed's pooled dev mean logits;
   the threshold is the calibrated probability at the pooled dev EER point.

Writes (only with ``--write``)
    paper/config/audio_codec_model_selection.json   the seeds eval may score, and the decision
    paper/config/audio_calibration_codec.json       same schema as audio_calibration.json
    paper_results/audio_codec_model/dev_scores_<checkpoint>.csv

No eval file is read.

Usage (PowerShell)::

    python ml/evaluation/select_codec_model.py            # report only
    python ml/evaluation/select_codec_model.py --write
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

CACHE = REPO_ROOT / "data/processed/asvspoof2019_la/features"
CURRENT_CALIBRATION = REPO_ROOT / "paper/config/audio_calibration.json"
SELECTION_OUT = REPO_ROOT / "paper/config/audio_codec_model_selection.json"
CALIBRATION_OUT = REPO_ROOT / "paper/config/audio_calibration_codec.json"
SCORES_DIR = REPO_ROOT / "paper_results/audio_codec_model"
SEEDS = (0, 1, 2)
DEV_SPLITS = ("dev", "dev_codec2")  # plan amendment v2
TAG = "_codec2"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def strict_scores(checkpoint: Path, caches: list, device) -> list[np.ndarray]:
    """Mean spoof logits per utterance of each cache, strict float32."""
    import torch

    from ml.evaluation.eval_asvspoof import load_model, score_split
    from ml.training.asvspoof_dataset import ASVspoofWindowDataset

    model, _ = load_model(checkpoint, device)
    previous = torch.backends.cuda.matmul.allow_tf32
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        with torch.backends.cudnn.flags(enabled=True, benchmark=False, deterministic=True, allow_tf32=False):
            per_cache = [score_split(model, ASVspoofWindowDataset(c), device) for c in caches]
    finally:
        torch.backends.cuda.matmul.allow_tf32 = previous
    return [np.array([logits[u] for u in c.utt_ids], dtype=np.float64) for c, logits in zip(caches, per_cache)]


def pooled_eer(logits: list[np.ndarray], labels: list[np.ndarray]) -> tuple[float, float]:
    """(EER, mean-logit threshold at the EER point) over all trials of all caches."""
    from ml.evaluation.asvspoof_metrics import eer

    x, y = np.concatenate(logits), np.concatenate(labels)
    value, cm_threshold = eer(-x[y == 0], -x[y == 1])
    return float(value), float(-cm_threshold)


def choose(candidates: dict[int, float], current: float) -> dict:
    """The served seed (lowest pooled dev EER, ties to the lower seed) and whether it replaces the current model."""
    seed = min(candidates, key=lambda s: (candidates[s], s))
    return {"served_seed": seed, "served_pooled_dev_eer": candidates[seed], "current_pooled_dev_eer": current,
            "replaces_current": candidates[seed] < current}


def write_scores(path: Path, caches: list, logits: list[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["split", "utt_id", "attack_id", "label", "mean_spoof_logit"])
        for cache, values in zip(caches, logits):
            for utt, attack, label, value in zip(cache.utt_ids, cache.attack_ids, cache.labels, values, strict=True):
                writer.writerow([cache.split, utt, attack, int(label), f"{value:.6f}"])


def main(argv: list[str] | None = None) -> int:
    import torch

    from ml.evaluation.calibrate_audio_lcnn import _sigmoid, balanced_log_loss, fit_balanced_platt
    from ml.provenance import collect_provenance, sha256_file
    from ml.training.asvspoof_dataset import CachedSplit

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--checkpoint-dir", type=Path, default=REPO_ROOT / "checkpoints")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    caches = [CachedSplit(args.cache, "lfcc", s) for s in DEV_SPLITS]
    labels = [c.labels for c in caches]
    current_cal = json.loads(CURRENT_CALIBRATION.read_text(encoding="utf-8"))
    current_path = args.checkpoint_dir / Path(current_cal["checkpoint"]).name
    if sha256_file(current_path) != current_cal["checkpoint_sha256"]:
        raise SystemExit(f"{current_path.name} differs from the served checkpoint named in the calibration file.")

    results: dict[str, dict] = {}
    for name, path in [("current", current_path)] + [
            (f"seed{s}", args.checkpoint_dir / f"audio_lcnn_asvspoof_lfcc{TAG}_seed{s}.pt") for s in SEEDS]:
        if not path.is_file():
            raise SystemExit(f"{path.name} not found: train all seeds of the plan first.")
        logits = strict_scores(path, caches, device)
        value, threshold = pooled_eer(logits, labels)
        per_split = {c.split: pooled_eer([x], [c.labels])[0] for c, x in zip(caches, logits)}
        results[name] = {"checkpoint": path, "logits": logits, "pooled_dev_eer": value,
                         "logit_threshold": threshold, "per_split_eer": per_split}
        print(f"{name:8s} {path.name}: pooled dev EER {value * 100:.3f}% "
              + " ".join(f"{k} {v * 100:.3f}%" for k, v in per_split.items()))

    decision = choose({s: results[f"seed{s}"]["pooled_dev_eer"] for s in SEEDS}, results["current"]["pooled_dev_eer"])
    served = results[f"seed{decision['served_seed']}"]
    x, y = np.concatenate(served["logits"]), np.concatenate(labels)
    a, b = fit_balanced_platt(x, y)
    p_threshold = float(_sigmoid(a * served["logit_threshold"] + b))
    print(f"served: seed {decision['served_seed']}; replaces current: {decision['replaces_current']}; "
          f"Platt a={a:.4f} b={b:.4f}; p at pooled dev EER = {p_threshold:.4f}")
    if not args.write:
        return 0

    for name, entry in results.items():
        write_scores(SCORES_DIR / f"dev_scores_{entry['checkpoint'].stem}.csv", caches, entry["logits"])
    provenance = collect_provenance(None)
    selection = {
        "purpose": "Codec-trained LCNN: seed choice and replacement decision on dev only (audio_codec_plan.json)",
        "dev_splits": list(DEV_SPLITS),
        "scoring": "strict float32 (TF32 off, deterministic cuDNN), mean window spoof logit, pooled EER",
        "selected_frontend": "lfcc",
        "selected_checkpoints": [
            {"seed": s, "checkpoint": _rel(results[f"seed{s}"]["checkpoint"]),
             "sha256": sha256_file(results[f"seed{s}"]["checkpoint"]),
             "dev_eer": results[f"seed{s}"]["pooled_dev_eer"], "per_split_eer": results[f"seed{s}"]["per_split_eer"]}
            for s in SEEDS],
        "current_model": {"checkpoint": _rel(current_path), "sha256": current_cal["checkpoint_sha256"],
                          "pooled_dev_eer": results["current"]["pooled_dev_eer"],
                          "per_split_eer": results["current"]["per_split_eer"]},
        **decision,
        "decided_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provenance": provenance,
    }
    SELECTION_OUT.write_text(json.dumps(selection, indent=2, default=str) + "\n", encoding="utf-8")
    path = served["checkpoint"]
    calibration = {
        "purpose": "Codec-trained LCNN and its calibration, fitted on pooled ASVspoof 2019 LA dev + dev_codec only",
        "serving_rule": "of seeds 0-2, the lowest pooled dev EER (ties: lower seed)",
        "checkpoint": _rel(path),
        "checkpoint_sha256": sha256_file(path),
        "seed": decision["served_seed"],
        "dev_eer": served["pooled_dev_eer"],
        "frontend": "lfcc",
        "input": "16 kHz waveform as read from the file, without peak normalisation; 4 s windows; "
                 "mean of the window spoof logits",
        "method": "platt_balanced",
        "formula": "p_spoof = 1 / (1 + exp(-(a * mean_spoof_logit + b)))",
        "a": a,
        "b": b,
        "class_weighting": "each class half the total weight (equal priors)",
        "fit_data": {"file": _rel(SCORES_DIR / f"dev_scores_{path.stem}.csv"), "splits": list(DEV_SPLITS),
                     "n_bonafide": int((y == 0).sum()), "n_spoof": int((y == 1).sum())},
        "dev_diagnostics": {
            "balanced_log_loss_uncalibrated": balanced_log_loss(x, y, 1.0, 0.0),
            "balanced_log_loss_calibrated": balanced_log_loss(x, y, a, b),
            "p_spoof_at_dev_eer_threshold": p_threshold,
            "dev_eer_check": served["pooled_dev_eer"],
        },
        "decided_utc": selection["decided_utc"],
        "provenance": provenance,
    }
    CALIBRATION_OUT.write_text(json.dumps(calibration, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {_rel(SELECTION_OUT)}, {_rel(CALIBRATION_OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
