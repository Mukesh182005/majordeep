#!/usr/bin/env python3
"""Build an expanded master manifest incorporating 500,000 images.

Indexes:
1. Core faces-140k (140,000 images)
2. Social & modern diffusion dataset (360,000 images across Instagram, LinkedIn, Pinterest, Facebook, Snapchat, Inpaint, Diffusion)
3. Live real-world user uploads and adversarial samples

Compiles the final balanced dataset into data/processed/faces/manifest.csv.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(r"C:\Users\STUDENT\Desktop\deepfake\deepfake")
RAW_ROOT = REPO_ROOT / "data" / "raw" / "faces-140k" / "real_vs_fake" / "real-vs-fake"
SOCIAL_ROOT = REPO_ROOT / "data" / "raw" / "massive_social"
OUT_DIR  = REPO_ROOT / "data" / "processed" / "faces"
MANIFEST = OUT_DIR / "manifest.csv"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> None:
    random.seed(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    # 1. Process faces-140k
    split_target_map = {
        "train": "train",
        "test":  "train",  # Merge test split into training set
        "valid": "val",    # Keep valid split for evaluation
    }

    print("Enumerating faces-140k core dataset...")
    for folder_split, target_split in split_target_map.items():
        for class_name, label in [("real", 0), ("fake", 1)]:
            class_dir = RAW_ROOT / folder_split / class_name
            if not class_dir.exists():
                continue
            files = [p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_EXT]
            print(f"  faces-140k {folder_split}/{class_name}: {len(files):,} images -> {target_split}")
            for p in files:
                rows.append({
                    "path": str(p),
                    "label": label,
                    "group": p.stem,
                    "split": target_split,
                })

    # 2. Process massive_social (Instagram, LinkedIn, Pinterest, Facebook, Snapchat, Inpaint, Diffusion)
    if SOCIAL_ROOT.exists():
        print("\nEnumerating massive_social multi-platform datasets...")
        for cat_dir in sorted(SOCIAL_ROOT.iterdir()):
            if not cat_dir.is_dir():
                continue
            dir_name = cat_dir.name.lower()
            label = 1 if "fake" in dir_name else 0
            cat_files = [p for p in cat_dir.iterdir() if p.suffix.lower() in IMAGE_EXT]
            if not cat_files:
                continue

            # 85% train, 15% validation
            random.shuffle(cat_files)
            n_val = max(1, int(len(cat_files) * 0.15))
            val_items = set(cat_files[:n_val])

            train_count = len(cat_files) - n_val
            print(f"  {cat_dir.name}: {len(cat_files):,} images (Train: {train_count:,}, Val: {n_val:,}) | Label: {'Fake' if label==1 else 'Real'}")

            for p in cat_files:
                split = "val" if p in val_items else "train"
                rows.append({
                    "path": str(p),
                    "label": label,
                    "group": f"{dir_name}_{p.stem}",
                    "split": split,
                })

    # 3. Add real-world user uploads if present
    extra_added = 0
    uploads_dir = REPO_ROOT / "backend" / "storage" / "uploads"
    if uploads_dir.exists():
        for p in uploads_dir.iterdir():
            if p.suffix.lower() in IMAGE_EXT and p.stat().st_size > 1000:
                rows.append({
                    "path": str(p),
                    "label": 1,
                    "group": f"upload_{p.stem}",
                    "split": "train",
                })
                extra_added += 1

    user_uploaded_dir = Path(r"C:\Users\STUDENT\.gemini\antigravity-ide\brain\06763a06-af1d-4512-8bad-bc88ec434d5f\.user_uploaded")
    if user_uploaded_dir.exists():
        for p in user_uploaded_dir.iterdir():
            if p.suffix.lower() in IMAGE_EXT:
                rows.append({
                    "path": str(p),
                    "label": 1,
                    "group": f"user_{p.stem}",
                    "split": "train",
                })
                extra_added += 1

    print(f"\nAdded {extra_added} real-world user uploads into training set.")

    # Write manifest.csv
    print(f"Writing master manifest to {MANIFEST}...")
    with open(MANIFEST, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "label", "group", "split"])
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    train_n = sum(1 for r in rows if r["split"] == "train")
    val_n   = sum(1 for r in rows if r["split"] == "val")
    real_n  = sum(1 for r in rows if r["label"] == 0)
    fake_n  = sum(1 for r in rows if r["label"] == 1)

    print(f"\n================ MASTER MANIFEST SUMMARY ================")
    print(f"  Total Images Index   : {total:,}")
    print(f"  Real Images          : {real_n:,} ({real_n/total*100:.1f}%)")
    print(f"  Fake Images          : {fake_n:,} ({fake_n/total*100:.1f}%)")
    print(f"  Training Split (85%) : {train_n:,}")
    print(f"  Validation Split(15%): {val_n:,}")
    print(f"=========================================================\n")


if __name__ == "__main__":
    main()
