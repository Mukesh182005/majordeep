#!/usr/bin/env python3
"""Train the LCNN on ASVspoof 2019 LA (official train split), select by dev EER.

* Model: ``build_audio_model`` (LCNN) from ``backend/app/ml/models_arch.py``.
* Input: window 0 of each training utterance (first 4 s, repeated if short)
  from the cached ``logmel`` or ``lfcc`` features.
* Class imbalance (about 9 spoof : 1 bona fide): weighted BCE loss with
  ``pos_weight = n_bonafide / n_spoof`` (default), or ``--balance sampler`` for
  a class-balanced sampler. The choice is recorded in the run config.
* Training steps reuse ``_run_epoch`` from ``ml/training/engine.py`` (AMP,
  gradient clipping). Dev scoring runs in float32 and averages the logits of
  all 4 s windows of each utterance.
* The checkpoint kept is the epoch with the lowest dev EER. The eval split is
  never touched here.
* Resumable: ``last.pt`` in the run folder is written every epoch; rerun the
  same command with ``--resume``.

Writes the checkpoint to ``checkpoints/audio_lcnn_asvspoof_<features>_seed<k>.pt``
(never ``audio_detector.pt``, never over an existing file) and the run record
(train log, dev scores and metrics, config with provenance) to
``paper_results/audio_asvspoof2019la/dev_runs/<name>/``.

Usage (PowerShell, from the repository root)::

    python ml/training/train_asvspoof.py --features lfcc --seed 0
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT, set_seed  # noqa: E402

PROTECTED_CHECKPOINTS = {"audio_detector.pt", "image_detector.pt", "image_detector_b0.pt"}


class _InputsTargets:
    """Adapts (features, label, utt_id) batches to the (inputs, targets) the engine expects."""

    def __init__(self, loader) -> None:
        self.loader = loader

    def __len__(self) -> int:
        return len(self.loader)

    def __iter__(self):
        for features, labels, _utts in self.loader:
            yield features, labels.float().unsqueeze(1)


def parse_args() -> argparse.Namespace:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--features", choices=["logmel", "lfcc"], required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--warmup-epochs", type=int, default=1)
    parser.add_argument("--patience", type=int, default=10, help="stop after this many epochs without a dev EER gain")
    parser.add_argument("--balance", choices=["weighted_loss", "sampler"], default="weighted_loss")
    parser.add_argument("--output", type=Path, default=None,
                        help="checkpoint path (default: checkpoints/audio_lcnn_asvspoof_<features>_seed<k>.pt)")
    parser.add_argument("--run-dir", type=Path, default=None,
                        help="default: paper_results/audio_asvspoof2019la/dev_runs/<checkpoint stem>")
    parser.add_argument("--cache", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/features")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    parser.add_argument("--asvspoof-root", type=Path, default=default_la_root(), help="for dev ASV scores (t-DCF)")
    parser.add_argument("--train-limit", type=int, default=None, help="random subset of train (smoke tests only)")
    parser.add_argument("--device", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--extra-train-splits", nargs="*", default=[],
                        help="further cached splits of the same utterances to train on, e.g. train_codec")
    parser.add_argument("--dev-splits", nargs="+", default=["dev"],
                        help="cached dev splits; the selection EER is pooled over all of them")
    parser.add_argument("--tag", default="", help="inserted into the run name, e.g. _codec")
    return parser.parse_args()


def _rng_state(generator) -> dict:
    import torch

    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "loader": generator.get_state(),
    }


def _restore_rng(state: dict, generator) -> None:
    import torch

    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    if state["cuda"] is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])
    generator.set_state(state["loader"])


def main() -> None:
    import torch
    import torch.nn as nn
    from app.ml.models_arch import build_audio_model
    from torch.utils.data import DataLoader, WeightedRandomSampler

    from ml.evaluation.asvspoof_metrics import eer, evaluate_scores
    from ml.evaluation.eval_asvspoof import cm_scores, load_asv, score_split, write_scores
    from ml.preprocessing.build_asvspoof2019_la import sha256_file
    from ml.provenance import collect_provenance
    from ml.training.asvspoof_dataset import (
        ASVspoofTrainDataset,
        ASVspoofWindowDataset,
        CachedSplit,
    )
    from ml.training.engine import _format_duration, _run_epoch

    args = parse_args()
    name = f"audio_lcnn_asvspoof_{args.features}{args.tag}_seed{args.seed}"
    output = (args.output or REPO_ROOT / "checkpoints" / f"{name}.pt").resolve()
    run_dir = (args.run_dir or REPO_ROOT / "paper_results/audio_asvspoof2019la/dev_runs" / output.stem).resolve()
    last_path = run_dir / "last.pt"
    if output.name in PROTECTED_CHECKPOINTS:
        raise SystemExit(f"Refusing to write {output.name}: existing checkpoints are never overwritten.")
    if output.exists() and not args.resume:
        raise SystemExit(f"{output} already exists. Use --resume to continue that run, or choose another --output.")
    if output.exists() and args.resume and not last_path.exists():
        raise SystemExit(f"No resume state at {last_path}; refusing to restart over the existing {output.name}.")
    run_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    set_seed(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(device)}")

    from torch.utils.data import ConcatDataset

    train_cache = CachedSplit(args.cache, args.features, "train")
    extra_caches = [CachedSplit(args.cache, args.features, s) for s in args.extra_train_splits]
    dev_caches = [CachedSplit(args.cache, args.features, s) for s in args.dev_splits]
    dev_cache = dev_caches[0]
    if len({c.manifest_sha256 for c in [train_cache, *extra_caches, *dev_caches]}) != 1:
        raise SystemExit("the train and dev caches come from different manifests")
    for extra in extra_caches:
        if extra.utt_ids != train_cache.utt_ids:
            raise SystemExit(f"{extra.split} does not hold the train utterances in the same order")

    indices = np.arange(len(train_cache))
    if args.train_limit:
        indices = np.sort(np.random.default_rng(args.seed).choice(indices, size=args.train_limit, replace=False))
    parts = [ASVspoofTrainDataset(c, indices) for c in [train_cache, *extra_caches]]
    train_set = parts[0] if len(parts) == 1 else ConcatDataset(parts)
    labels = np.concatenate([part.labels for part in parts])
    n_spoof, n_bona = int(labels.sum()), int((labels == 0).sum())
    print(f"train: {len(train_set):,} examples ({n_bona:,} bona fide, {n_spoof:,} spoof) from "
          f"{', '.join(c.split for c in [train_cache, *extra_caches])} | dev: "
          + ", ".join(f"{c.split} {len(c):,} utterances" for c in dev_caches))

    generator = torch.Generator()
    generator.manual_seed(args.seed)
    if args.balance == "sampler":
        weights = np.where(labels == 1, 1.0 / n_spoof, 1.0 / n_bona)
        sampler = WeightedRandomSampler(weights.tolist(), num_samples=len(labels), replacement=True,
                                        generator=generator)
        train_loader = DataLoader(train_set, batch_size=args.batch_size, sampler=sampler, drop_last=True)
        criterion = nn.BCEWithLogitsLoss()
        balance_note = "class-balanced WeightedRandomSampler, unweighted BCE"
    else:
        train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, generator=generator,
                                  drop_last=True)
        pos_weight = n_bona / n_spoof
        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight], device=device))
        balance_note = f"weighted BCE, pos_weight = n_bonafide / n_spoof = {pos_weight:.6f}"
    dev_sets = [ASVspoofWindowDataset(c) for c in dev_caches]
    dev_labels = np.concatenate([c.labels for c in dev_caches])

    def pooled_dev_scores() -> list[np.ndarray]:
        return [cm_scores(c, score_split(model, s, device)) for c, s in zip(dev_caches, dev_sets)]

    model = build_audio_model().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    def lr_lambda(epoch: int) -> float:  # linear warm-up, then cosine decay (as in engine.train_model)
        if epoch < args.warmup_epochs:
            return float(epoch + 1) / float(max(1, args.warmup_epochs))
        progress = (epoch - args.warmup_epochs) / max(1, args.epochs - args.warmup_epochs)
        return 0.5 * (1.0 + np.cos(np.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler(enabled=use_amp)

    train_config = {
        "features": args.features,
        "seed": args.seed,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "optimizer": "AdamW",
        "lr": args.lr,
        "weight_decay": args.weight_decay,
        "schedule": f"linear warm-up {args.warmup_epochs} epoch(s), cosine decay",
        "patience_epochs": args.patience,
        "max_grad_norm": 5.0,
        "amp_training": use_amp,
        "inference_dtype": "float32",
        "class_balance": balance_note,
        "selection": "epoch with the lowest dev EER (pooled over the dev splits, window-averaged logits); "
                     "eval split unused",
        "train_splits": [c.split for c in [train_cache, *extra_caches]],
        "dev_splits": [c.split for c in dev_caches],
        "train_input": "window 0 of each utterance (first 4 s, repeated if shorter)",
        "train_limit": args.train_limit,
        "n_train": len(train_set),
        "n_dev": int(sum(len(c) for c in dev_caches)),
    }

    # Recorded in every checkpoint so it states what it was trained on (P2).
    from ml.provenance import git_state

    summary_path = args.manifest.parent / "dataset_summary.json"
    dataset_record = {
        "dataset": "ASVspoof 2019 logical access (LA)",
        "split_policy": "official CM protocol files: trained on train, epoch chosen on dev, eval unused",
        "protocol_sha256": (json.loads(summary_path.read_text(encoding="utf-8")).get("protocol_sha256")
                            if summary_path.is_file() else None),
        "git_commit": git_state().get("git_commit"),
    }

    start_epoch, best_eer, best_epoch, stale = 1, float("inf"), 0, 0
    log_path = run_dir / "train_log.csv"
    if args.resume and last_path.exists():
        # The resume file holds Python and NumPy RNG states, which the safe loader
        # rejects; it is this script's own output in its own run folder.
        state = torch.load(last_path, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        _restore_rng(state["rng"], generator)
        start_epoch, best_eer, best_epoch, stale = state["epoch"] + 1, state["best_eer"], state["best_epoch"], state["stale"]
        print(f"Resuming after epoch {state['epoch']} (best dev EER {best_eer * 100:.3f}% at epoch {best_epoch})")
    else:
        with open(log_path, "w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(["epoch", "train_loss", "dev_eer", "lr", "epoch_s"])

    feature_config = json.loads((Path(args.cache) / args.features / "frontend.json").read_text(encoding="utf-8"))
    for epoch in range(start_epoch, args.epochs + 1):
        if stale >= args.patience:
            print(f"Early stop: no dev EER gain for {args.patience} epochs.")
            break
        t0 = time.perf_counter()
        lr = optimizer.param_groups[0]["lr"]
        train_loss = _run_epoch(model, _InputsTargets(train_loader), criterion, optimizer, scaler, device,
                                use_amp, 5.0)
        scheduler.step()
        dev_scores = np.concatenate(pooled_dev_scores())
        dev_eer = eer(dev_scores[dev_labels == 0], dev_scores[dev_labels == 1])[0]
        epoch_s = time.perf_counter() - t0
        with open(log_path, "a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow([epoch, f"{train_loss:.6f}", f"{dev_eer:.6f}", f"{lr:.3e}", f"{epoch_s:.1f}"])
        improved = dev_eer < best_eer
        print(f"epoch {epoch:3d}/{args.epochs} | train loss {train_loss:.4f} | dev EER {dev_eer * 100:6.3f}% | "
              f"{epoch_s:.0f}s | ETA {_format_duration(epoch_s * (args.epochs - epoch))}"
              + ("  <- best" if improved else ""), flush=True)
        if improved:
            best_eer, best_epoch, stale = dev_eer, epoch, 0
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "architecture": "LCNN",
                    "frontend": args.features,
                    "input_shape": [1, feature_config["bands"], feature_config["frames_per_window"]],
                    "feature_config": feature_config,
                    "epoch": epoch,
                    "dev_eer": dev_eer,
                    "seed": args.seed,
                    "train_config": train_config,
                    "manifest_sha256": train_cache.manifest_sha256,
                    **dataset_record,
                    "score_convention": "model outputs a spoof logit; CM score = -mean window logit",
                    "model_version": f"audio-lcnn-asvspoof2019la-{args.features}{args.tag.replace('_', '-')}"
                                     f"-seed{args.seed}",
                },
                output,
            )
        else:
            stale += 1
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "scaler": scaler.state_dict(),
                "rng": _rng_state(generator),
                "epoch": epoch,
                "best_eer": best_eer,
                "best_epoch": best_epoch,
                "stale": stale,
            },
            last_path,
        )

    # Re-score dev with the selected epoch and record everything about the run.
    best = torch.load(output, map_location="cpu", weights_only=True)
    model.load_state_dict(best["state_dict"])
    per_split = pooled_dev_scores()
    asv, asv_note = load_asv(args.asvspoof_root, "dev")
    for cache, scores in zip(dev_caches, per_split):
        suffix = "" if cache.split == "dev" else "_" + cache.split.removeprefix("dev_")
        write_scores(run_dir / f"dev{suffix}_scores.csv", cache, scores)
    dev_scores = per_split[0]
    dev_metrics = evaluate_scores(dev_scores, dev_cache.labels, np.array(dev_cache.attack_ids), asv)
    dev_metrics["asv_scores"] = asv_note
    if len(dev_caches) > 1:
        pooled = np.concatenate(per_split)
        dev_metrics["pooled"] = {"splits": [c.split for c in dev_caches],
                                 "eer": float(eer(pooled[dev_labels == 0], pooled[dev_labels == 1])[0]),
                                 "per_split_eer": {c.split: float(eer(s[c.labels == 0], s[c.labels == 1])[0])
                                                   for c, s in zip(dev_caches, per_split)}}
    (run_dir / "dev_metrics.json").write_text(json.dumps(dev_metrics, indent=2, default=str), encoding="utf-8")
    run_config = {
        "run": output.stem,
        "checkpoint": output.relative_to(REPO_ROOT).as_posix() if output.is_relative_to(REPO_ROOT) else output.name,
        "checkpoint_sha256": sha256_file(output),
        "best_epoch": best_epoch,
        "dev_eer": dev_metrics["eer"],
        "pooled_dev_eer": dev_metrics.get("pooled", {}).get("eer", dev_metrics["eer"]),
        "dev_min_tdcf": dev_metrics["min_tdcf"],
        "train_config": train_config,
        "feature_config": feature_config,
        "provenance": collect_provenance(args.manifest if args.manifest.is_file() else None, seeds=args.seed),
    }
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, default=str), encoding="utf-8")
    tdcf = "n/a" if dev_metrics["min_tdcf"] is None else f"{dev_metrics['min_tdcf']:.4f}"
    print(f"\nBest epoch {best_epoch}: dev EER {dev_metrics['eer'] * 100:.3f}%, dev min t-DCF {tdcf}")
    print(f"Checkpoint: {output}\nRun record: {run_dir}")


if __name__ == "__main__":
    main()
