#!/usr/bin/env python3
"""Codec robustness of audio checkpoints on ASVspoof 2019 LA **dev** (paper/config/audio_codec_plan.json).

The balanced dev subsample of Phase 3 (1,000 bona fide, 1,000 spoofed;
``paper_results/audio_heuristics_dev/subsample.csv``) in every condition of
``ml/preprocessing/audio_codecs.py`` plus the file as distributed, scored by
each checkpoint given: LFCC of every 4 s window (``utterance_lfcc``, as
served), strict float32 on the CPU, mean window spoof logit. Dev data only.

``score`` appends one row per utterance, condition and checkpoint to
``scores.csv`` (resumable). ``summarise`` turns the rows of one checkpoint into
per-condition EER and AUC and, given its calibration and frozen rule, the
verdict rates; the per-family guard of the plan (more than 5 % of bona fide
flagged in any condition of mp3, aac, opus or resample) is computed from them.

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python ml/evaluation/audio_codec_dev.py score --checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed2.pt
    python ml/evaluation/audio_codec_dev.py summarise --checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed2.pt `
        --calibration paper/config/audio_calibration.json --frozen paper/config/frozen_audio_config.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402  (also puts backend/ on sys.path)

SUBSAMPLE = REPO_ROOT / "paper_results/audio_heuristics_dev/subsample.csv"
OUT_DIR = REPO_ROOT / "paper_results/audio_codec_dev"
COLUMNS = ["utt_id", "label", "attack_id", "condition", "checkpoint", "mean_spoof_logit", "n_windows", "error"]
GUARD_RATE = 0.05

_models: dict = {}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def conditions() -> list[str]:
    from ml.preprocessing.audio_codecs import ALL_CONDITIONS

    return ["original", *ALL_CONDITIONS]


def family(condition: str) -> str:
    """mp3, aac, opus, or resample (any change of sample rate)."""
    return condition.split("_", 1)[0]


def _init(checkpoints: list[str], threads: int) -> None:
    import torch

    torch.set_num_threads(threads)
    from ml.evaluation.eval_asvspoof import load_model

    for path in checkpoints:
        _models[Path(path).name] = load_model(Path(path), torch.device("cpu"))[0]


def score_task(task: tuple[str, str, int]) -> list[dict]:
    """Every condition of one utterance with every loaded checkpoint; errors recorded, never raised."""
    import torch
    from app.ml.asvspoof_frontend import utterance_lfcc

    from ml.preprocessing.asvspoof_features import load_waveform
    from ml.preprocessing.audio_codecs import encode_decode

    utt_id, path, num_samples = task
    rows = []
    for condition in conditions():
        try:
            wave = load_waveform(Path(path)) if condition == "original" else encode_decode(Path(path), condition,
                                                                                            num_samples)
            features = torch.from_numpy(utterance_lfcc(wave)).unsqueeze(1)
            for name, model in _models.items():
                with torch.no_grad():
                    logits = model(features.float()).float().squeeze(1).numpy()
                rows.append({"utt_id": utt_id, "condition": condition, "checkpoint": name,
                             "mean_spoof_logit": float(np.atleast_1d(logits).mean()),
                             "n_windows": int(np.atleast_1d(logits).size), "error": ""})
        except Exception as exc:
            rows += [{"utt_id": utt_id, "condition": condition, "checkpoint": name,
                      "error": f"{type(exc).__name__}: {exc}"[:300]} for name in _models or ["?"]]
    return rows


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def cmd_score(args: argparse.Namespace) -> int:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root, read_manifest
    from ml.provenance import collect_provenance, sha256_file

    root = args.asvspoof_root or default_la_root()
    if root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")
    with open(SUBSAMPLE, newline="", encoding="utf-8") as handle:
        sample = list(csv.DictReader(handle))
    manifest = {r["utt_id"]: r for r in read_manifest(args.manifest) if r["split"] == "dev"}
    if any(r["utt_id"] not in manifest for r in sample):
        raise SystemExit("The subsample holds an utterance that is not in the dev manifest.")
    names = [p.name for p in args.checkpoint]
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    scores_path = out / "scores.csv"
    existing = read_rows(scores_path)
    done = {r["utt_id"] for r in existing if r["checkpoint"] in names}
    todo = [r for r in sample if r["utt_id"] not in done][: args.limit]
    config_path = out / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {"runs": []}
    config.update({
        "purpose": "Codec robustness on ASVspoof 2019 LA dev (paper/config/audio_codec_plan.json)",
        "subsample": {"file": _rel(SUBSAMPLE), "sha256": sha256_file(SUBSAMPLE), "size": len(sample)},
        "conditions": conditions(),
        "scoring": "utterance_lfcc (as served), CPU strict float32, mean window spoof logit",
    })
    config["runs"].append({"checkpoints": [{"name": p.name, "sha256": sha256_file(p)} for p in args.checkpoint],
                           "n_utterances": len(todo), "provenance": collect_provenance(args.manifest)})
    config_path.write_text(json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"{len(sample):,} utterances x {len(conditions())} conditions x {len(names)} checkpoint(s); "
          f"{len(todo):,} to do", flush=True)

    new_file = not scores_path.is_file()
    t0 = time.perf_counter()
    with open(scores_path, "a", newline="", encoding="utf-8") as handle, \
            ProcessPoolExecutor(max_workers=args.workers, initializer=_init,
                                initargs=([str(p) for p in args.checkpoint], args.threads)) as pool:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        tasks = [(r["utt_id"], str(root / manifest[r["utt_id"]]["relative_path"]),
                  int(manifest[r["utt_id"]]["num_samples"])) for r in todo]
        labels = {r["utt_id"]: r for r in todo}
        for k, future in enumerate(as_completed([pool.submit(score_task, t) for t in tasks]), start=1):
            for row in future.result():
                src = labels[row["utt_id"]]
                writer.writerow({**{c: "" for c in COLUMNS}, **row, "label": src["label"],
                                 "attack_id": src["attack_id"]})
            handle.flush()
            if k % 100 == 0 or k == len(tasks):
                rate = k / (time.perf_counter() - t0)
                print(f"  {k:,}/{len(tasks):,} | {rate:.1f} utt/s | ETA {(len(tasks) - k) / rate / 60:.1f} min",
                      flush=True)
    return 0


def frozen_verdicts(logits: np.ndarray, calibration: dict, frozen: dict) -> np.ndarray:
    """'authentic' / 'inconclusive' / 'flagged' as the backend's frozen rule gives them."""
    p = 1.0 / (1.0 + np.exp(-(float(calibration["a"]) * logits + float(calibration["b"]))))
    return np.where(p >= float(frozen["flagged_at_or_above"]), "flagged",
                    np.where(p < float(frozen["authentic_below"]), "authentic", "inconclusive"))


def summarise_checkpoint(rows: list[dict], checkpoint: str, calibration: dict | None = None,
                         frozen: dict | None = None) -> dict:
    from ml.evaluation.asvspoof_metrics import eer
    from ml.evaluation.metrics import roc_auc

    mine = [r for r in rows if r["checkpoint"] == checkpoint]
    result: dict = {"checkpoint": checkpoint, "conditions": {}}
    for condition in conditions():
        group = [r for r in mine if r["condition"] == condition and not r["error"]]
        if not group:
            continue
        y = np.array([int(r["label"]) for r in group])
        logit = np.array([float(r["mean_spoof_logit"]) for r in group])
        entry: dict = {"n": len(group), "errors": sum(1 for r in mine if r["condition"] == condition and r["error"]),
                       "eer": float(eer(-logit[y == 0], -logit[y == 1])[0]), "auc": float(roc_auc(y, logit))}
        if calibration and frozen:
            verdicts = frozen_verdicts(logit, calibration, frozen)
            entry["bonafide_flagged_rate"] = float(np.mean(verdicts[y == 0] == "flagged"))
            entry["bonafide_authentic_rate"] = float(np.mean(verdicts[y == 0] == "authentic"))
            entry["spoof_flagged_rate"] = float(np.mean(verdicts[y == 1] == "flagged"))
        result["conditions"][condition] = entry
    if calibration and frozen:
        families = sorted({family(c) for c in result["conditions"] if c != "original"})
        result["guard"] = {
            "rule": f"a codec family is guarded if any of its conditions flags more than {GUARD_RATE:.0%} of "
                    "bona fide dev utterances under the frozen rule",
            "families": {f: any(e["bonafide_flagged_rate"] > GUARD_RATE for c, e in result["conditions"].items()
                                if family(c) == f) for f in families},
        }
    return result


def cmd_summarise(args: argparse.Namespace) -> int:
    rows = read_rows(args.output_dir / "scores.csv")
    calibration = json.loads(args.calibration.read_text(encoding="utf-8")) if args.calibration else None
    frozen = json.loads(args.frozen.read_text(encoding="utf-8")) if args.frozen else None
    summary = summarise_checkpoint(rows, args.checkpoint[0].name, calibration, frozen)
    if calibration and frozen:
        summary["calibration_file"], summary["frozen_file"] = _rel(args.calibration), _rel(args.frozen)
    path = args.output_dir / f"metrics_{args.checkpoint[0].stem}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for condition, e in summary["conditions"].items():
        extra = (f" | bona fide flagged {e['bonafide_flagged_rate'] * 100:5.1f}% | spoof flagged "
                 f"{e['spoof_flagged_rate'] * 100:5.1f}%") if "bonafide_flagged_rate" in e else ""
        print(f"{condition:9s} EER {e['eer'] * 100:6.2f}% AUC {e['auc']:.4f}{extra}")
    if "guard" in summary:
        print("guard:", summary["guard"]["families"])
    print(f"wrote {_rel(path)}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("score", "summarise"):
        p = sub.add_parser(name)
        p.add_argument("--checkpoint", type=Path, nargs="+", required=True)
        p.add_argument("--output-dir", type=Path, default=OUT_DIR)
    score = sub.choices["score"]
    score.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    score.add_argument("--asvspoof-root", type=Path, default=default_la_root())
    score.add_argument("--workers", type=int, default=16)
    score.add_argument("--threads", type=int, default=2)
    score.add_argument("--limit", type=int, default=None)
    summary = sub.choices["summarise"]
    summary.add_argument("--calibration", type=Path, default=None)
    summary.add_argument("--frozen", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return cmd_score(args) if args.command == "score" else cmd_summarise(args)


if __name__ == "__main__":
    raise SystemExit(main())
