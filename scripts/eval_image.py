#!/usr/bin/env python3
"""Full image pipeline over a labelled manifest, summarised into results/image_eval.json.

``score`` runs ``ml/evaluation/eval_image_detectors.py --end-to-end`` over a
manifest (``image_id, relative_path, label, generator, source, condition,
group``; see ``paper/README.md``), which records per image the scene detector
scores and the verdict ``analyze_image`` gives. ``summarise`` turns the saved
per-image file into, for the original (untransformed) images:

* AUC of the final probability, with a bootstrap 95% interval;
* the false-positive rate on real photographs (verdict MANIPULATED), with a
  Wilson interval;
* recall per generator (AI images given MANIPULATED), with Wilson intervals;
* verdict counts for real and AI images, INCONCLUSIVE included, as a
  confusion matrix;
* the scene-detector metrics of ``paper/analysis/image_metrics.py``;

plus a ROC curve and the confusion matrix in ``results/figures/``.

The 560-image held-out set (H560) is not on this machine (searched on C:, D:
and Google Drive; docs/paper_upgrade/STATUS.md), so no manifest can be built
for it and ``results/image_eval.json`` says so instead of holding numbers. A
manifest whose name starts with ``t2`` is refused until the image
configuration is frozen (``paper/config/frozen_image_config.json``, CLAUDE.md
section 3).

Usage (PowerShell)::

    python scripts/eval_image.py score --manifest paper/manifests/h560.csv --image-root "$env:DEEPSENTINEL_DATA\\H560"
    python scripts/eval_image.py summarise
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_pipeline as ep  # noqa: E402  (also puts the repository and backend/ on sys.path)

REPO_ROOT = ep.REPO_ROOT
MANIFEST = REPO_ROOT / "paper/manifests/h560.csv"
SCORES = REPO_ROOT / "paper_results/image_h560/scores.jsonl"
FROZEN_IMAGE_CONFIG = REPO_ROOT / "paper/config/frozen_image_config.json"
RESULTS_FILE = REPO_ROOT / "results/image_eval.json"
ROC_FIGURE = REPO_ROOT / "results/figures/image_roc.png"
CONFUSION_FIGURE = REPO_ROOT / "results/figures/image_confusion.png"
VERDICTS = ("AUTHENTIC", "INCONCLUSIVE", "MANIPULATED")
NOT_RUN_REASON = (
    "Not run: the 560-image held-out set (H560) is not on this machine (searched on C:, D: and Google Drive, "
    "docs/paper_upgrade/STATUS.md), so paper/manifests/h560.csv cannot be built and no image has been scored. "
    "No number is reported until the images are found."
)


def t2_gate(manifest: Path, frozen_tracked: bool) -> str | None:
    if manifest.stem.lower().startswith("t2") and not frozen_tracked:
        return (f"{manifest.name} is a T2 manifest: commit {ep._rel(FROZEN_IMAGE_CONFIG)} "
                "(paper/config/freeze_image_config.py) before scoring any T2 image.")
    return None


def image_eval_metrics(records: list[dict], n_resamples: int = 2000, seed: int = 0) -> dict:
    """Metrics of the end-to-end verdicts and probabilities on the original images."""
    from ml.evaluation.stats import bootstrap_auc_ci, rate_with_ci
    from paper.analysis.image_metrics import condition_metrics

    originals = [r for r in records if r.get("condition", "original") == "original"]
    scored = [r for r in originals if "end_to_end" in r]
    if not scored:
        raise SystemExit("No end-to-end records: score with --end-to-end.")
    labels = np.array([int(r["label"]) for r in scored])
    probs = np.array([float(r["end_to_end"]["final_probability"]) for r in scored])
    verdicts = [r["end_to_end"]["verdict"] for r in scored]
    counts = {cls: {v: sum(1 for r, verdict in zip(scored, verdicts) if int(r["label"]) == label and verdict == v)
                    for v in VERDICTS}
              for cls, label in (("real", 0), ("ai", 1))}
    per_generator = {}
    for generator in sorted({r["generator"] for r in scored if int(r["label"]) == 1}):
        group = [v for r, v in zip(scored, verdicts) if int(r["label"]) == 1 and r["generator"] == generator]
        per_generator[generator] = rate_with_ci([v == "MANIPULATED" for v in group])
    real = [v for r, v in zip(scored, verdicts) if int(r["label"]) == 0]
    ai = [v for r, v in zip(scored, verdicts) if int(r["label"]) == 1]
    return {
        "n_images": len(scored), "n_real": len(real), "n_ai": len(ai),
        "auc_final_probability": bootstrap_auc_ci(labels, probs, n_resamples=n_resamples, seed=seed),
        "false_positive_rate_real": rate_with_ci([v == "MANIPULATED" for v in real]),
        "inconclusive_rate_real": rate_with_ci([v == "INCONCLUSIVE" for v in real]),
        "recall_ai": rate_with_ci([v == "MANIPULATED" for v in ai]),
        "recall_per_generator": per_generator,
        "verdict_counts": counts,
        "confusion_matrix": {"rows": ["real", "ai"], "columns": list(VERDICTS),
                             "counts": [[counts["real"][v] for v in VERDICTS], [counts["ai"][v] for v in VERDICTS]]},
        "scene_detectors": condition_metrics(originals, n_resamples=n_resamples, seed=seed),
    }


def plot_figures(records: list[dict], metrics: dict, roc_path: Path, confusion_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ml.evaluation.metrics import roc_curve

    surface, ink, muted, mark = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"
    scored = [r for r in records if r.get("condition", "original") == "original" and "end_to_end" in r]
    fpr, tpr, _ = roc_curve(np.array([int(r["label"]) for r in scored]),
                            np.array([float(r["end_to_end"]["final_probability"]) for r in scored]))
    fig, ax = plt.subplots(figsize=(4.2, 4.0), facecolor=surface)
    ax.set_facecolor(surface)
    ax.plot([0, 1], [0, 1], color="#d6d5d0", linewidth=1)
    ax.plot(fpr, tpr, color=mark, linewidth=2)
    auc = metrics["auc_final_probability"]
    ax.set_title(f"Image pipeline ROC, AUC {auc['auc']:.3f}", fontsize=9.5, color=ink, loc="left")
    ax.set_xlabel("False-positive rate", fontsize=8.5, color=muted)
    ax.set_ylabel("True-positive rate", fontsize=8.5, color=muted)
    ax.tick_params(labelsize=8, colors=muted)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    roc_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(roc_path, dpi=150, facecolor=surface)
    plt.close(fig)

    counts = np.array(metrics["confusion_matrix"]["counts"], dtype=float)
    shares = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(4.8, 2.4), facecolor=surface)
    ax.imshow(shares, cmap="Blues", vmin=0, vmax=1)
    for (i, j), value in np.ndenumerate(counts):
        ax.text(j, i, f"{int(value)}\n{shares[i, j] * 100:.1f}%", ha="center", va="center", fontsize=8,
                color="white" if shares[i, j] > 0.55 else ink)
    ax.set_xticks(range(3), [v.capitalize() for v in VERDICTS], fontsize=8.5, color=ink)
    ax.set_yticks(range(2), ["Real photos", "AI images"], fontsize=8.5, color=ink)
    ax.tick_params(length=0)
    ax.set_title("Image pipeline verdicts", fontsize=9.5, color=ink, loc="left")
    fig.tight_layout()
    fig.savefig(confusion_path, dpi=150, facecolor=surface)
    plt.close(fig)


def summarise(scores: Path = SCORES, results_file: Path = RESULTS_FILE, roc_path: Path = ROC_FIGURE,
              confusion_path: Path = CONFUSION_FIGURE) -> dict:
    from ml.provenance import collect_provenance
    from paper.analysis.image_metrics import load_scores

    if scores.is_file():
        records = load_scores(scores)
        metrics = image_eval_metrics(records)
        plot_figures(records, metrics, roc_path, confusion_path)
        payload = {"status": "done", "source": ep._rel(scores), "scores_sha256": ep._sha256(scores),
                   "figures": [ep._rel(roc_path), ep._rel(confusion_path)], **metrics}
    else:
        payload = {"status": "not_run", "reason": NOT_RUN_REASON, "manifest_expected": ep._rel(MANIFEST),
                   "scores_expected": ep._rel(scores)}
    payload["provenance"] = collect_provenance(None)
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {ep._rel(results_file)} ({payload['status']})")
    return payload


def cmd_score(args: argparse.Namespace) -> int:
    if not args.manifest.is_file():
        raise SystemExit(f"{args.manifest} not found. {NOT_RUN_REASON}")
    problem = t2_gate(args.manifest, bool(ep._git("ls-files", "--", ep._rel(FROZEN_IMAGE_CONFIG))))
    if problem:
        raise SystemExit(problem)
    subprocess.run([sys.executable, str(REPO_ROOT / "ml/evaluation/eval_image_detectors.py"),
                    "--manifest", str(args.manifest), "--image-root", str(args.image_root),
                    "--output", str(args.output), "--end-to-end"], check=True)
    if args.output.resolve() == SCORES.resolve():
        summarise()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    score = sub.add_parser("score", help="score a manifest end to end, then summarise")
    score.add_argument("--manifest", type=Path, default=MANIFEST)
    score.add_argument("--image-root", type=Path, required=True)
    score.add_argument("--output", type=Path, default=SCORES)
    sub.add_parser("summarise", help="rebuild results/image_eval.json from the saved scores")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "score":
        return cmd_score(args)
    summarise()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
