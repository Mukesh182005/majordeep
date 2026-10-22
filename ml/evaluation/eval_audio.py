#!/usr/bin/env python3
"""Summarise the served audio model's evaluation into results/audio_eval.json.

Reads saved score files only; no model is run and no test set is re-scored.

* ASVspoof 2019 LA eval: the served checkpoint's per-utterance scores
  (``paper_results/audio_asvspoof2019la/eval/<checkpoint>_eval_scores.csv``,
  written once by ``eval_asvspoof.py --confirm-final-eval``). EER and AUC are
  recomputed from them and must agree with the stored metrics file; min t-DCF
  is taken from that file (it needs the organisers' ASV scores). The 3-seed
  mean and SD come from ``paper_results/audio_asvspoof2019la/metrics.json``.
* In-the-Wild, with ``--itw``: the served checkpoint's scores from
  ``eval_in_the_wild.py`` (``paper_results/audio_in_the_wild/``).

Writes ``results/audio_eval.json`` and ``results/figures/audio_roc.png``.

Usage (PowerShell)::

    python ml/evaluation/eval_audio.py            # LA eval only
    python ml/evaluation/eval_audio.py --itw      # plus In-the-Wild, once scored
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

CALIBRATION_FILE = REPO_ROOT / "paper/config/audio_calibration.json"
LA_DIR = REPO_ROOT / "paper_results/audio_asvspoof2019la"
ITW_DIR = REPO_ROOT / "paper_results/audio_in_the_wild"
OUTPUT = REPO_ROOT / "results/audio_eval.json"
FIGURE = REPO_ROOT / "results/figures/audio_roc.png"


def _rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_scores(path: Path, label_key: str = "label") -> tuple[np.ndarray, np.ndarray]:
    """(labels 1 = spoof, scores higher = bona fide) from a score CSV."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return np.array([int(r[label_key]) for r in rows]), np.array([float(r["score"]) for r in rows])


def score_metrics(labels: np.ndarray, scores: np.ndarray) -> dict:
    from ml.evaluation.asvspoof_metrics import eer
    from ml.evaluation.metrics import roc_auc

    value, threshold = eer(scores[labels == 0], scores[labels == 1])
    return {
        "n_bonafide": int((labels == 0).sum()),
        "n_spoof": int((labels == 1).sum()),
        "eer": value,
        "eer_threshold": threshold,
        "auc_bonafide_vs_spoof": roc_auc((labels == 0).astype(int), scores),
    }


def la_eval(stem: str, la_dir: Path = LA_DIR) -> dict:
    from ml.provenance import sha256_file

    scores_path = la_dir / "eval" / f"{stem}_eval_scores.csv"
    stored_path = la_dir / "eval" / f"{stem}_eval_metrics.json"
    if not scores_path.is_file():
        raise SystemExit(f"{_rel(scores_path)} not found: the served checkpoint has not been scored on LA eval.")
    labels, scores = read_scores(scores_path)
    result = score_metrics(labels, scores)
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    for key in ("eer", "auc_bonafide_vs_spoof", "n_bonafide", "n_spoof"):
        if abs(float(result[key]) - float(stored[key])) > 1e-9:
            raise SystemExit(f"{key} recomputed from {scores_path.name} ({result[key]}) differs from "
                             f"{stored_path.name} ({stored[key]}); refusing to summarise inconsistent files.")
    result["min_tdcf"] = stored.get("min_tdcf")
    result["per_attack_eer"] = {k: v["eer"] for k, v in stored.get("per_attack", {}).items()}
    result["sources"] = {
        "scores": {"file": _rel(scores_path), "sha256": sha256_file(scores_path)},
        "metrics": {"file": _rel(stored_path), "sha256": sha256_file(stored_path), "key_min_tdcf": "min_tdcf"},
    }
    seeds_path = la_dir / "metrics.json"
    if seeds_path.is_file():
        summary = json.loads(seeds_path.read_text(encoding="utf-8"))["summary"]
        result["all_seeds"] = {
            "file": _rel(seeds_path),
            "eer_percent": {k: summary["eer_percent"][k] for k in ("mean", "sd", "n")},
            "min_tdcf": {k: summary["min_tdcf"][k] for k in ("mean", "sd", "n")},
            "auc_bonafide_vs_spoof": {k: summary["auc_bonafide_vs_spoof"][k] for k in ("mean", "sd", "n")},
        }
    result["_curve"] = (labels, scores)
    return result


def itw_eval(stem: str, itw_dir: Path = ITW_DIR) -> dict:
    from ml.provenance import sha256_file

    scores_path = itw_dir / f"{stem}_scores.csv"
    if not scores_path.is_file():
        raise SystemExit(f"{_rel(scores_path)} not found: run ml/evaluation/eval_in_the_wild.py --confirm-final-eval first.")
    labels, scores = read_scores(scores_path)
    result = score_metrics(labels, scores)
    result["sources"] = {"scores": {"file": _rel(scores_path), "sha256": sha256_file(scores_path)}}
    metrics_path = itw_dir / "metrics.json"
    if metrics_path.is_file():
        result["all_seeds"] = {"file": _rel(metrics_path), **json.loads(metrics_path.read_text(encoding="utf-8"))["summary"]}
    result["_curve"] = (labels, scores)
    return result


def plot_roc(curves: dict[str, tuple[np.ndarray, np.ndarray]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ml.evaluation.metrics import roc_curve

    fig, ax = plt.subplots(figsize=(4.2, 4.0), dpi=150)
    for name, (labels, scores) in curves.items():
        fpr, tpr, _ = roc_curve((labels == 0).astype(int), scores)
        ax.plot(fpr, tpr, label=name)
    ax.plot([0, 1], [0, 1], color="0.7", linewidth=0.8, linestyle="--")
    ax.set_xlabel("False positive rate (spoof accepted as bona fide)")
    ax.set_ylabel("True positive rate (bona fide accepted)")
    ax.set_title("Served audio LCNN: ROC")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main(argv: list[str] | None = None) -> dict:
    from ml.provenance import collect_provenance

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--itw", action="store_true", help="include In-the-Wild (needs eval_in_the_wild.py output)")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figure", type=Path, default=FIGURE)
    args = parser.parse_args(argv)

    calibration = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
    stem = Path(calibration["checkpoint"]).stem
    curves = {}
    la = la_eval(stem)
    curves["ASVspoof 2019 LA eval"] = la.pop("_curve")
    report = {
        "model": {
            "checkpoint": calibration["checkpoint"],
            "checkpoint_sha256": calibration["checkpoint_sha256"],
            "selection": "served seed = lowest dev EER of the frozen seeds (paper/config/audio_calibration.json)",
            "decision_threshold_from_dev": calibration["dev_diagnostics"]["p_spoof_at_dev_eer_threshold"],
        },
        "score_convention": "higher = bona fide; score = -mean window spoof logit",
        "asvspoof2019_la_eval": la,
    }
    if args.itw:
        itw = itw_eval(stem)
        curves["In-the-Wild"] = itw.pop("_curve")
        report["in_the_wild"] = itw
    report["figure"] = _rel(args.figure)
    report["provenance"] = collect_provenance()
    plot_roc(curves, args.figure)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in la.items() if k in ("eer", "auc_bonafide_vs_spoof", "min_tdcf")}, indent=2))
    return report


if __name__ == "__main__":
    main()
