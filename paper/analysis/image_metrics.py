#!/usr/bin/env python3
"""Metrics, tables and figures from a per-image scores file (JSON Lines).

Reads the output of ``ml/evaluation/eval_image_detectors.py`` and computes,
per condition (original, jpeg75, screenshot, ...):

* ROC AUC with a stratified 2,000-resample bootstrap 95% interval, for the
  fused score ("ours"), each detector alone, the uncropped score where present
  and every extra scorer;
* DeLong tests of the fused score against every other column, on the same images;
* real images scored >= 0.5 and AI images scored < 0.5, with Wilson intervals;
* end-to-end verdict rates per class with Wilson intervals (if recorded);
* per-generator detection rates (score >= 0.5) with Wilson intervals;
* expected calibration error (15 bins) and a reliability diagram.

Writes ``metrics.json`` to ``--out-dir``, LaTeX snippets
``paper/tables/<prefix>_*.tex``, the figure ``paper/figures/<prefix>_reliability.pdf``
and the ``<prefix>`` section of ``paper_results/INDEX.md``. It never runs a model.

Usage::

    python paper/analysis/image_metrics.py --scores paper_results/image_h560/scores.jsonl `
        --out-dir paper_results/image_h560 --prefix image_h560
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

THRESHOLD = 0.5
OURS = "fused"


def load_scores(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score_columns(records: list[dict]) -> dict[str, np.ndarray]:
    """Every score column as an array aligned with ``records`` (NaN where absent)."""
    names: dict[str, None] = {OURS: None}
    for r in records:
        for k in r.get("detectors", {}):
            names[f"detector:{k}"] = None
        for k in r.get("extra", {}):
            names[f"extra:{k}"] = None
    columns = {}
    for name in names:
        values = []
        for r in records:
            if name == OURS:
                value = r.get("fused")
            elif name.startswith("detector:"):
                value = r.get("detectors", {}).get(name.split(":", 1)[1])
            else:
                value = r.get("extra", {}).get(name.split(":", 1)[1])
            values.append(np.nan if value is None else float(value))
        columns[name] = np.array(values, dtype=np.float64)
    if any("fused_uncropped" in r for r in records):
        # Uncropped score where borders were cropped; identical to fused elsewhere.
        columns["fused_without_border_crop"] = np.array(
            [float(r.get("fused_uncropped", r.get("fused")) if r.get("fused") is not None else np.nan) for r in records]
        )
    return columns


def column_metrics(labels: np.ndarray, scores: np.ndarray, n_resamples: int, seed: int) -> dict:
    from ml.evaluation.stats import bootstrap_auc_ci, expected_calibration_error, rate_with_ci

    ok = ~np.isnan(scores)
    labels, scores = labels[ok], scores[ok]
    return {
        "n": int(ok.sum()),
        "auc": bootstrap_auc_ci(labels, scores, n_resamples=n_resamples, seed=seed),
        "real_at_or_above_threshold": rate_with_ci(scores[labels == 0] >= THRESHOLD),
        "ai_below_threshold": rate_with_ci(scores[labels == 1] < THRESHOLD),
        "ai_detected": rate_with_ci(scores[labels == 1] >= THRESHOLD),
        "calibration": expected_calibration_error(labels, scores, n_bins=15),
    }


def condition_metrics(records: list[dict], n_resamples: int = 2000, seed: int = 0) -> dict:
    from ml.evaluation.stats import delong_test, rate_with_ci

    labels = np.array([r["label"] for r in records], dtype=int)
    columns = score_columns(records)
    result: dict = {
        "n_images": len(records),
        "n_real": int((labels == 0).sum()),
        "n_ai": int((labels == 1).sum()),
        "threshold": THRESHOLD,
        "columns": {},
        "delong_vs_ours": {},
    }
    for name, scores in columns.items():
        if np.isnan(scores).all() or len(set(labels[~np.isnan(scores)])) < 2:
            continue
        result["columns"][name] = column_metrics(labels, scores, n_resamples, seed)
    ours = columns[OURS]
    for name, scores in columns.items():
        if name == OURS or name not in result["columns"]:
            continue
        both = ~np.isnan(ours) & ~np.isnan(scores)
        result["delong_vs_ours"][name] = {"n": int(both.sum()), **delong_test(labels[both], ours[both], scores[both])}

    generators = sorted({r["generator"] for r in records if r["label"] == 1})
    result["per_generator"] = {}
    for generator in generators:
        mask = np.array([r["generator"] == generator for r in records])
        entry = {"n": int(mask.sum())}
        for name, scores in columns.items():
            values = scores[mask & ~np.isnan(scores)]
            if values.size:
                entry[name] = rate_with_ci(values >= THRESHOLD)
        result["per_generator"][generator] = entry

    e2e = [r for r in records if "end_to_end" in r]
    if e2e:
        verdicts: dict[str, dict] = {}
        for label, cls in ((0, "real"), (1, "ai")):
            group = [r["end_to_end"]["verdict"] for r in e2e if r["label"] == label]
            entry: dict = {"n": len(group)}
            for verdict in ("AUTHENTIC", "INCONCLUSIVE", "MANIPULATED"):
                entry[verdict] = rate_with_ci([g == verdict for g in group])
            verdicts[cls] = entry
        result["end_to_end_verdicts"] = verdicts
        result["verdict_basis_counts"] = {}
        for r in e2e:
            basis = r["end_to_end"].get("verdict_basis")
            result["verdict_basis_counts"][basis] = result["verdict_basis_counts"].get(basis, 0) + 1
    return result


def _ci(entry: dict, scale: float = 100.0, digits: int = 1) -> str:
    low, high = entry["ci95"]
    return f"{entry['rate'] * scale:.{digits}f} [{low * scale:.{digits}f}, {high * scale:.{digits}f}]"


def write_tables(metrics: dict, prefix: str) -> list[Path]:
    tables = REPO_ROOT / "paper/tables"
    tables.mkdir(parents=True, exist_ok=True)
    written = []
    for condition, m in metrics["conditions"].items():
        lines = [
            "% Generated by paper/analysis/image_metrics.py -- do not edit.",
            "\\begin{tabular}{lccc}", "\\hline",
            "Method & AUC [95\\% CI] & Real $\\geq 0.5$ (\\%) & AI detected (\\%) \\\\", "\\hline",
        ]
        for name, c in m["columns"].items():
            auc = c["auc"]
            label = name.replace("detector:", "").replace("extra:", "").replace("_", "\\_")
            lines.append(
                f"{label} & {auc['auc']:.3f} [{auc['ci95'][0]:.3f}, {auc['ci95'][1]:.3f}] & "
                f"{_ci(c['real_at_or_above_threshold'])} & {_ci(c['ai_detected'])} \\\\"
            )
        lines += ["\\hline", "\\end{tabular}", ""]
        path = tables / f"{prefix}_{condition}_main.tex"
        path.write_text("\n".join(lines), encoding="utf-8")
        written.append(path)

        gen_lines = [
            "% Generated by paper/analysis/image_metrics.py -- do not edit.",
            "\\begin{tabular}{lcc}", "\\hline", "Generator & $n$ & Detected by ours (\\%) \\\\", "\\hline",
        ]
        for generator, entry in m["per_generator"].items():
            if OURS in entry:
                escaped = generator.replace("_", "\\_")
                gen_lines.append(f"{escaped} & {entry['n']} & {_ci(entry[OURS])} \\\\")
        gen_lines += ["\\hline", "\\end{tabular}", ""]
        path = tables / f"{prefix}_{condition}_per_generator.tex"
        path.write_text("\n".join(gen_lines), encoding="utf-8")
        written.append(path)
    return written


def write_reliability(metrics: dict, prefix: str) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = REPO_ROOT / "paper/figures"
    figures.mkdir(parents=True, exist_ok=True)
    written = []
    for condition, m in metrics["conditions"].items():
        calibration = m["columns"][OURS]["calibration"]
        bins = [b for b in calibration["bins"] if b["count"]]
        fig, ax = plt.subplots(figsize=(3.2, 3.0))
        ax.plot([0, 1], [0, 1], ls="--", lw=0.8, color="grey")
        ax.plot([b["mean_probability"] for b in bins], [b["fraction_positive"] for b in bins], marker="o", lw=1)
        ax.set_xlabel("Mean predicted P(AI)")
        ax.set_ylabel("Fraction AI-generated")
        ax.set_title(f"ECE = {calibration['ece']:.3f}", fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        fig.tight_layout()
        path = figures / f"{prefix}_{condition}_reliability.pdf"
        fig.savefig(path)
        plt.close(fig)
        written.append(path)
    return written


def main() -> int:
    from ml.preprocessing.build_asvspoof2019_la import sha256_file
    from ml.provenance import collect_provenance
    from paper.analysis.index_tools import update_index_section

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True, help="e.g. image_h560 or image_t2")
    parser.add_argument("--phase", default="4")
    parser.add_argument("--n-resamples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    records = load_scores(args.scores)
    conditions = sorted({r["condition"] for r in records})
    metrics = {
        "scores_file": args.scores.as_posix(),
        "scores_sha256": sha256_file(args.scores),
        "bootstrap": {"n_resamples": args.n_resamples, "seed": args.seed, "stratified": True},
        "conditions": {c: condition_metrics([r for r in records if r["condition"] == c], args.n_resamples, args.seed)
                       for c in conditions},
        "provenance": collect_provenance(seeds=args.seed),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    write_tables(metrics, args.prefix)
    write_reliability(metrics, args.prefix)

    rel = metrics_path.resolve().relative_to(REPO_ROOT).as_posix()
    rows = []
    for condition, m in metrics["conditions"].items():
        ours = m["columns"].get(OURS)
        if not ours:
            continue
        key = f"conditions.{condition}.columns.{OURS}"
        rows += [
            (f"{args.prefix} {condition}: fused AUC", f"{ours['auc']['auc']:.3f}", rel, f"{key}.auc.auc", args.phase),
            (f"{args.prefix} {condition}: fused AUC 95% CI", f"{ours['auc']['ci95'][0]:.3f}-{ours['auc']['ci95'][1]:.3f}",
             rel, f"{key}.auc.ci95", args.phase),
            (f"{args.prefix} {condition}: real >= 0.5 (%)", f"{ours['real_at_or_above_threshold']['rate'] * 100:.1f}",
             rel, f"{key}.real_at_or_above_threshold.rate", args.phase),
            (f"{args.prefix} {condition}: AI detected (%)", f"{ours['ai_detected']['rate'] * 100:.1f}", rel,
             f"{key}.ai_detected.rate", args.phase),
        ]
    update_index_section(args.prefix, rows)
    print(f"Wrote {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
