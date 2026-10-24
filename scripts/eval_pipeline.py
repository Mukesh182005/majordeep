#!/usr/bin/env python3
"""Full-pipeline verdicts on labelled test sets.

Audio, ASVspoof 2019 LA eval (Phase 3 task 7 in docs/paper_upgrade/GOAL.md):

* A stratified random sample of the eval partition with a fixed seed: bona
  fide utterances at random, and the same number from each eval attack
  (A07-A19). The defaults (2,002 bona fide, 154 per attack) give 4,004.
* Every file goes through ``app.ml.pipeline.analyze``, the function the
  worker runs for an upload, with the verdict rule frozen on dev
  (``paper/config/frozen_audio_config.json``, committed in 9b2f17b before any
  end-to-end eval scoring). Nothing is tuned here.
* The trained model runs in strict float32 (TF32 off, deterministic cuDNN).
  The committed per-utterance eval scores of Phase 2 were computed with cuDNN
  TF32 on, so the LCNN probabilities here can differ slightly from them; the
  two are reported separately and never mixed.

Scoring the eval split needs ``--confirm-final-eval``, a clean working tree
and an unchanged frozen config; every start, resume and completion is
appended to ``eval_log.csv``. A finished run is refused a second time unless
``--rescore-reason`` says why. The run resumes after an interruption.

Video (FaceForensics++ c23 test, Celeb-DF v2 test) and In-the-Wild audio are
recorded as not run, with the reason, until their data can be used.

Writes
    paper_results/audio_end_to_end_eval/{sample.csv, scores.csv, config.json,
        eval_log.csv, verdict_rates.json}
    results/pipeline_eval.json, results/figures/audio_pipeline_verdicts.png
    the ``audio_end_to_end_eval`` section of paper_results/INDEX.md

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    $env:DEVICE = "cuda"
    # timing on dev clips, scratch output (no eval file is read)
    python scripts/eval_pipeline.py audio-la --split dev --limit 50 --output-dir $env:TEMP\\ds-timing
    # the eval run, once
    python scripts/eval_pipeline.py audio-la --workers 8 --confirm-final-eval
    # rebuild the summaries from the saved rows only
    python scripts/eval_pipeline.py summarise
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT, REPO_ROOT / "backend"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

OUT_DIR = REPO_ROOT / "paper_results/audio_end_to_end_eval"
RESULTS_FILE = REPO_ROOT / "results/pipeline_eval.json"
FIGURE = REPO_ROOT / "results/figures/audio_pipeline_verdicts.png"
FROZEN_CONFIG = REPO_ROOT / "paper/config/frozen_audio_config.json"
INDEX_SECTION = "audio_end_to_end_eval"

VERDICTS = ("authentic", "inconclusive", "flagged")
VERDICT_NAMES = {"AUTHENTIC": "authentic", "INCONCLUSIVE": "inconclusive", "MANIPULATED": "flagged"}
COLUMNS = [
    "utt_id", "label", "attack_id", "verdict", "fake_probability", "lcnn_probability", "mean_spoof_logit",
    "n_windows", "weights_status", "model_version", "checkpoint_sha256", "seconds", "error",
]
LOG_COLUMNS = ["utc_time", "event", "split", "git_commit", "n_rows", "rescore_reason"]

NOT_RUN = {
    "in_the_wild": (
        "Not run: the In-the-Wild licence is unresolved (Apache 2.0 on one page, CC BY-SA 4.0 on another); "
        "ml/preprocessing/build_in_the_wild.py refuses to run without --licence-confirmed."
    ),
    "faceforensics_c23_test": "Not run: FaceForensics++ (c23) is not on this machine (access not yet granted).",
    "celeb_df_v2_test": "Not run: Celeb-DF v2 is not on this machine (access not yet granted).",
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _sha256(path: Path) -> str:
    from ml.provenance import sha256_file

    return sha256_file(path)


# --------------------------------------------------------------------------- sample


def stratified_sample(rows: list[dict], split: str, n_bonafide: int, n_per_attack: int, seed: int) -> list[dict]:
    """Bona fide rows at random plus ``n_per_attack`` rows of every attack in ``split``.

    Rows are sorted by ``utt_id`` first, so the draw depends only on the
    manifest's content and the seed, not on its row order.
    """
    rng = np.random.default_rng(seed)
    pool = sorted((r for r in rows if r["split"] == split), key=lambda r: r["utt_id"])
    bona = [r for r in pool if int(r["label"]) == 0]
    if len(bona) < n_bonafide:
        raise ValueError(f"only {len(bona)} bona fide {split} utterances, {n_bonafide} requested")
    chosen = [bona[i] for i in sorted(rng.choice(len(bona), n_bonafide, replace=False))]
    for attack in sorted({r["attack_id"] for r in pool if int(r["label"]) == 1}):
        spoofs = [r for r in pool if int(r["label"]) == 1 and r["attack_id"] == attack]
        if len(spoofs) < n_per_attack:
            raise ValueError(f"only {len(spoofs)} {split} utterances of {attack}, {n_per_attack} requested")
        chosen += [spoofs[i] for i in sorted(rng.choice(len(spoofs), n_per_attack, replace=False))]
    return chosen


def write_sample(path: Path, sample: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "label", "attack_id", "relative_path"])
        writer.writerows([r["utt_id"], int(r["label"]), r["attack_id"], r["relative_path"]] for r in sample)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- scoring


def score_file(task: tuple[str, str]) -> dict:
    """Run one file through the worker's pipeline; never raises."""
    from app.ml.pipeline import analyze
    from app.models import MediaType

    utt_id, path = task
    t0 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="ds-e2e-") as evidence_dir:
            result = analyze(MediaType.AUDIO, Path(path), evidence_dir, utt_id)
        lcnn = (result.evidence.get("models_output") or {}).get("lcnn_asvspoof") or {}
        return {
            "utt_id": utt_id,
            "verdict": VERDICT_NAMES[str(result.verdict)],
            "fake_probability": result.fake_probability,
            "lcnn_probability": lcnn.get("probability"),
            "mean_spoof_logit": lcnn.get("mean_spoof_logit"),
            "n_windows": lcnn.get("n_windows"),
            "weights_status": result.weights_status,
            "model_version": result.model_version,
            "checkpoint_sha256": lcnn.get("checkpoint_sha256"),
            "seconds": round(time.perf_counter() - t0, 3),
            "error": "",
        }
    except Exception as exc:  # recorded, never dropped
        return {"utt_id": utt_id, "seconds": round(time.perf_counter() - t0, 3),
                "error": f"{type(exc).__name__}: {exc}"[:500]}


def _init_worker(threads: int) -> None:
    try:
        import torch

        torch.set_num_threads(threads)
    except ImportError:
        pass


def done_ids(scores_path: Path) -> set[str]:
    return {r["utt_id"] for r in read_csv(scores_path)} if scores_path.is_file() else set()


def run_scoring(
    todo: list[dict],
    root: Path,
    scores_path: Path,
    workers: int,
    threads: int,
    scorer: Callable[[tuple[str, str]], dict] = score_file,
) -> int:
    """Score ``todo`` and append one row per file to ``scores_path``; returns the count."""
    by_id = {r["utt_id"]: r for r in todo}
    tasks = [(r["utt_id"], str(root / r["relative_path"])) for r in todo]
    new_file = not scores_path.is_file()
    t0 = time.perf_counter()
    written = 0
    with open(scores_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()

        def emit(record: dict) -> None:
            nonlocal written
            source = by_id[record["utt_id"]]
            writer.writerow({**{c: "" for c in COLUMNS}, **record,
                             "label": int(source["label"]), "attack_id": source["attack_id"]})
            handle.flush()
            written += 1
            if written % 25 == 0 or written == len(tasks):
                rate = written / (time.perf_counter() - t0)
                print(f"  {written:,}/{len(tasks):,} | {rate:.2f} files/s | "
                      f"ETA {(len(tasks) - written) / rate / 60:.1f} min", flush=True)

        if workers <= 1:
            for task in tasks:
                emit(scorer(task))
        else:
            with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(threads,)) as pool:
                for future in as_completed([pool.submit(scorer, task) for task in tasks]):
                    emit(future.result())
    return written


# --------------------------------------------------------------------------- eval gate


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False).stdout.strip()


def gate_problems(split: str, confirm: bool, official: bool, git_status: str, frozen_diff: str,
                  frozen_tracked: bool) -> list[str]:
    """Reasons the run must not start (empty = may start)."""
    problems = []
    if split == "eval" and not confirm:
        problems.append("Scoring the eval split is the final test: pass --confirm-final-eval.")
    if split == "eval":
        if not frozen_tracked:
            problems.append(f"{_rel(FROZEN_CONFIG)} is not committed; the rule must be frozen before eval scoring.")
        if frozen_diff:
            problems.append(f"{_rel(FROZEN_CONFIG)} differs from the committed version.")
    if official and git_status:
        problems.append("The working tree is not clean; commit first so the scored code is recorded exactly.")
    return problems


def read_log(path: Path) -> list[dict]:
    return read_csv(path) if path.is_file() else []


def append_log(path: Path, event: str, split: str, commit: str, n_rows: int, reason: str = "") -> None:
    new_file = not path.is_file()
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({"utc_time": datetime.now(UTC).isoformat(timespec="seconds"), "event": event,
                         "split": split, "git_commit": commit, "n_rows": n_rows, "rescore_reason": reason})


# --------------------------------------------------------------------------- summary


def _rate(k: int, n: int) -> dict:
    from ml.evaluation.stats import wilson_interval

    low, high = wilson_interval(k, n)
    return {"k": k, "n": n, "rate": k / n if n else None, "ci95": [low, high]}


def group_rates(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    scored = [r for r in rows if not r.get("error")]
    out: dict = {"n": len(rows), "errors": len(rows) - len(scored)}
    for verdict in VERDICTS:
        out[verdict] = _rate(sum(1 for r in scored if r["verdict"] == verdict), len(scored))
    return out


def verdict_rates(rows: list[dict], n_resamples: int = 2000, seed: int = 0) -> dict:
    """Verdict rates with Wilson intervals per class and per attack, and the AUC of the final probability."""
    from ml.evaluation.stats import bootstrap_auc_ci

    bona = [r for r in rows if int(r["label"]) == 0]
    spoof = [r for r in rows if int(r["label"]) == 1]
    scored = [r for r in rows if not r.get("error")]
    labels = np.array([int(r["label"]) for r in scored])
    summary: dict = {
        "classes": {"bonafide": group_rates(bona), "spoof": group_rates(spoof)},
        "per_attack": {a: group_rates(r for r in spoof if r["attack_id"] == a)
                       for a in sorted({r["attack_id"] for r in spoof})},
    }
    if labels.size and 0 < labels.sum() < labels.size:
        # fake_probability is what the API returns, rounded to 4 decimals, so many
        # utterances tie at 0 or 1; the unrounded LCNN probability ranks them all.
        probs = np.array([float(r["fake_probability"]) for r in scored])
        summary["auc_fake_probability"] = bootstrap_auc_ci(labels, probs, n_resamples=n_resamples, seed=seed)
        summary["fake_probability_ties"] = {"at_0": int((probs == 0).sum()), "at_1": int((probs == 1).sum()),
                                            "distinct_values": int(np.unique(probs).size)}
        if all(r.get("lcnn_probability") not in (None, "") for r in scored):
            lcnn = np.array([float(r["lcnn_probability"]) for r in scored])
            summary["auc_lcnn_probability_unrounded"] = bootstrap_auc_ci(labels, lcnn, n_resamples=n_resamples,
                                                                         seed=seed)
    return summary


def _pct(entry: dict) -> str:
    low, high = entry["ci95"]
    return f"{entry['rate'] * 100:.1f}% [{low * 100:.1f}, {high * 100:.1f}] ({entry['k']:,}/{entry['n']:,})"


def index_rows(summary: dict, file: str) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for cls, name in (("bonafide", "bona fide"), ("spoof", "spoofed")):
        entry = summary["classes"][cls]
        for verdict in VERDICTS:
            rows.append((f"Audio LA eval end to end, {name}: {verdict} (n={entry['n']:,})", _pct(entry[verdict]),
                         file, f"classes.{cls}.{verdict}.rate", "3"))
    for attack, entry in summary["per_attack"].items():
        rows.append((f"Audio LA eval end to end, {attack}: flagged", _pct(entry["flagged"]), file,
                     f"per_attack.{attack}.flagged.rate", "3"))
    for key, item in (("auc_fake_probability", "AUC of the API probability (rounded to 4 decimals)"),
                      ("auc_lcnn_probability_unrounded", "AUC of the unrounded LCNN probability")):
        auc = summary.get(key)
        if auc:
            rows.append((f"Audio LA eval end to end: {item}",
                         f"{auc['auc']:.4f} [{auc['ci95'][0]:.4f}, {auc['ci95'][1]:.4f}]", file,
                         f"{key}.auc, .ci95", "3"))
    return rows


def plot_verdicts(summary: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted = "#fcfcfb", "#0b0b0b", "#52514e"
    colours = {"authentic": "#2a78d6", "inconclusive": "#1baf7a", "flagged": "#eb6834"}
    groups = [("Bona fide", summary["classes"]["bonafide"]), ("Spoofed (all)", summary["classes"]["spoof"])]
    groups += [(attack, entry) for attack, entry in summary["per_attack"].items()]
    fig, ax = plt.subplots(figsize=(7.5, 0.34 * len(groups) + 1.4), facecolor=surface)
    ax.set_facecolor(surface)
    for y, (name, entry) in enumerate(groups):
        left = 0.0
        for verdict in VERDICTS:
            share = entry[verdict]["rate"] or 0.0
            ax.barh(y, share * 100, left=left * 100, height=0.72, color=colours[verdict],
                    edgecolor=surface, linewidth=2, label=verdict if y == 0 else None)
            if share >= 0.08:
                ax.text((left + share / 2) * 100, y, f"{share * 100:.1f}", ha="center", va="center",
                        fontsize=7.5, color="white")
            left += share
    ax.set_yticks(range(len(groups)), [name for name, _ in groups], fontsize=8.5, color=ink)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of utterances (%)", fontsize=8.5, color=muted)
    ax.tick_params(axis="x", labelsize=8, colors=muted)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#d6d5d0")
    ax.tick_params(axis="y", length=0)
    ax.set_title("End-to-end audio verdicts, ASVspoof 2019 LA eval sample (frozen dev rule)",
                 fontsize=9.5, color=ink, loc="left")
    ax.legend(ncol=3, frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.08 - 1.2 / len(groups)),
              labelcolor=ink)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


PHASE2_EVAL_SCORES = REPO_ROOT / "paper_results/audio_asvspoof2019la/eval/audio_lcnn_asvspoof_lfcc_seed2_eval_scores.csv"


def tf32_comparison(scores: list[dict], phase2: Path = PHASE2_EVAL_SCORES) -> dict | None:
    """The strict-float32 mean logits here against the Phase 2 eval scores (cuDNN TF32 on), same utterances.

    Reported side by side so the two are never mixed silently; nothing is re-scored.
    """
    from ml.evaluation.metrics import roc_auc

    if not phase2.is_file():
        return None
    stored = {r["utt_id"]: float(r["score"]) for r in read_csv(phase2)}
    rows = [r for r in scores if not r.get("error") and r["utt_id"] in stored and r.get("mean_spoof_logit")]
    if not rows:
        return None
    labels = np.array([int(r["label"]) for r in rows])
    float32 = np.array([float(r["mean_spoof_logit"]) for r in rows])
    tf32 = np.array([-stored[r["utt_id"]] for r in rows])  # stored score = -mean spoof logit
    return {
        "phase2_scores_file": _rel(phase2), "n": len(rows),
        "max_abs_mean_logit_difference": float(np.max(np.abs(float32 - tf32))),
        "auc_float32_mean_logit": float(roc_auc(labels, float32)),
        "auc_tf32_mean_logit": float(roc_auc(labels, tf32)),
    }


def summarise(out_dir: Path = OUT_DIR, results_file: Path = RESULTS_FILE, figure: Path = FIGURE,
              index: Path | None = None) -> dict:
    """Write verdict_rates.json, results/pipeline_eval.json, the figure and INDEX rows from saved files only."""
    from ml.provenance import collect_provenance
    from paper.analysis.index_tools import INDEX, update_index_section

    audio: dict = {"in_the_wild": {"status": "not_run", "reason": NOT_RUN["in_the_wild"]}}
    scores_path, sample_path = out_dir / "scores.csv", out_dir / "sample.csv"
    if scores_path.is_file() and sample_path.is_file():
        sample, scores = read_csv(sample_path), read_csv(scores_path)
        config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
        ids = [r["utt_id"] for r in scores]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"{_rel(scores_path)} scores some utterances twice.")
        missing = {r["utt_id"] for r in sample} - set(ids)
        if missing:
            raise SystemExit(f"{len(missing):,} sampled utterances are not scored yet; finish the run first.")
        order = {r["utt_id"]: i for i, r in enumerate(sample)}
        scores.sort(key=lambda r: order[r["utt_id"]])
        checkpoints = {r["checkpoint_sha256"] for r in scores if not r["error"]}
        summary = {
            "purpose": "Phase 3 task 7: end-to-end verdicts on a stratified ASVspoof 2019 LA eval sample, "
                       "frozen dev rule",
            "rule": config["rule"],
            "sample": config["sample"],
            "inference": config["inference"],
            "checkpoint_sha256": sorted(checkpoints),
            "scores_file": _rel(scores_path),
            "scores_sha256": _sha256(scores_path),
            **verdict_rates(scores),
        }
        comparison = tf32_comparison(scores)
        if comparison:
            summary["tf32_comparison"] = comparison
        rates_path = out_dir / "verdict_rates.json"
        rates_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        plot_verdicts(summary, figure)
        update_index_section(INDEX_SECTION, index_rows(summary, _rel(rates_path)), index or INDEX)
        audio["asvspoof2019_la_eval"] = {"status": "done", "source": _rel(rates_path), "figure": _rel(figure),
                                         **{k: summary[k] for k in ("sample", "rule", "inference", "classes",
                                                                    "per_attack", "auc_fake_probability",
                                                                    "fake_probability_ties",
                                                                    "auc_lcnn_probability_unrounded",
                                                                    "tf32_comparison")
                                            if k in summary}}
    else:
        audio["asvspoof2019_la_eval"] = {"status": "not_run",
                                         "reason": f"No saved scores in {_rel(out_dir)}; run `audio-la` first."}
    payload = {
        "audio": audio,
        "video": {key: {"status": "not_run", "reason": NOT_RUN[key]}
                  for key in ("faceforensics_c23_test", "celeb_df_v2_test")},
        "provenance": collect_provenance(None),
    }
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {_rel(results_file)}")
    return payload


# --------------------------------------------------------------------------- commands


def cmd_audio_la(args: argparse.Namespace) -> int:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root, read_manifest
    from ml.provenance import collect_provenance

    root = args.asvspoof_root or default_la_root()
    if root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")
    out = args.output_dir
    official = out.resolve() == OUT_DIR.resolve()
    problems = gate_problems(
        args.split, args.confirm_final_eval, official,
        git_status=_git("status", "--porcelain"),
        frozen_diff=_git("diff", "HEAD", "--", _rel(FROZEN_CONFIG)),
        frozen_tracked=bool(_git("ls-files", "--", _rel(FROZEN_CONFIG))),
    )
    if problems:
        raise SystemExit("\n".join(problems))
    # Before any output exists, so the dirty-tree flag describes the code alone.
    provenance = collect_provenance(args.manifest, seeds=[args.seed])

    log_path = out / "eval_log.csv"
    log = read_log(log_path)
    if any(r["event"] == "complete" for r in log) and not args.rescore_reason:
        raise SystemExit(f"{_rel(out)} already holds a completed run; pass --rescore-reason to score again.")

    sample = stratified_sample(read_manifest(args.manifest), args.split, args.bonafide, args.per_attack, args.seed)
    out.mkdir(parents=True, exist_ok=True)
    scores_path = out / "scores.csv"
    commit = _git("rev-parse", "HEAD")
    if scores_path.is_file():
        previous = json.loads((out / "config.json").read_text(encoding="utf-8"))
        if previous["provenance"].get("git_commit") != commit:
            raise SystemExit(f"{_rel(scores_path)} was started at another commit; move it aside to start again.")
        if previous["sample"]["seed"] != args.seed or previous["sample"]["size"] != len(sample):
            raise SystemExit(f"{_rel(scores_path)} was started with another sample; move it aside to start again.")
    write_sample(out / "sample.csv", sample)

    from app.config import settings

    frozen = json.loads(FROZEN_CONFIG.read_text(encoding="utf-8"))
    done = done_ids(scores_path)
    todo = [r for r in sample if r["utt_id"] not in done][: args.limit]
    if not scores_path.is_file():
        attacks = sorted({r["attack_id"] for r in sample if int(r["label"]) == 1})
        config = {
            "purpose": "Phase 3 task 7: end-to-end verdicts on a stratified ASVspoof 2019 LA sample",
            "sample": {"split": args.split, "seed": args.seed, "size": len(sample), "bonafide": args.bonafide,
                       "per_attack": args.per_attack, "attacks": attacks,
                       "sample_sha256": _sha256(out / "sample.csv")},
            "rule": {"file": _rel(FROZEN_CONFIG), "sha256": _sha256(FROZEN_CONFIG),
                     "authentic_below": frozen["authentic_below"],
                     "flagged_at_or_above": frozen["flagged_at_or_above"],
                     "decision_rule": frozen["decision_rule"]},
            "pipeline": "app.ml.pipeline.analyze(MediaType.AUDIO, ...), the worker's function for an upload",
            "settings": {"audio_model_source": settings.audio_model_source, "device": settings.device,
                         "max_audio_seconds": settings.max_audio_seconds,
                         "calibration_file": _rel(Path(settings.audio_lcnn_calibration_file)),
                         "calibration_sha256": _sha256(Path(settings.audio_lcnn_calibration_file))},
            "inference": "LCNN in strict float32 (TF32 off, deterministic cuDNN); the Phase 2 eval_scores.csv "
                         "were computed with cuDNN TF32 on, so LCNN probabilities may differ slightly from them",
            "workers": args.workers, "threads_per_worker": args.threads,
            "provenance": provenance,
        }
        (out / "config.json").write_text(json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"{len(sample):,} sampled ({args.split}), {len(done):,} already scored, {len(todo):,} to do", flush=True)
    append_log(log_path, "resume" if done else "start", args.split, commit, len(done), args.rescore_reason or "")

    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(name, str(args.threads))
    t0 = time.perf_counter()
    written = run_scoring(todo, root, scores_path, args.workers, args.threads)
    elapsed = time.perf_counter() - t0
    if written:
        print(f"{written:,} scored in {elapsed / 60:.1f} min ({elapsed / written:.2f} s per file wall clock)")

    remaining = len(sample) - len(done_ids(scores_path))
    if remaining:
        print(f"{remaining:,} still to score; run the same command again to continue.")
        return 0
    append_log(log_path, "complete", args.split, commit, len(sample), args.rescore_reason or "")
    if official:
        summarise(out)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    audio = sub.add_parser("audio-la", help="score the ASVspoof 2019 LA sample end to end")
    audio.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    audio.add_argument("--asvspoof-root", type=Path, default=None)
    audio.add_argument("--split", choices=("eval", "dev"), default="eval")
    audio.add_argument("--bonafide", type=int, default=2002)
    audio.add_argument("--per-attack", type=int, default=154)
    audio.add_argument("--seed", type=int, default=0)
    audio.add_argument("--workers", type=int, default=8)
    audio.add_argument("--threads", type=int, default=4, help="CPU threads per worker")
    audio.add_argument("--limit", type=int, default=None, help="score at most N new files (timing)")
    audio.add_argument("--output-dir", type=Path, default=OUT_DIR)
    audio.add_argument("--confirm-final-eval", action="store_true")
    audio.add_argument("--rescore-reason", default="")
    sub.add_parser("summarise", help="rebuild the summaries from the saved rows only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "audio-la":
        return cmd_audio_la(args)
    summarise()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
