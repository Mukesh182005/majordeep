#!/usr/bin/env python3
"""Score an ASVspoof 2019 LA split with a trained LCNN and compute its metrics.

Writes ``<split>_scores.csv`` (utt_id, attack_id, label, score) and
``<split>_metrics.json``. Following the ASVspoof convention, a higher score
means more likely bona fide: score = minus the mean of the per-window spoof
logits. Inference always runs in float32.

The eval split is the final test. Scoring it requires ``--confirm-final-eval``
and a checkpoint listed in ``paper/config/audio_model_selection.json`` (the
choice made on dev, committed first). Every eval scoring is appended to
``eval_log.csv``; a checkpoint already scored on eval is refused unless a
reason is given with ``--rescore-reason``.

Usage (PowerShell, from the repository root)::

    python ml/evaluation/eval_asvspoof.py --checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed0.pt --split dev
    python ml/evaluation/eval_asvspoof.py --checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed0.pt `
        --split eval --confirm-final-eval
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

RESULTS_DIR = REPO_ROOT / "paper_results/audio_asvspoof2019la"
SELECTION_FILE = REPO_ROOT / "paper/config/audio_model_selection.json"
DEFAULT_CACHE = REPO_ROOT / "data/processed/asvspoof2019_la/features"


def score_split(model, dataset, device, batch_size: int = 256) -> dict[str, float]:
    """Mean spoof logit per utterance over all windows, computed in float32."""
    import torch
    from torch.utils.data import DataLoader

    from ml.training.asvspoof_dataset import average_by_utterance

    model.eval()
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    utt_ids: list[str] = []
    logits: list[np.ndarray] = []
    with torch.no_grad():
        for features, _labels, utts in loader:
            out = model(features.to(device, dtype=torch.float32)).float().squeeze(1)
            logits.append(out.cpu().numpy())
            utt_ids.extend(utts)
    return average_by_utterance(utt_ids, np.concatenate(logits))


def cm_scores(cache, mean_logits: dict[str, float]) -> np.ndarray:
    """CM scores (higher = bona fide) in the cache's utterance order."""
    return np.array([-mean_logits[utt] for utt in cache.utt_ids], dtype=np.float64)


def write_scores(path: Path, cache, scores: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "attack_id", "label", "score"])
        for utt, attack, label, score in zip(cache.utt_ids, cache.attack_ids, cache.labels, scores, strict=True):
            writer.writerow([utt, attack, int(label), f"{score:.6f}"])


def read_scores(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        "utt_id": np.array([r["utt_id"] for r in rows]),
        "attack_id": np.array([r["attack_id"] for r in rows]),
        "label": np.array([int(r["label"]) for r in rows]),
        "score": np.array([float(r["score"]) for r in rows]),
    }


def load_asv(la_root: Path | None, split: str):
    from ml.evaluation.asvspoof_metrics import ASV_SCORE_FILES, load_asv_scores

    if la_root is None:
        return None, "LA root unknown (set DEEPSENTINEL_DATA)"
    path = la_root / ASV_SCORE_FILES[split]
    if not path.is_file():
        return None, f"ASV score file not found: {ASV_SCORE_FILES[split]}"
    return load_asv_scores(path), ASV_SCORE_FILES[split]


def load_model(checkpoint_path: Path, device):
    import torch
    from app.ml.models_arch import build_audio_model

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model = build_audio_model()
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device).float().eval()
    return model, checkpoint


def _eval_guard(checkpoint_sha: str, args: argparse.Namespace, log_path: Path) -> None:
    if not args.confirm_final_eval:
        raise SystemExit("Scoring the eval split is the final test: pass --confirm-final-eval.")
    if not SELECTION_FILE.is_file():
        raise SystemExit(f"{SELECTION_FILE.relative_to(REPO_ROOT)} not found: choose the configuration on dev "
                         "(ml/evaluation/select_asvspoof_frontend.py) and commit it before scoring eval.")
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    selected = {c["sha256"] for c in selection.get("selected_checkpoints", [])}
    if checkpoint_sha not in selected:
        raise SystemExit("This checkpoint is not in the dev-based selection; eval scoring refused.")
    if log_path.is_file():
        with open(log_path, newline="", encoding="utf-8") as handle:
            previous = [r for r in csv.DictReader(handle) if r["checkpoint_sha256"] == checkpoint_sha]
        if previous and not args.rescore_reason:
            raise SystemExit("This checkpoint was already scored on eval; pass --rescore-reason to repeat it "
                             "(the reason is logged).")


def parse_args() -> argparse.Namespace:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "eval"], required=True)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--asvspoof-root", type=Path, default=default_la_root())
    parser.add_argument("--output", type=Path, default=None, help="default: paper_results/audio_asvspoof2019la/<split>")
    parser.add_argument("--confirm-final-eval", action="store_true")
    parser.add_argument("--rescore-reason", default="")
    parser.add_argument("--device", default=None)
    parser.add_argument("--batch-size", type=int, default=256)
    return parser.parse_args()


def main() -> None:
    import torch

    from ml.evaluation.asvspoof_metrics import evaluate_scores
    from ml.preprocessing.build_asvspoof2019_la import sha256_file
    from ml.provenance import collect_provenance
    from ml.training.asvspoof_dataset import ASVspoofWindowDataset, CachedSplit

    args = parse_args()
    checkpoint_sha = sha256_file(args.checkpoint)
    log_path = RESULTS_DIR / "eval_log.csv"
    if args.split == "eval":
        _eval_guard(checkpoint_sha, args, log_path)

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model, checkpoint = load_model(args.checkpoint, device)
    frontend = checkpoint["frontend"]
    cache = CachedSplit(args.cache, frontend, args.split)
    if checkpoint.get("manifest_sha256") and cache.manifest_sha256 != checkpoint["manifest_sha256"]:
        raise SystemExit("Feature cache was built from a different manifest than the training data.")

    print(f"Scoring {args.split} ({len(cache):,} utterances, {int(cache.n_windows.sum()):,} windows) "
          f"with {args.checkpoint.name} [{frontend}] on {device}")
    mean_logits = score_split(model, ASVspoofWindowDataset(cache), device, args.batch_size)
    scores = cm_scores(cache, mean_logits)

    out_dir = args.output or RESULTS_DIR / args.split
    stem = args.checkpoint.stem
    scores_path = out_dir / f"{stem}_{args.split}_scores.csv"
    write_scores(scores_path, cache, scores)

    asv, asv_note = load_asv(args.asvspoof_root, args.split)
    metrics = evaluate_scores(scores, cache.labels, np.array(cache.attack_ids), asv)
    metrics.update(
        {
            "split": args.split,
            "frontend": frontend,
            "checkpoint": args.checkpoint.name,
            "checkpoint_sha256": checkpoint_sha,
            "checkpoint_epoch": checkpoint.get("epoch"),
            "checkpoint_dev_eer": checkpoint.get("dev_eer"),
            "seed": checkpoint.get("seed"),
            "asv_scores": asv_note,
            "score_convention": "higher = bona fide; score = -mean window spoof logit",
            "scores_file": scores_path.name,
            "provenance": collect_provenance(seeds=checkpoint.get("seed")),
        }
    )
    metrics_path = out_dir / f"{stem}_{args.split}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    if args.split == "eval":
        new_log = not log_path.is_file()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if new_log:
                writer.writerow(["utc_time", "checkpoint", "checkpoint_sha256", "git_commit", "rescore_reason"])
            writer.writerow([datetime.now(UTC).isoformat(timespec="seconds"), args.checkpoint.name, checkpoint_sha,
                             metrics["provenance"]["git_commit"], args.rescore_reason])

    tdcf = "n/a" if metrics["min_tdcf"] is None else f"{metrics['min_tdcf']:.4f}"
    print(f"EER {metrics['eer'] * 100:.2f}% | min t-DCF {tdcf} | AUC {metrics['auc_bonafide_vs_spoof']:.4f}")
    print(f"Wrote {scores_path} and {metrics_path}")


if __name__ == "__main__":
    main()
