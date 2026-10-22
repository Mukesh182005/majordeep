#!/usr/bin/env python3
"""Record every audio signal of the legacy forensic suite on a balanced dev subsample.

Phase 3 measures, on ASVspoof 2019 LA **dev** data only, whether each signal
that feeds the audio verdict separates bona fide from spoofed speech.

* Subsample: 1,000 bona fide and 1,000 spoofed dev utterances, the spoofs
  spread as evenly as possible over attacks A01-A06, drawn with a fixed seed;
  written to ``subsample.csv``.
* Each file is loaded as the application loads it (``load_audio`` at 16 kHz,
  then ``normalize_waveform``) and passed through
  ``run_comprehensive_audio_forensics`` (the full suite, including its plots,
  into a temporary folder).
* The legacy model stage contains ``SincRawNet`` with random, never-trained
  weights; torch is seeded (``--torch-seed``) before the ensemble is built so
  this run is repeatable, and the seed is recorded. The application itself
  uses a different random draw in every process.

**Runs only on the pre-P1 code.** P1 (branch fix/p1-honest-outputs) deleted
the untrained SincRawNet and spectral-smoothness branches this script records.
The committed results in paper_results/audio_heuristics_dev/ were produced at
commit 4daed3f (recorded in their config.json); to reproduce them, check out
that commit. On later code the script stops instead of writing other columns.

Writes ``scores.csv`` (one row per utterance, resumable) and ``config.json``.
The LCNN probability column is added once the Phase 2 model is chosen.

Usage (PowerShell)::

    python ml/evaluation/audio_heuristics_dev.py --limit 20     # timing
    python ml/evaluation/audio_heuristics_dev.py                # all 2,000
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

OUT_DIR = REPO_ROOT / "paper_results/audio_heuristics_dev"
COLUMNS = [
    "utt_id", "label", "attack_id",
    "glottal_anomaly", "coarticulation_anomaly",
    "enf_detected", "enf_phase_slips", "enf_max_slip_deg", "enf_splice_flag", "environment_anomaly",
    "splice_f1_spikes", "splice_worst_segment", "splice_flag",
    "model_stage_fused", "model_rawnet", "model_spectral_smoothness", "model_tabular",
    "r_synth", "r_tamper", "legacy_final_prob", "legacy_verdict", "seconds",
]


def balanced_subsample(rows: list[dict], n_per_class: int, seed: int) -> list[dict]:
    """``n_per_class`` bona fide and spoofed dev rows; spoofs spread evenly over attacks."""
    rng = np.random.default_rng(seed)
    dev = [r for r in rows if r["split"] == "dev"]
    bona = [r for r in dev if r["label"] == 0]
    attacks = sorted({r["attack_id"] for r in dev if r["label"] == 1})
    if len(bona) < n_per_class:
        raise ValueError("not enough bona fide dev utterances")
    chosen = [bona[i] for i in sorted(rng.choice(len(bona), n_per_class, replace=False))]
    base, extra = divmod(n_per_class, len(attacks))
    for k, attack in enumerate(attacks):
        pool = [r for r in dev if r["label"] == 1 and r["attack_id"] == attack]
        take = base + (1 if k < extra else 0)
        chosen += [pool[i] for i in sorted(rng.choice(len(pool), take, replace=False))]
    return chosen


def record_signals(path: Path) -> dict:
    from app.ml.audio import run_comprehensive_audio_forensics
    from app.ml.preprocessing import load_audio, normalize_waveform

    t0 = time.perf_counter()
    waveform, rate = load_audio(path, 16000)
    waveform = normalize_waveform(waveform)
    with tempfile.TemporaryDirectory(prefix="ds-audio-") as evidence_dir:
        result = run_comprehensive_audio_forensics(path, waveform, rate, evidence_dir, job_id="heuristics")
    seconds = time.perf_counter() - t0
    glottal, speech = result["glottal_physics"], result["speech_semantics"]
    enf, splice = result["enf_environment"], result["splicing_timeline"]
    models, fusion = result["models_output"], result["fusion_decision"]
    branches = models.get("model_branch_scores", {})
    enf_forensics = enf.get("enf_forensics", {})
    return {
        "glottal_anomaly": glottal.get("composite_physiological_anomaly_score"),
        "coarticulation_anomaly": speech.get("phonemic_coarticulation_anomaly_score"),
        "enf_detected": int(bool(enf_forensics.get("enf_detected"))),
        "enf_phase_slips": enf_forensics.get("phase_discontinuity_count"),
        "enf_max_slip_deg": enf_forensics.get("max_phase_slip_degrees"),
        "enf_splice_flag": int(bool(enf.get("environmental_splicing_confirmed"))),
        "environment_anomaly": enf.get("environmental_anomaly_score"),
        "splice_f1_spikes": splice.get("first_order_f1_spikes_count"),
        "splice_worst_segment": splice.get("worst_segment_fake_probability"),
        "splice_flag": int(bool(splice.get("splicing_detected"))),
        "model_stage_fused": models.get("fused_ai_probability"),
        "model_rawnet": branches.get("rawnet_waveform_prob"),
        "model_spectral_smoothness": branches.get("wavlm_l18_acoustic_prob"),
        "model_tabular": branches.get("tabular_physics_prob"),
        "r_synth": fusion.get("generative_ai_risk_score"),
        "r_tamper": fusion.get("structural_tampering_risk_score"),
        "legacy_final_prob": fusion.get("calibrated_fake_probability"),
        "legacy_verdict": fusion.get("final_verdict"),
        "seconds": round(seconds, 3),
    }


def main() -> int:
    import torch

    from ml.preprocessing.build_asvspoof2019_la import default_la_root, read_manifest, sha256_file
    from ml.provenance import collect_provenance

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    parser.add_argument("--asvspoof-root", type=Path, default=default_la_root())
    parser.add_argument("--n-per-class", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0, help="subsample seed")
    parser.add_argument("--torch-seed", type=int, default=0, help="seed for the untrained SincRawNet weights")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int, default=None, help="score at most N new utterances (timing)")
    args = parser.parse_args()
    if args.asvspoof_root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")

    rows = read_manifest(args.manifest)
    subsample = balanced_subsample(rows, args.n_per_class, args.seed)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "subsample.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "label", "attack_id"])
        writer.writerows([r["utt_id"], r["label"], r["attack_id"]] for r in subsample)

    torch.manual_seed(args.torch_seed)
    try:
        from app.ml.audio import get_audio_ensemble
    except ImportError:
        raise SystemExit(
            "The legacy model-stage branches this script measures were removed in P1. "
            "Run it from commit 4daed3f, where paper_results/audio_heuristics_dev/ was produced."
        ) from None

    get_audio_ensemble()  # build the seeded ensemble before any scoring

    scores_path = out / "scores.csv"
    done: set[str] = set()
    if scores_path.is_file():
        with open(scores_path, newline="", encoding="utf-8") as handle:
            done = {r["utt_id"] for r in csv.DictReader(handle)}
    todo = [r for r in subsample if r["utt_id"] not in done][: args.limit]
    print(f"{len(done):,} already recorded, {len(todo):,} to do", flush=True)
    new_file = not scores_path.is_file()
    t0 = time.perf_counter()
    with open(scores_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        for i, row in enumerate(todo, start=1):
            signals = record_signals(args.asvspoof_root / row["relative_path"])
            writer.writerow({"utt_id": row["utt_id"], "label": row["label"], "attack_id": row["attack_id"], **signals})
            handle.flush()
            if i % 10 == 0 or i == len(todo):
                rate = i / (time.perf_counter() - t0)
                print(f"  {i:,}/{len(todo):,} | {rate:.2f} utt/s | ETA {(len(todo) - i) / rate / 60:.1f} min", flush=True)

    config = {
        "purpose": "Phase 3: legacy audio signals on a balanced ASVspoof 2019 LA dev subsample",
        "n_per_class": args.n_per_class,
        "subsample_seed": args.seed,
        "torch_seed_for_untrained_sincrawnet": args.torch_seed,
        "loading": "app.ml.preprocessing.load_audio at 16 kHz, then normalize_waveform (as analyze_audio)",
        "suite": "app.ml.audio.run_comprehensive_audio_forensics (legacy mode)",
        "subsample_sha256": sha256_file(out / "subsample.csv"),
        "provenance": collect_provenance(args.manifest, seeds=[args.seed, args.torch_seed]),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    elapsed = time.perf_counter() - t0
    if todo:
        per = elapsed / len(todo)
        remaining = len(subsample) - len(done) - len(todo)
        print(f"{per:.2f} s per utterance; {remaining:,} remaining -> about {remaining * per / 60:.0f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
