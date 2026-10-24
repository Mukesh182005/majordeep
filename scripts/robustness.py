#!/usr/bin/env python3
"""Robustness of the detectors to re-encoding.

Audio (``audio``): the utterances of the end-to-end LA eval sample
(``paper_results/audio_end_to_end_eval/sample.csv``), each scored by the served
ASVspoof LCNN as the application loads an upload (``load_audio`` at 16 kHz,
then ``score_lcnn_asvspoof``), in three conditions fixed before scoring:

* ``original``: the FLAC file as distributed;
* ``mp3_64k``: MP3 at 64 kbit/s (libmp3lame);
* ``opus_32k``: Opus at 32 kbit/s in Ogg (libopus).

Both codecs use the ffmpeg build bundled with imageio-ffmpeg. Per condition:
EER, AUC with a bootstrap interval, the DeLong test against ``original`` on
the same utterances, per-attack EER, and the verdict rates the frozen dev rule
(``paper/config/frozen_audio_config.json``) gives the LCNN probability. The
model runs in strict float32. Scoring the eval split needs
``--confirm-final-eval`` and a clean working tree, and is logged; nothing is
tuned on it.

Image (``image-transforms``): writes transformed copies of an image manifest
(JPEG quality 95/75/50/30, 0.5x resize, and a WhatsApp-style recompression:
longest side at most 1,600 px, JPEG quality 70) and their manifest, for
``ml/evaluation/eval_image_detectors.py``. There is no image test set on this
machine yet (H560 missing, T2 not built, image configuration not frozen), so
``results/robustness.json`` records the image part as not run until per-image
scores exist in ``paper_results/image_robustness/scores.jsonl``.

Writes
    paper_results/audio_codec_robustness/{scores.csv, config.json, eval_log.csv, metrics.json}
    results/robustness.json, results/figures/audio_codec_robustness.png
    the ``audio_codec_robustness`` section of paper_results/INDEX.md

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python scripts/robustness.py audio --workers 12 --confirm-final-eval
    python scripts/robustness.py image-transforms --manifest paper/manifests/t2.csv `
        --image-root $env:DEEPSENTINEL_DATA\\T2 --out-root $env:DEEPSENTINEL_DATA\\T2_robustness `
        --manifest-out paper/manifests/t2_robustness.csv
    python scripts/robustness.py summarise
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_pipeline as ep  # noqa: E402  (also puts the repository and backend/ on sys.path)

REPO_ROOT = ep.REPO_ROOT
OUT_DIR = REPO_ROOT / "paper_results/audio_codec_robustness"
SAMPLE = ep.OUT_DIR / "sample.csv"
IMAGE_SCORES = REPO_ROOT / "paper_results/image_robustness/scores.jsonl"
RESULTS_FILE = REPO_ROOT / "results/robustness.json"
FIGURE = REPO_ROOT / "results/figures/audio_codec_robustness.png"
INDEX_SECTION = "audio_codec_robustness"

AUDIO_CODECS = {
    "mp3_64k": {"suffix": ".mp3", "args": ["-c:a", "libmp3lame", "-b:a", "64k"]},
    "opus_32k": {"suffix": ".ogg", "args": ["-c:a", "libopus", "-b:a", "32k"]},
}
CONDITIONS = ("original", *AUDIO_CODECS)
COLUMNS = ["utt_id", "label", "attack_id", "condition", "probability", "cm_score", "n_windows", "error"]

IMAGE_CONDITIONS = ("jpeg95", "jpeg75", "jpeg50", "jpeg30", "resize50", "whatsapp")
WHATSAPP_MAX_SIDE, WHATSAPP_QUALITY = 1600, 70
IMAGE_NOT_RUN = (
    "Not run: no image test set is on this machine. H560 was not found (docs/paper_upgrade/STATUS.md), T2 is "
    "not built and the image configuration is not frozen (paper/config/freeze_image_config.py has not been run)."
)


# --------------------------------------------------------------------------- audio


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def encode(source: Path, condition: str, workdir: Path, exe: str) -> Path:
    codec = AUDIO_CODECS[condition]
    target = workdir / f"{source.stem}_{condition}{codec['suffix']}"
    subprocess.run([exe, "-nostdin", "-v", "error", "-y", "-i", str(source), *codec["args"], str(target)],
                   check=True, capture_output=True, timeout=120)
    return target


def score_audio_file(path: Path) -> dict:
    from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
    from app.ml.preprocessing import load_audio

    waveform, rate = load_audio(path, 16000)
    scored = score_lcnn_asvspoof(waveform, rate)
    return {"probability": scored["probability"], "cm_score": scored["cm_score"], "n_windows": scored["n_windows"]}


def score_conditions(task: tuple[str, str]) -> list[dict]:
    """Every condition of one utterance; errors are recorded, never raised."""
    utt_id, source = task
    exe = ffmpeg_exe()
    rows = []
    with tempfile.TemporaryDirectory(prefix="ds-codec-") as tmp:
        for condition in CONDITIONS:
            try:
                path = Path(source) if condition == "original" else encode(Path(source), condition, Path(tmp), exe)
                rows.append({"utt_id": utt_id, "condition": condition, **score_audio_file(path), "error": ""})
            except Exception as exc:
                rows.append({"utt_id": utt_id, "condition": condition, "error": f"{type(exc).__name__}: {exc}"[:500]})
    return rows


def run_audio(todo: list[dict], root: Path, scores_path: Path, workers: int, threads: int, scorer=score_conditions) -> int:
    by_id = {r["utt_id"]: r for r in todo}
    tasks = [(r["utt_id"], str(root / r["relative_path"])) for r in todo]
    new_file = not scores_path.is_file()
    t0, written = time.perf_counter(), 0
    with open(scores_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()

        def emit(rows: list[dict]) -> None:
            nonlocal written
            for row in rows:
                source = by_id[row["utt_id"]]
                writer.writerow({**{c: "" for c in COLUMNS}, **row, "label": int(source["label"]),
                                 "attack_id": source["attack_id"]})
            handle.flush()
            written += 1
            if written % 50 == 0 or written == len(tasks):
                rate = written / (time.perf_counter() - t0)
                print(f"  {written:,}/{len(tasks):,} | {rate:.2f} utt/s | "
                      f"ETA {(len(tasks) - written) / rate / 60:.1f} min", flush=True)

        if workers <= 1:
            for task in tasks:
                emit(scorer(task))
        else:
            with ProcessPoolExecutor(max_workers=workers, initializer=ep._init_worker, initargs=(threads,)) as pool:
                for future in as_completed([pool.submit(scorer, task) for task in tasks]):
                    emit(future.result())
    return written


def frozen_verdict(probability: float, rule: dict) -> str:
    """The frozen dev rule, as app/ml/audio/evidence_fusion.py applies it."""
    if probability >= float(rule["flagged_at_or_above"]):
        return "flagged"
    if probability < float(rule["authentic_below"]):
        return "authentic"
    return "inconclusive"


def condition_metrics(rows: list[dict], rule: dict, n_resamples: int = 2000, seed: int = 0) -> dict:
    """EER, AUC with interval, per-attack EER and frozen-rule verdict rates of one condition."""
    from ml.evaluation.asvspoof_metrics import eer
    from ml.evaluation.stats import bootstrap_auc_ci

    scored = [r for r in rows if not r.get("error")]
    labels = np.array([int(r["label"]) for r in scored])
    cm = np.array([float(r["cm_score"]) for r in scored])
    probs = np.array([float(r["probability"]) for r in scored])
    value, threshold = eer(cm[labels == 0], cm[labels == 1])
    per_attack = {}
    for attack in sorted({r["attack_id"] for r in scored if int(r["label"]) == 1}):
        mask = np.array([r["attack_id"] == attack for r in scored])
        per_attack[attack] = float(eer(cm[labels == 0], cm[mask])[0])
    verdicts = {}
    for cls, label in (("bonafide", 0), ("spoof", 1)):
        group = [frozen_verdict(float(r["probability"]), rule) for r in scored if int(r["label"]) == label]
        verdicts[cls] = {v: ep._rate(sum(g == v for g in group), len(group)) for v in ep.VERDICTS}
    return {
        "n": len(rows), "errors": len(rows) - len(scored),
        "eer": float(value), "eer_threshold_cm_score": float(threshold),
        "auc": bootstrap_auc_ci(labels, probs, n_resamples=n_resamples, seed=seed),
        "per_attack_eer": per_attack,
        "frozen_rule_verdicts": verdicts,
    }


def audio_metrics(rows: list[dict], rule: dict, n_resamples: int = 2000, seed: int = 0) -> dict:
    from ml.evaluation.stats import delong_test

    by_condition = {c: [r for r in rows if r["condition"] == c] for c in CONDITIONS}
    result: dict = {"conditions": {c: condition_metrics(by_condition[c], rule, n_resamples, seed)
                                   for c in CONDITIONS if by_condition[c]}}
    reference = {r["utt_id"]: r for r in by_condition["original"] if not r.get("error")}
    result["delong_vs_original"] = {}
    for condition in AUDIO_CODECS:
        pairs = [(reference[r["utt_id"]], r) for r in by_condition[condition]
                 if not r.get("error") and r["utt_id"] in reference]
        if not pairs:
            continue
        labels = np.array([int(a["label"]) for a, _ in pairs])
        a = np.array([float(x["probability"]) for x, _ in pairs])
        b = np.array([float(y["probability"]) for _, y in pairs])
        result["delong_vs_original"][condition] = {"n": len(pairs), **delong_test(labels, a, b)}
    return result


def end_to_end_agreement(rows: list[dict]) -> dict | None:
    """Largest difference between the ``original`` LCNN probabilities and the end-to-end run's, if it exists."""
    e2e_path = ep.OUT_DIR / "scores.csv"
    if not e2e_path.is_file():
        return None
    e2e = {r["utt_id"]: r for r in ep.read_csv(e2e_path) if not r["error"]}
    diffs = [abs(float(r["probability"]) - float(e2e[r["utt_id"]]["lcnn_probability"]))
             for r in rows if r["condition"] == "original" and not r["error"] and r["utt_id"] in e2e]
    return {"n": len(diffs), "max_abs_difference": max(diffs) if diffs else None,
            "file": ep._rel(e2e_path)} if diffs else None


def plot_audio(metrics: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted, mark = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"
    names = {"original": "Original (FLAC)", "mp3_64k": "MP3 64 kbit/s", "opus_32k": "Opus 32 kbit/s"}
    conditions = [c for c in CONDITIONS if c in metrics["conditions"]]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 0.55 * len(conditions) + 1.3), facecolor=surface)
    for ax in axes:
        ax.set_facecolor(surface)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#d6d5d0")
        ax.tick_params(axis="y", length=0, labelsize=8.5, colors=ink)
        ax.tick_params(axis="x", labelsize=8, colors=muted)
    ys = range(len(conditions))
    eers = [metrics["conditions"][c]["eer"] * 100 for c in conditions]
    axes[0].barh(list(ys), eers, height=0.55, color=mark, edgecolor=surface, linewidth=2)
    for y, value in zip(ys, eers):
        axes[0].text(value, y, f" {value:.2f}", va="center", fontsize=8, color=ink)
    axes[0].set_yticks(list(ys), [names[c] for c in conditions])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("EER (%)", fontsize=8.5, color=muted)
    axes[0].set_xlim(0, max(eers) * 1.25 + 0.5)
    for y, condition in zip(ys, conditions):
        auc = metrics["conditions"][condition]["auc"]
        axes[1].plot(auc["ci95"], [y, y], color=mark, linewidth=2, solid_capstyle="round")
        axes[1].plot([auc["auc"]], [y], "o", color=mark, markersize=8, markeredgecolor=surface, markeredgewidth=2)
        axes[1].text(auc["ci95"][1], y, f"  {auc['auc']:.4f}", va="center", fontsize=8, color=ink)
    axes[1].set_yticks(list(ys), [""] * len(conditions))
    axes[1].invert_yaxis()
    axes[1].set_xlabel("AUC (95% bootstrap interval)", fontsize=8.5, color=muted)
    low = min(metrics["conditions"][c]["auc"]["ci95"][0] for c in conditions)
    axes[1].set_xlim(max(0.0, low - 0.02), 1.004)
    fig.suptitle("Served audio model under re-encoding, ASVspoof 2019 LA eval sample", fontsize=9.5, color=ink,
                 x=0.02, ha="left")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


def index_rows(metrics: dict, file: str) -> list[tuple[str, str, str, str, str]]:
    names = {"original": "original FLAC", "mp3_64k": "MP3 64 kbit/s", "opus_32k": "Opus 32 kbit/s"}
    rows = []
    for condition, entry in metrics["conditions"].items():
        auc = entry["auc"]
        rows.append((f"Audio LA eval sample, {names[condition]}: EER (%)", f"{entry['eer'] * 100:.2f}", file,
                     f"conditions.{condition}.eer", "6"))
        rows.append((f"Audio LA eval sample, {names[condition]}: AUC",
                     f"{auc['auc']:.4f} [{auc['ci95'][0]:.4f}, {auc['ci95'][1]:.4f}]", file,
                     f"conditions.{condition}.auc.auc, .ci95", "6"))
        verdicts = entry["frozen_rule_verdicts"]
        for cls, verdict, name in (("bonafide", "authentic", "bona fide called authentic"),
                                   ("spoof", "flagged", "spoofed flagged")):
            rows.append((f"Audio LA eval sample, {names[condition]}: {name} (frozen rule)",
                         ep._pct(verdicts[cls][verdict]), file,
                         f"conditions.{condition}.frozen_rule_verdicts.{cls}.{verdict}.rate", "6"))
    for condition, test in metrics.get("delong_vs_original", {}).items():
        rows.append((f"Audio LA eval sample, DeLong {names[condition]} vs original: p", f"{test['p_value']:.3g}",
                     file, f"delong_vs_original.{condition}.p_value", "6"))
    return rows


# --------------------------------------------------------------------------- image


def transform_image(image, condition: str):
    """(transformed RGB image, JPEG quality or None) for one robustness condition."""
    from PIL import Image

    image = image.convert("RGB")
    if condition.startswith("jpeg"):
        return image, int(condition[4:])
    if condition == "resize50":
        size = (max(1, round(image.width * 0.5)), max(1, round(image.height * 0.5)))
        return image.resize(size, Image.Resampling.LANCZOS), None
    if condition == "whatsapp":
        scale = min(1.0, WHATSAPP_MAX_SIDE / max(image.size))
        if scale < 1.0:
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
        return image, WHATSAPP_QUALITY
    raise ValueError(f"unknown image condition: {condition}")


def make_image_copies(rows: list[dict], image_root: Path, out_root: Path,
                      conditions: tuple[str, ...] = IMAGE_CONDITIONS) -> list[dict]:
    """Write every condition of every original row; returns the new manifest rows (originals first)."""
    from PIL import Image

    manifest = []
    for row in rows:
        if row.get("condition", "original") != "original":
            continue
        group = row.get("group") or row["image_id"]
        manifest.append({**row, "condition": "original", "group": group})
        with Image.open(image_root / row["relative_path"]) as source:
            source.load()
            for condition in conditions:
                image, quality = transform_image(source, condition)
                suffix = ".jpg" if quality else ".png"
                relative = Path(condition) / Path(row["relative_path"]).with_suffix(suffix)
                target = out_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if quality:
                    image.save(target, "JPEG", quality=quality)
                else:
                    image.save(target, "PNG")
                manifest.append({**row, "image_id": f"{row['image_id']}_{condition}", "condition": condition,
                                 "group": group, "relative_path": relative.as_posix()})
    return manifest


def image_summary() -> dict:
    if not IMAGE_SCORES.is_file():
        return {"status": "not_run", "reason": IMAGE_NOT_RUN, "conditions_defined": list(IMAGE_CONDITIONS)}
    from paper.analysis.image_metrics import condition_metrics as image_condition_metrics, load_scores

    records = load_scores(IMAGE_SCORES)
    conditions = sorted({r.get("condition", "original") for r in records})
    return {"status": "done", "source": ep._rel(IMAGE_SCORES),
            "conditions": {c: image_condition_metrics([r for r in records if r.get("condition", "original") == c])
                           for c in conditions}}


# --------------------------------------------------------------------------- summary and commands


def summarise(out_dir: Path = OUT_DIR, results_file: Path = RESULTS_FILE, figure: Path = FIGURE,
              index: Path | None = None) -> dict:
    from ml.provenance import collect_provenance
    from paper.analysis.index_tools import INDEX, update_index_section

    audio: dict
    scores_path = out_dir / "scores.csv"
    if scores_path.is_file():
        config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
        rows = ep.read_csv(scores_path)
        sample_ids = {r["utt_id"] for r in ep.read_csv(out_dir / "sample.csv")}
        seen = {(r["utt_id"], r["condition"]) for r in rows}
        if len(seen) != len(rows):
            raise SystemExit(f"{ep._rel(scores_path)} holds a condition of an utterance twice.")
        if {(u, c) for u in sample_ids for c in CONDITIONS} - seen:
            raise SystemExit("Some utterances are not scored in every condition yet; finish the run first.")
        metrics = {"purpose": "Served audio model under MP3 and Opus re-encoding, ASVspoof 2019 LA eval sample",
                   "sample": config["sample"], "codecs": config["codecs"], "rule": config["rule"],
                   "inference": config["inference"], "scores_file": ep._rel(scores_path),
                   "scores_sha256": ep._sha256(scores_path), **audio_metrics(rows, config["rule"]),
                   "original_vs_end_to_end_run": end_to_end_agreement(rows)}
        metrics_path = out_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        plot_audio(metrics, figure)
        update_index_section(INDEX_SECTION, index_rows(metrics, ep._rel(metrics_path)), index or INDEX)
        audio = {"status": "done", "source": ep._rel(metrics_path), "figure": ep._rel(figure),
                 **{k: metrics[k] for k in ("sample", "codecs", "conditions", "delong_vs_original")}}
    else:
        audio = {"status": "not_run", "reason": f"No saved scores in {ep._rel(out_dir)}; run `audio` first."}
    payload = {"audio": audio, "image": image_summary(), "provenance": collect_provenance(None)}
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {ep._rel(results_file)}")
    return payload


def cmd_audio(args: argparse.Namespace) -> int:
    import os

    from ml.preprocessing.build_asvspoof2019_la import default_la_root
    from ml.provenance import collect_provenance

    root = args.asvspoof_root or default_la_root()
    if root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")
    if not args.sample.is_file():
        raise SystemExit(f"{ep._rel(args.sample)} not found: run scripts/eval_pipeline.py audio-la first.")
    out = args.output_dir
    official = out.resolve() == OUT_DIR.resolve()
    problems = ep.gate_problems("eval", args.confirm_final_eval, official,
                                git_status=ep._git("status", "--porcelain"),
                                frozen_diff=ep._git("diff", "HEAD", "--", ep._rel(ep.FROZEN_CONFIG)),
                                frozen_tracked=bool(ep._git("ls-files", "--", ep._rel(ep.FROZEN_CONFIG))))
    if problems:
        raise SystemExit("\n".join(problems))
    provenance = collect_provenance(args.sample, seeds=None)
    log_path = out / "eval_log.csv"
    if any(r["event"] == "complete" for r in ep.read_log(log_path)) and not args.rescore_reason:
        raise SystemExit(f"{ep._rel(out)} already holds a completed run; pass --rescore-reason to score again.")

    sample = ep.read_csv(args.sample)[: args.limit_sample]
    out.mkdir(parents=True, exist_ok=True)
    scores_path = out / "scores.csv"
    commit = ep._git("rev-parse", "HEAD")
    if scores_path.is_file():
        previous = json.loads((out / "config.json").read_text(encoding="utf-8"))
        if previous["provenance"].get("git_commit") != commit:
            raise SystemExit(f"{ep._rel(scores_path)} was started at another commit; move it aside to start again.")
    ep.write_sample(out / "sample.csv", sample)
    if not scores_path.is_file():
        frozen = json.loads(ep.FROZEN_CONFIG.read_text(encoding="utf-8"))
        version = subprocess.run([ffmpeg_exe(), "-version"], capture_output=True, text=True).stdout.splitlines()[0]
        config = {
            "purpose": "Served audio model under MP3 and Opus re-encoding",
            "sample": {"file": ep._rel(args.sample), "sha256": ep._sha256(args.sample), "size": len(sample)},
            "codecs": {"ffmpeg": version, **{c: " ".join(v["args"]) for c, v in AUDIO_CODECS.items()}},
            "loading": "app.ml.preprocessing.load_audio at 16 kHz (as an upload), then score_lcnn_asvspoof",
            "rule": {"file": ep._rel(ep.FROZEN_CONFIG), "sha256": ep._sha256(ep.FROZEN_CONFIG),
                     "authentic_below": frozen["authentic_below"],
                     "flagged_at_or_above": frozen["flagged_at_or_above"]},
            "inference": "LCNN in strict float32 (TF32 off, deterministic cuDNN)",
            "workers": args.workers, "threads_per_worker": args.threads,
            "provenance": provenance,
        }
        (out / "config.json").write_text(json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8")
    done = {r["utt_id"] for r in ep.read_csv(scores_path)} if scores_path.is_file() else set()
    todo = [r for r in sample if r["utt_id"] not in done]
    print(f"{len(sample):,} utterances x {len(CONDITIONS)} conditions; {len(done):,} done, {len(todo):,} to do",
          flush=True)
    ep.append_log(log_path, "resume" if done else "start", "eval", commit, len(done), args.rescore_reason)
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(name, str(args.threads))
    run_audio(todo, root, scores_path, args.workers, args.threads)
    if {r["utt_id"] for r in ep.read_csv(scores_path)} >= {r["utt_id"] for r in sample}:
        ep.append_log(log_path, "complete", "eval", commit, len(sample), args.rescore_reason)
        if official:
            summarise(out)
    return 0


def cmd_image_transforms(args: argparse.Namespace) -> int:
    from ml.evaluation.eval_image_detectors import MANIFEST_COLUMNS, read_image_manifest

    rows = make_image_copies(read_image_manifest(args.manifest), args.image_root, args.out_root)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest_out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} rows to {args.manifest_out}; score them with ml/evaluation/eval_image_detectors.py "
          f"--image-root <out-root> --output {ep._rel(IMAGE_SCORES)} --end-to-end")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    audio = sub.add_parser("audio", help="score the LA eval sample under each codec")
    audio.add_argument("--sample", type=Path, default=SAMPLE)
    audio.add_argument("--asvspoof-root", type=Path, default=None)
    audio.add_argument("--workers", type=int, default=12)
    audio.add_argument("--threads", type=int, default=2)
    audio.add_argument("--limit-sample", type=int, default=None, help="first N utterances only (timing)")
    audio.add_argument("--output-dir", type=Path, default=OUT_DIR)
    audio.add_argument("--confirm-final-eval", action="store_true")
    audio.add_argument("--rescore-reason", default="")
    image = sub.add_parser("image-transforms", help="write transformed copies of an image manifest")
    image.add_argument("--manifest", type=Path, required=True)
    image.add_argument("--image-root", type=Path, required=True)
    image.add_argument("--out-root", type=Path, required=True)
    image.add_argument("--manifest-out", type=Path, required=True)
    sub.add_parser("summarise", help="rebuild the summaries from the saved rows only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "audio":
        return cmd_audio(args)
    if args.command == "image-transforms":
        return cmd_image_transforms(args)
    summarise()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
