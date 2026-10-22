#!/usr/bin/env python3
"""Per-signal AUC of the audio forensic signals on the balanced ASVspoof dev subsample.

Reads ``paper_results/audio_heuristics_dev/scores.csv`` (written by
``ml/evaluation/audio_heuristics_dev.py``) and, without running any model,
computes for each signal the ROC AUC for spoof (label 1) against bona fide,
with a 2,000-resample stratified bootstrap 95% interval. The direction is the
one the signal is designed with (higher = more suspicious); it is not flipped
to fit the data.

Rule fixed in GOAL.md before the measurement: a signal may stay in the
synthesis risk only if the lower end of its interval is above 0.60; every
other signal becomes context (computed and shown, not used in the verdict).

Also reports the legacy verdict rates per class with Wilson intervals.

Writes ``signal_auc.json`` next to the scores, ``paper/tables/audio_heuristics_auc.tex``
and the ``audio_heuristics_dev`` section of ``paper_results/INDEX.md``.

Usage::

    python paper/analysis/audio_heuristics_table.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402
from ml.evaluation.stats import bootstrap_auc_ci, wilson_interval  # noqa: E402
from paper.analysis.index_tools import update_index_section  # noqa: E402

RESULTS = REPO_ROOT / "paper_results/audio_heuristics_dev"
TABLE = REPO_ROOT / "paper/tables/audio_heuristics_auc.tex"
KEEP_LOWER_BOUND = 0.60
SIGNALS = [  # (column, description)
    ("lcnn_prob", "LCNN (ASVspoof-trained) probability"),
    ("glottal_anomaly", "Glottal anomaly score"),
    ("coarticulation_anomaly", "Coarticulation anomaly score"),
    ("environment_anomaly", "Environment / mains-hum anomaly"),
    ("enf_splice_flag", "Mains-hum splice flag"),
    ("enf_phase_slips", "Mains-hum phase slips"),
    ("splice_worst_segment", "Splice timeline: worst segment"),
    ("splice_f1_spikes", "Splice timeline: F1 spikes"),
    ("splice_flag", "Splice timeline flag"),
    ("model_rawnet", "Untrained SincRawNet branch"),
    ("model_spectral_smoothness", "Spectral-smoothness branch (labelled WavLM)"),
    ("model_tabular", "Tabular rules branch"),
    ("model_stage_fused", "Legacy model stage (fused)"),
    ("r_synth", "Synthesis risk R_synth"),
    ("r_tamper", "Tampering risk R_tamper"),
    ("legacy_final_prob", "Legacy final probability"),
]


def _float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def add_lcnn_probability(rows: list[dict]) -> dict:
    """The served LCNN's calibrated probability, from its saved dev scores (no model is run)."""
    calibration = json.loads((REPO_ROOT / "paper/config/audio_calibration.json").read_text(encoding="utf-8"))
    path = REPO_ROOT / calibration["fit_data"]["file"]
    with open(path, newline="", encoding="utf-8") as handle:
        cm = {r["utt_id"]: float(r["score"]) for r in csv.DictReader(handle)}
    a, b = calibration["a"], calibration["b"]
    for row in rows:
        row["lcnn_prob"] = str(1.0 / (1.0 + np.exp(-(a * -cm[row["utt_id"]] + b))))
    return {"scores_file": path.relative_to(REPO_ROOT).as_posix(), "checkpoint": calibration["checkpoint"],
            "note": "selected and calibrated on dev, so its dev AUC is optimistic"}


def main() -> int:
    scores_path = RESULTS / "scores.csv"
    with open(scores_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    lcnn_source = add_lcnn_probability(rows)
    labels = np.array([int(r["label"]) for r in rows])
    print(f"{len(rows):,} utterances ({int((labels == 0).sum()):,} bona fide, {int((labels == 1).sum()):,} spoof)")

    signals = {}
    for column, description in SIGNALS:
        if column not in rows[0]:
            continue
        values = np.array([_float(r[column]) for r in rows])
        ok = np.isfinite(values)
        entry: dict = {"description": description, "n": int(ok.sum()), "n_missing": int((~ok).sum())}
        if len(np.unique(values[ok])) < 2 or len(np.unique(labels[ok])) < 2:
            entry.update({"auc": None, "ci95": None, "decision": "context (constant or one class)"})
        else:
            entry.update(bootstrap_auc_ci(labels[ok], values[ok], n_resamples=2000, seed=0))
            keep = entry["ci95"][0] > KEEP_LOWER_BOUND
            entry["decision"] = "synthesis risk" if keep else "context"
        signals[column] = entry
        auc = "n/a" if entry["auc"] is None else f"{entry['auc']:.3f} [{entry['ci95'][0]:.3f}, {entry['ci95'][1]:.3f}]"
        print(f"  {column:28s} AUC {auc:26s} -> {entry['decision']}")

    verdicts = {}
    for name, label in (("bonafide", 0), ("spoof", 1)):
        subset = [r["legacy_verdict"] for r in rows if int(r["label"]) == label]
        verdicts[name] = {}
        for verdict in sorted(set(r["legacy_verdict"] for r in rows)):
            k = sum(v == verdict for v in subset)
            low, high = wilson_interval(k, len(subset))
            verdicts[name][verdict] = {"count": k, "n": len(subset), "rate": k / len(subset), "ci95": [low, high]}

    seconds = np.array([_float(r["seconds"]) for r in rows])
    result = {
        "scores_file": scores_path.name,
        "rule": f"keep in synthesis risk only if the bootstrap 95% lower bound > {KEEP_LOWER_BOUND}",
        "direction": "higher signal = more likely spoof (as designed; not flipped)",
        "lcnn_prob_source": lcnn_source,
        "signals": signals,
        "legacy_verdict_rates": verdicts,
        "seconds_per_utterance": {"median": float(np.nanmedian(seconds)), "mean": float(np.nanmean(seconds))},
    }
    out = RESULTS / "signal_auc.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [r"\begin{tabular}{lcc}", r"\toprule", r"Signal & AUC [95\% CI] & Role \\", r"\midrule"]
    for entry in signals.values():
        auc = "--" if entry["auc"] is None else f"{entry['auc']:.3f} [{entry['ci95'][0]:.3f}, {entry['ci95'][1]:.3f}]"
        lines.append(f"{entry['description']} & {auc} & {entry['decision'].split(' (')[0]} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rel = out.relative_to(REPO_ROOT).as_posix()
    index_rows = []
    for column, entry in signals.items():
        if entry["auc"] is not None:
            value = f"{entry['auc']:.3f} [{entry['ci95'][0]:.3f}, {entry['ci95'][1]:.3f}]"
            index_rows.append((f"Audio dev subsample: AUC of {entry['description']}", value, f"`{rel}`",
                               f"`signals.{column}.auc`, `.ci95`", "3"))
    for name in ("bonafide", "spoof"):
        for verdict, entry in verdicts[name].items():
            index_rows.append((f"Audio dev subsample: legacy verdict {verdict}, {name}",
                               f"{entry['rate'] * 100:.1f}% ({entry['count']}/{entry['n']})", f"`{rel}`",
                               f"`legacy_verdict_rates.{name}.{verdict}.rate`", "3"))
    update_index_section("audio_heuristics_dev", index_rows)
    print(f"Wrote {out.relative_to(REPO_ROOT)}, {TABLE.relative_to(REPO_ROOT)} and INDEX.md rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
