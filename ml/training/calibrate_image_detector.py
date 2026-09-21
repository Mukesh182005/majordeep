#!/usr/bin/env python3
"""25-Minute Multi-Platform Calibration Pipeline for EfficientNet-B4.

Calibrates the image detector on a balanced 55,000-sample multi-platform dataset:
- Instagram Real & Fake (10,000 images)
- LinkedIn Real & Fake (10,000 images)
- Pinterest Real & Fake (10,000 images)
- Facebook Real & Fake (10,000 images)
- Snapchat Real & Fake (10,000 images)
- Synthetic Inpaintings & Swaps (2,500 images)
- Modern Diffusion AI (2,500 images)

Runs on NVIDIA GeForce RTX 5070 with PyTorch AMP fp16, batch_size=64, num_workers=4.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from ml.common import REPO_ROOT, set_seed, read_manifest
from app.ml.models_arch import build_image_model
from app.ml.checkpoints import extract_state_dict
from ml.evaluation.metrics import compute_metrics, format_report


class CalibrationDataset(Dataset):
    def __init__(self, items: list[tuple[str, int]], size: int = 224, augment: bool = True):
        self.items = items
        if augment:
            self.transform = T.Compose([
                T.Resize((size, size)),
                T.RandomHorizontalFlip(),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            self.transform = T.Compose([
                T.Resize((size, size)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        path_str, label = self.items[idx]
        with Image.open(path_str) as opened:
            img = opened.convert("RGB")
        return self.transform(img), torch.tensor([float(label)], dtype=torch.float32)


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

    avg_loss = total_loss / max(1, len(loader))
    metrics = compute_metrics(np.array(all_labels), np.array(all_scores))
    return avg_loss, metrics


def main() -> None:
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cudnn.benchmark = (device.type == "cuda")

    ckpt_path = REPO_ROOT / "checkpoints" / "image_detector.pt"
    manifest_path = REPO_ROOT / "data" / "processed" / "faces" / "manifest.csv"

    print("=" * 68)
    print("FAST 25-MINUTE MULTI-PLATFORM CALIBRATION PIPELINE")
    print(f"Hardware Device : {device.type.upper()} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
    print(f"Checkpoint Path : {ckpt_path}")
    print(f"Batch Size      : 64  |  Target Samples: 55,000 balanced")
    print("=" * 68, flush=True)

    print(f"Loading master manifest from {manifest_path}...", flush=True)
    rows = read_manifest(manifest_path, "train")

    # Group by category (instagram, linkedin, pinterest, facebook, snapchat, inpaint, diffusion)
    categories: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for r in rows:
        grp = r.get("group", "")
        for cat in ["instagram", "linkedin", "pinterest", "facebook", "snapchat", "inpaint", "diffusion"]:
            if cat in grp.lower():
                categories[f"{cat}_{r['label']}"].append((r["path"], int(r["label"])))
                break

    # Build balanced calibration set: 5,000 per class (or 2,500 for specialized fakes)
    train_items: list[tuple[str, int]] = []
    val_items: list[tuple[str, int]] = []

    target_per_cat = {
        "instagram_0": 5000, "instagram_1": 5000,
        "linkedin_0":  5000, "linkedin_1":  5000,
        "pinterest_0": 5000, "pinterest_1": 5000,
        "facebook_0":  5000, "facebook_1":  5000,
        "snapchat_0":  5000, "snapchat_1":  5000,
        "inpaint_1":   2500, "diffusion_1": 2500,
    }

    print("\nSampling multi-platform calibration splits:", flush=True)
    for cat_key, target_n in target_per_cat.items():
        pool = categories.get(cat_key, [])
        random.shuffle(pool)
        n_take = min(target_n, len(pool))
        n_val = int(n_take * 0.1)
        train_items.extend(pool[:n_take - n_val])
        val_items.extend(pool[n_take - n_val:n_take])
        print(f"  {cat_key:15s}: {n_take - n_val:5d} train + {n_val:4d} val from {len(pool):,} available", flush=True)

    random.shuffle(train_items)
    print(f"\nTotal Calibration Samples: {len(train_items):,} train, {len(val_items):,} val", flush=True)

    train_ds = CalibrationDataset(train_items, size=224, augment=True)
    val_ds = CalibrationDataset(val_items, size=224, augment=False)

    train_loader = DataLoader(
        train_ds,
        batch_size=64,
        shuffle=True,
        num_workers=4,
        pin_memory=(device.type == "cuda"),
        persistent_workers=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=64,
        shuffle=False,
        num_workers=4,
        pin_memory=(device.type == "cuda"),
        persistent_workers=True,
    )

    print("\nLoading EfficientNet-B4 pre-trained model...", flush=True)
    model = build_image_model("efficientnet_b4", pretrained=False)
    if ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location="cpu")
        state_dict = extract_state_dict(ckpt)
        model.load_state_dict(state_dict)
        print("  Pre-trained weights loaded successfully!", flush=True)
    model.to(device)

    use_amp = (device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=1e-5)
    total_batches = len(train_loader)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_batches, eta_min=3e-6)

    print(f"\nEvaluating pre-calibration baseline on {len(val_ds):,} validation images...", flush=True)
    base_loss, base_metrics = evaluate(model, val_loader, device, use_amp)
    print(f"  Pre-Calibration Accuracy: {base_metrics['accuracy'] * 100:.2f}% | Loss: {base_loss:.4f} | AUC: {base_metrics['auc_roc']:.4f}\n", flush=True)

    print(f"Starting 1 calibration epoch ({total_batches} batches, batch size 64)...", flush=True)
    model.train()
    t_start = time.perf_counter()
    running_loss = 0.0

    for batch_idx, (inputs, targets) in enumerate(train_loader):
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=use_amp):
            logits = model(inputs)
            loss = criterion(logits, targets)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        running_loss += float(loss.item())

        if (batch_idx + 1) % 50 == 0 or (batch_idx + 1) == total_batches:
            done_batches = batch_idx + 1
            elapsed = time.perf_counter() - t_start
            imgs_done = done_batches * 64
            rate = imgs_done / max(0.1, elapsed)
            rem_s = (total_batches - done_batches) * 64 / max(0.1, rate)
            avg_loss = running_loss / done_batches
            print(
                f"  Batch [{done_batches:4d}/{total_batches}] "
                f"Loss: {avg_loss:.4f} | "
                f"Speed: {rate:4.1f} img/s | "
                f"Progress: {done_batches/total_batches*100:5.1f}% | "
                f"ETA: {rem_s/60:.1f}m",
                flush=True
            )

    train_time = time.perf_counter() - t_start
    print(f"\nCalibration training loop completed in {train_time/60:.1f} minutes!", flush=True)

    print(f"Evaluating post-calibration on {len(val_ds):,} validation images...", flush=True)
    val_loss, val_metrics = evaluate(model, val_loader, device, use_amp)
    print("=" * 68)
    print("POST-CALIBRATION RESULTS:")
    print(f"  Validation Loss    : {val_loss:.4f}")
    print(f"  Accuracy           : {val_metrics['accuracy'] * 100:.2f}%")
    print(f"  Recall (Fake Det.) : {val_metrics['recall'] * 100:.2f}%")
    print(f"  AUC-ROC            : {val_metrics['auc_roc']:.4f}")
    print(f"  EER                : {val_metrics['eer']:.4f}")
    print("=" * 68, flush=True)

    # Save updated checkpoint
    print(f"Saving updated checkpoint to {ckpt_path}...", flush=True)
    save_payload = {
        "state_dict": model.state_dict(),
        "version": "image-detector-v2.2.0-b4-calibrated",
        "val_accuracy": float(val_metrics["accuracy"]),
        "val_auc": float(val_metrics["auc_roc"]),
        "val_eer": float(val_metrics["eer"]),
        "backbone": "efficientnet_b4",
        "input_size": 224,
        "extra_metadata": {
            "dataset": "multi-platform-55k-calibrated",
            "samples": len(train_items),
            "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    torch.save(save_payload, ckpt_path)

    summary_path = ckpt_path.with_name("image_detector.summary.json")
    summary_data = {
        "best_val_loss": float(val_loss),
        "best_val_metrics": val_metrics,
        "checkpoint": str(ckpt_path),
        "model_version": "image-detector-v2.2.0-b4-calibrated",
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "backbone": "efficientnet_b4",
        "input_size": 224,
        "calibration_samples": len(train_items),
        "validation_samples": len(val_items),
    }
    summary_path.write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")
    print(f"Successfully saved updated checkpoint and summary!")


if __name__ == "__main__":
    main()
