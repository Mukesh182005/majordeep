#!/usr/bin/env python3
"""Choose the served LCNN and fit its probability calibration on ASVspoof dev (Phase 3).

Rules, fixed before looking at any result they produce; the eval split is not read:

* Served checkpoint: of the seeds in ``paper/config/audio_model_selection.json``,
  the one with the lowest dev EER (ties: the lower seed).
* Calibration: class-balanced Platt scaling on that checkpoint's dev scores,
  ``p(spoof) = sigmoid(a * m + b)`` with ``m`` the mean window spoof logit
  (``m = -CM score``). Each class carries half the total weight, so ``p`` is
  calibrated for equal priors; dev itself is about 90% spoofed, and a fit at
  that prior would push every probability towards "spoof".

Writes ``paper/config/audio_calibration.json``, which the backend reads in
``audio_model_source="lcnn_asvspoof"`` mode (the checkpoint's sha256 is
checked at load time).

Usage (PowerShell, from the repository root)::

    python ml/evaluation/calibrate_audio_lcnn.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

SELECTION_FILE = REPO_ROOT / "paper/config/audio_model_selection.json"
CALIBRATION_FILE = REPO_ROOT / "paper/config/audio_calibration.json"
DEV_RUNS = REPO_ROOT / "paper_results/audio_asvspoof2019la/dev_runs"


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def balanced_log_loss(x: np.ndarray, y: np.ndarray, a: float, b: float) -> float:
    p = np.clip(_sigmoid(a * x + b), 1e-12, 1 - 1e-12)
    return float(0.5 * -np.log(p[y == 1]).mean() + 0.5 * -np.log(1 - p[y == 0]).mean())


def fit_balanced_platt(x, y, max_iter: int = 100, tol: float = 1e-10) -> tuple[float, float]:
    """Newton's method on the class-balanced logistic loss of ``sigmoid(a x + b)``."""
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y).astype(int).ravel()
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("calibration needs both classes")
    w = np.where(y == 1, 0.5 / n1, 0.5 / n0)
    design = np.column_stack([x, np.ones_like(x)])
    theta = np.array([1.0, 0.0])
    loss = balanced_log_loss(x, y, *theta)
    for _ in range(max_iter):
        p = _sigmoid(design @ theta)
        grad = design.T @ (w * (p - y))
        hess = design.T @ (design * (w * p * (1 - p))[:, None])
        step = np.linalg.solve(hess, grad)
        scale = 1.0
        while True:  # halve the step until the loss does not increase
            candidate = theta - scale * step
            new_loss = balanced_log_loss(x, y, *candidate)
            if new_loss <= loss or scale < 1e-6:
                break
            scale *= 0.5
        theta, loss = candidate, new_loss
        if np.abs(scale * step).max() < tol:
            break
    return float(theta[0]), float(theta[1])


def main() -> int:
    from ml.evaluation.asvspoof_metrics import eer
    from ml.evaluation.eval_asvspoof import read_scores
    from ml.preprocessing.build_asvspoof2019_la import sha256_file
    from ml.provenance import collect_provenance

    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    served = min(selection["selected_checkpoints"], key=lambda c: (c["dev_eer"], c["seed"]))
    checkpoint = REPO_ROOT / served["checkpoint"]
    sha = sha256_file(checkpoint)
    if sha != served["sha256"]:
        raise SystemExit(f"{checkpoint.name} does not match the frozen selection (sha256 differs).")

    scores_path = DEV_RUNS / checkpoint.stem / "dev_scores.csv"
    dev = read_scores(scores_path)
    mean_logit, y = -dev["score"], dev["label"]
    a, b = fit_balanced_platt(mean_logit, y)
    p = _sigmoid(a * mean_logit + b)
    dev_eer, threshold = eer(dev["score"][y == 0], dev["score"][y == 1])

    calibration = {
        "purpose": "Phase 3: served LCNN and its probability calibration, fitted on ASVspoof 2019 LA dev only",
        "serving_rule": "of the frozen seeds, the lowest dev EER (ties: lower seed)",
        "checkpoint": served["checkpoint"],
        "checkpoint_sha256": sha,
        "seed": served["seed"],
        "dev_eer": served["dev_eer"],
        "frontend": selection["selected_frontend"],
        "input": "16 kHz waveform as read from the file, without peak normalisation; 4 s windows; "
                 "mean of the window spoof logits",
        "method": "platt_balanced",
        "formula": "p_spoof = 1 / (1 + exp(-(a * mean_spoof_logit + b)))",
        "a": a,
        "b": b,
        "class_weighting": "each class half the total weight (equal priors)",
        "fit_data": {"file": scores_path.relative_to(REPO_ROOT).as_posix(), "sha256": sha256_file(scores_path),
                     "n_bonafide": int((y == 0).sum()), "n_spoof": int((y == 1).sum())},
        "dev_diagnostics": {
            "balanced_log_loss_uncalibrated": balanced_log_loss(mean_logit, y, 1.0, 0.0),
            "balanced_log_loss_calibrated": balanced_log_loss(mean_logit, y, a, b),
            "mean_p_spoof_bonafide": float(p[y == 0].mean()),
            "mean_p_spoof_spoof": float(p[y == 1].mean()),
            "p_spoof_at_dev_eer_threshold": float(_sigmoid(a * -threshold + b)),
            "dev_eer_check": float(dev_eer),
        },
        "decided_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provenance": collect_provenance(seeds=served["seed"]),
    }
    CALIBRATION_FILE.write_text(json.dumps(calibration, indent=2, default=str), encoding="utf-8")
    print(f"Served: {checkpoint.name} (seed {served['seed']}, dev EER {served['dev_eer'] * 100:.3f}%)")
    print(f"Balanced Platt: a = {a:.6f}, b = {b:.6f}; p at the dev EER threshold = "
          f"{calibration['dev_diagnostics']['p_spoof_at_dev_eer_threshold']:.3f}")
    print(f"Wrote {CALIBRATION_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
