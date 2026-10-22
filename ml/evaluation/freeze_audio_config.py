#!/usr/bin/env python3
"""Freeze the audio verdict rule (Phase 3 task 6) from dev data only.

Writes ``paper/config/frozen_audio_config.json``, which the backend reads in
``AUDIO_MODEL_SOURCE=lcnn_asvspoof`` mode. Every input is development data or
a rule fixed in advance; no evaluation data is read.

* Synthesis risk = the calibrated LCNN probability alone. A heuristic signal
  may carry weight only if the lower end of its bootstrap 95 % AUC interval on
  the balanced dev subsample exceeds 0.60 (rule fixed in GOAL.md before the
  measurement); the signals are read from
  ``paper_results/audio_heuristics_dev/signal_auc.json`` and every one that
  fails is recorded with its bound. Tampering risk is reported, not used.
* Threshold = the calibrated spoof probability at the dev EER operating point
  (``paper/config/audio_calibration.json``, dev only).
* Inconclusive band = the platform's default UNCERTAIN_BAND (0.08), fixed in
  advance for every modality; not tuned on audio.
* For information only: verdict rates on the full dev split under the rule,
  from the served checkpoint's saved dev scores.

The frozen file is never overwritten silently: pass ``--replace-reason`` to
replace it (the reason is stored). Anything scored with an earlier version must
then be re-scored or reported as post hoc.

Usage (PowerShell)::

    python ml/evaluation/freeze_audio_config.py
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

CALIBRATION_FILE = REPO_ROOT / "paper/config/audio_calibration.json"
HEURISTICS_FILE = REPO_ROOT / "paper_results/audio_heuristics_dev/signal_auc.json"
OUTPUT = REPO_ROOT / "paper/config/frozen_audio_config.json"
UNCERTAIN_BAND = 0.08  # the platform default (backend/app/config.py), fixed before any audio result
AUC_LOWER_BOUND_RULE = 0.60


def _rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def verdict_rates(probabilities: np.ndarray, labels: np.ndarray, low: float, high: float) -> dict:
    """Share of authentic / inconclusive / flagged per class under the rule."""
    out = {}
    for name, value in (("bonafide", 0), ("spoof", 1)):
        p = probabilities[labels == value]
        out[name] = {
            "n": int(p.size),
            "authentic": float(np.mean(p < low)) if p.size else None,
            "inconclusive": float(np.mean((p >= low) & (p < high))) if p.size else None,
            "flagged": float(np.mean(p >= high)) if p.size else None,
        }
    return out


def build_config(calibration_file: Path = CALIBRATION_FILE, heuristics_file: Path = HEURISTICS_FILE) -> dict:
    from ml.provenance import collect_provenance, sha256_file

    calibration = json.loads(calibration_file.read_text(encoding="utf-8"))
    threshold = float(calibration["dev_diagnostics"]["p_spoof_at_dev_eer_threshold"])
    low, high = threshold - UNCERTAIN_BAND, threshold + UNCERTAIN_BAND

    signals = json.loads(heuristics_file.read_text(encoding="utf-8"))["signals"]
    weights = {"lcnn_probability": 1.0}
    excluded = {}
    for name, entry in signals.items():
        if name == "lcnn_prob":
            continue
        lower = (entry.get("ci95") or [None])[0]
        if lower is not None and lower > AUC_LOWER_BOUND_RULE:
            raise SystemExit(f"{name} passes the AUC rule (lower bound {lower:.3f}); this script assumes none does. "
                             "Decide its weight on dev before freezing.")
        excluded[name] = {"auc": entry.get("auc"), "ci95_lower": lower, "decision": "context only (weight 0)"}

    dev_file = REPO_ROOT / calibration["fit_data"]["file"]
    with open(dev_file, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    labels = np.array([int(r["label"]) for r in rows])
    mean_logit = -np.array([float(r["score"]) for r in rows])
    a, b = float(calibration["a"]), float(calibration["b"])
    probabilities = 1.0 / (1.0 + np.exp(-(a * mean_logit + b)))

    return {
        "purpose": "Phase 3 task 6: the audio verdict rule in AUDIO_MODEL_SOURCE=lcnn_asvspoof mode, fixed on dev only",
        "audio_model_source": "lcnn_asvspoof",
        "checkpoint": calibration["checkpoint"],
        "checkpoint_sha256": calibration["checkpoint_sha256"],
        "synthesis_risk_weights": weights,
        "tampering_risk_in_verdict": False,
        "heuristics_rule": f"weight > 0 only if the bootstrap 95% AUC lower bound on the balanced dev subsample exceeds {AUC_LOWER_BOUND_RULE}",
        "heuristics_excluded": excluded,
        "threshold": threshold,
        "threshold_rule": "calibrated spoof probability at the dev EER operating point (audio_calibration.json dev_diagnostics)",
        "inconclusive_band": UNCERTAIN_BAND,
        "band_rule": "the platform default UNCERTAIN_BAND, fixed in advance for every modality; not tuned on audio",
        "authentic_below": low,
        "flagged_at_or_above": high,
        "decision_rule": (f"LCNN spoof probability p: authentic if p < {low:.4f}, flagged (AI-generated) if "
                          f"p >= {high:.4f}, inconclusive otherwise; heuristic signals carry no weight"),
        "dev_verdict_rates_information_only": {
            "source": _rel(dev_file),
            "note": "dev holds only the training attacks A01-A06 and was used for selection and calibration, so these rates are optimistic",
            **verdict_rates(probabilities, labels, low, high),
        },
        "inputs": {
            "calibration": {"file": _rel(calibration_file), "sha256": sha256_file(calibration_file)},
            "heuristics": {"file": _rel(heuristics_file), "sha256": sha256_file(heuristics_file)},
        },
        "frozen_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provenance": collect_provenance(),
    }


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--replace-reason", default="")
    args = parser.parse_args(argv)
    if args.output.is_file() and not args.replace_reason:
        raise SystemExit(f"{args.output.name} is already frozen; pass --replace-reason to replace it.")
    config = build_config()
    if args.replace_reason:
        config["replaces_previous_because"] = args.replace_reason
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    print(config["decision_rule"])
    print(json.dumps({k: v for k, v in config["dev_verdict_rates_information_only"].items() if k in ("bonafide", "spoof")}, indent=2))
    return config


if __name__ == "__main__":
    main()
