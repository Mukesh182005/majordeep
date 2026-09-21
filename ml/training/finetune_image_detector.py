#!/usr/bin/env python3
"""Fine-tune the EfficientNet-B4 image detector on the expanded 120,000+ dataset.

Starts from the current checkpoint (image_detector.pt) and fine-tunes with
calibrated low learning rate, AMP (fp16), and AdamW on the NVIDIA GeForce RTX 5070.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from ml.common import REPO_ROOT, set_seed
from ml.training.datasets import FaceCropDataset
from ml.training.engine import TrainConfig
from app.ml.models_arch import build_image_model
from app.ml.checkpoints import extract_state_dict
from ml.evaluation.metrics import compute_metrics, format_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO_ROOT / "data/processed/faces",
        help="Directory containing manifest.csv",
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--size", type=int, default=224)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=REPO_ROOT / "checkpoints" / "image_detector.pt",
        help="Source and destination checkpoint path",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
    )
    parser.add_argument(
        "--version",
        default="image-detector-v2.1.0-b4-expanded",
    )
    return parser.parse_args()


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device, use_amp: bool) -> tuple[float, dict]:
    model.eval()
    criterion = nn.BCEWithLogitsLoss()
    total_loss = 0.0
    all_scores: list[float] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(loader):
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            with torch.amp.autocast(device_type="cuda", enabled=use_amp):
                logits = model(inputs)
                loss = criterion(logits, targets)

            total_loss += float(loss.item())
            probabilities = torch.sigmoid(logits).cpu().numpy().flatten()
            all_scores.extend(probabilities.tolist())
            all_labels.extend(targets.cpu().numpy().flatten().astype(int).tolist())

            if (batch_idx + 1) % 100 == 0 or (batch_idx + 1) == len(loader):
                print(f"  [Validation] Batch {batch_idx + 1}/{len(loader)} evaluated...", end="\n", flush=True)

    print()
    avg_loss = total_loss / max(1, len(loader))
    metrics = compute_metrics(np.array(all_labels), np.array(all_scores))
    return avg_loss, metrics


def main() -> None:
    args = parse_args()
    set_seed(42)

    device = torch.device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    print("=" * 65)
    print("DEEPFAKE IMAGE DETECTOR FINE-TUNING PIPELINE")
    print(f"Hardware Device : {device.type.upper()} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
    if device.type == "cuda":
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU VRAM Total  : {total_vram:.1f} GB")
    print(f"Checkpoint Path : {args.checkpoint}")
    print(f"Target Version  : {args.version}")
    print("=" * 65)

    manifest = args.data / "manifest.csv"
    if not manifest.exists():
        raise SystemExit(f"No manifest found at {manifest}. Run scripts/expand_training_dataset.py first.")

    print("\nLoading dataset splits from manifest...")
    train_set = FaceCropDataset(manifest, "train", size=args.size)
    val_set = FaceCropDataset(manifest, "val", size=args.size)
    print(f"  Training samples   : {len(train_set):,} images")
    print(f"  Validation samples : {len(val_set):,} images")

    pin = (device.type == "cuda")
    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=pin,
        drop_last=True,
        persistent_workers=(args.workers > 0),
    )
    val_loader = DataLoader(
        val_set,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=pin,
    )

    print(f"\nConstructing EfficientNet-B4 backbone and loading pre-trained weights...")
    model = build_image_model("efficientnet_b4", pretrained=False)
    
    if args.checkpoint.exists():
        print(f"  Loading existing checkpoint from {args.checkpoint}...")
        ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        state_dict = extract_state_dict(ckpt)
        model.load_state_dict(state_dict)
        print("  Pre-trained weights loaded successfully into model!")
    else:
        print("  WARNING: Checkpoint not found; training from ImageNet weights.")
        model = build_image_model("efficientnet_b4", pretrained=True)

    model.to(device)

    # Optimizer, Loss, AMP Scaler, Scheduler
    use_amp = (device.type == "cuda")
    scaler = torch.amp.GradScaler(enabled=use_amp)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=args.lr * 0.1)

    print(f"\nInitial baseline evaluation on {len(val_set):,} validation images...")
    base_val_loss, base_metrics = evaluate(model, val_loader, device, use_amp)
    print(f"  Baseline Val Loss: {base_val_loss:.5f} | Accuracy: {base_metrics['accuracy'] * 100:.2f}% | AUC-ROC: {base_metrics['auc_roc']:.5f}")

    best_val_loss = base_val_loss
    best_metrics = base_metrics

    # Training loop
    total_batches = len(train_loader)
    print(f"\nStarting fine-tuning for {args.epochs} epoch(s) ({total_batches} batches per epoch, batch size {args.batch_size})...\n")

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_start = time.perf_counter()
        running_loss = 0.0
        print(f"--- Epoch {epoch}/{args.epochs} (lr={scheduler.get_last_lr()[0]:.2e}) ---")

        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda", enabled=use_amp):
                logits = model(inputs)
                loss = criterion(logits, targets)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()

            running_loss += float(loss.item())

            if (batch_idx + 1) % 100 == 0 or (batch_idx + 1) == total_batches:
                avg_b_loss = running_loss / (batch_idx + 1)
                elapsed = time.perf_counter() - epoch_start
                batches_done = batch_idx + 1
                rate = batches_done / elapsed
                remaining_s = (total_batches - batches_done) / max(0.1, rate)
                vram_used = (torch.cuda.memory_allocated(0) / (1024**3)) if device.type == "cuda" else 0.0
                print(
                    f"  Batch [{batches_done:5d}/{total_batches}] "
                    f"Loss: {avg_b_loss:.4f} | "
                    f"Speed: {rate * args.batch_size:.1f} img/s | "
                    f"VRAM: {vram_used:.1f}GB | "
                    f"ETA: {remaining_s:.0f}s",
                    end="\n",
                    flush=True,
                )

        scheduler.step()
        print()
        epoch_time = time.perf_counter() - epoch_start
        train_loss = running_loss / total_batches

        # Validation
        print(f"  Validating on {len(val_set):,} images...")
        val_loss, metrics = evaluate(model, val_loader, device, use_amp)
        print(
            f"  Epoch {epoch} Results in {epoch_time:.1f}s:\n"
            f"    Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f}\n"
            f"    Val Accuracy: {metrics['accuracy'] * 100:.2f}% | Val Recall: {metrics['recall'] * 100:.2f}%\n"
            f"    AUC-ROC: {metrics['auc_roc']:.5f} | EER: {metrics['eer']:.4f}"
        )

        # Save checkpoint if better or at end
        if val_loss < best_val_loss or epoch == args.epochs:
            best_val_loss = min(best_val_loss, val_loss)
            best_metrics = metrics
            print(f"  --> Saving improved checkpoint to {args.checkpoint}...")
            
            save_payload = {
                "state_dict": model.state_dict(),
                "version": args.version,
                "epoch": epoch,
                "val_accuracy": float(metrics["accuracy"]),
                "val_auc": float(metrics["auc_roc"]),
                "val_eer": float(metrics["eer"]),
                "backbone": "efficientnet_b4",
                "input_size": args.size,
                "extra_metadata": {
                    "dataset": "faces-140k-expanded",
                    "training_samples": len(train_set),
                    "validation_samples": len(val_set),
                    "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
                }
            }
            torch.save(save_payload, args.checkpoint)

            # Update summary JSON
            summary_path = args.checkpoint.with_name("image_detector.summary.json")
            summary_data = {
                "best_val_loss": float(val_loss),
                "best_val_metrics": metrics,
                "epochs_run": epoch,
                "amp_used": use_amp,
                "checkpoint": str(args.checkpoint),
                "model_version": args.version,
                "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
                "backbone": "efficientnet_b4",
                "input_size": args.size,
                "training_dataset_size": len(train_set),
                "validation_dataset_size": len(val_set),
            }
            summary_path.write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")
            print(f"  --> Updated {summary_path.name}")

    print("\n" + "=" * 65)
    print("FINE-TUNING COMPLETED SUCCESSFULLY!")
    print(format_report(best_metrics))
    print("=" * 65)


if __name__ == "__main__":
    main()
