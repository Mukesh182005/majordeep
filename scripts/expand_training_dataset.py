#!/usr/bin/env python3
"""Build the image-detector training manifest without train/validation leakage.

Sources:
1. faces-140k (real FFHQ faces vs StyleGAN faces). Its own train / valid / test
   folders are kept as train / val / test; the test folder stays held out.
2. Derived sets (``massive_social``, ``expansion_300k``): re-encoded, filtered
   copies of faces-140k *training* images. A copy carries its source's
   content, so a copy in validation whose source is in training measures
   memorisation, not detection (the previous split put 144,000 such copies in
   validation and reported 99.98% accuracy after one epoch). Derived images
   are therefore training-only.
3. ``--extra`` CSV files (``path,label[,group]``) for independently labelled
   data — e.g. real photos and images from current generators. They are split
   70/15/15 by ``group`` so related images never straddle splits.

Unlabelled uploads are never added. The previous version appended every file
in ``backend/storage/uploads`` (and a local IDE folder) with label 1 = fake,
teaching the model that users' own real photos were AI.

Note: the derived "diffusion" and "inpaint" classes are not diffusion output —
they are PIL blur / patch filters applied to StyleGAN faces (see
``generate_massive_social_dataset.py``). Detecting current generators needs
real generated images, supplied through ``--extra``.

Usage (from the repo root):
    python scripts/expand_training_dataset.py
    python scripts/expand_training_dataset.py --extra data/labelled/modern_ai.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"
FACES_140K = RAW_ROOT / "faces-140k" / "real_vs_fake" / "real-vs-fake"
DERIVED_ROOTS = (RAW_ROOT / "massive_social", RAW_ROOT / "expansion_300k")
DEFAULT_MANIFEST = REPO_ROOT / "data" / "processed" / "faces" / "manifest.csv"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
FACES_SPLITS = {"train": "train", "valid": "val", "test": "test"}
LABELS = {"real": 0, "fake": 1}


def group_split(group: str, val: float = 0.15, test: float = 0.15) -> str:
    """Deterministic split from a group key, so a group always lands in one split."""
    bucket = int(hashlib.sha1(group.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if bucket < val:
        return "val"
    if bucket < val + test:
        return "test"
    return "train"


def _images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT)


def _derived_label(folder_name: str) -> int | None:
    name = folder_name.lower()
    if name.endswith("_fake"):
        return 1
    if name.endswith("_real"):
        return 0
    return None


def faces_140k_rows() -> list[dict]:
    rows = []
    for folder_split, split in FACES_SPLITS.items():
        for class_name, label in LABELS.items():
            folder = FACES_140K / folder_split / class_name
            if not folder.exists():
                continue
            files = _images(folder)
            print(f"  faces-140k {folder_split}/{class_name}: {len(files):,} -> {split}")
            rows += [{"path": str(p), "label": label, "group": f"faces140k_{p.stem}", "split": split} for p in files]
    return rows


def derived_rows() -> list[dict]:
    rows = []
    for root in DERIVED_ROOTS:
        if not root.exists():
            continue
        for folder in sorted(d for d in root.iterdir() if d.is_dir()):
            label = _derived_label(folder.name)
            if label is None:
                print(f"  skipping {root.name}/{folder.name}: name does not end in _real/_fake")
                continue
            files = _images(folder)
            print(f"  {root.name}/{folder.name}: {len(files):,} -> train only (derived from faces-140k train)")
            rows += [
                {"path": str(p), "label": label, "group": f"{root.name}_{folder.name}_{p.stem}", "split": "train"}
                for p in files
            ]
    return rows


def extra_rows(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for line_no, record in enumerate(csv.DictReader(fh), start=2):
            path = Path(record["path"])
            if not path.is_absolute():
                path = (csv_path.parent / path).resolve()
            label = int(record["label"])
            if label not in (0, 1):
                raise SystemExit(f"{csv_path}:{line_no}: label must be 0 (real) or 1 (fake), got {label}")
            group = record.get("group") or path.stem
            rows.append({"path": str(path), "label": label, "group": f"extra_{group}", "split": group_split(group)})
    print(f"  {csv_path.name}: {len(rows):,} labelled images (split by group)")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--extra", type=Path, action="append", default=[], help="CSV with path,label[,group]")
    parser.add_argument("--no-derived", action="store_true", help="exclude massive_social / expansion_300k")
    args = parser.parse_args()

    print("Indexing sources...")
    rows = faces_140k_rows()
    if not args.no_derived:
        rows += derived_rows()
    for csv_path in args.extra:
        rows += extra_rows(csv_path)
    if not rows:
        raise SystemExit(f"No images found under {RAW_ROOT}.")

    # Guard: no group may appear in more than one split.
    splits_by_group: dict[str, set[str]] = {}
    for row in rows:
        splits_by_group.setdefault(row["group"], set()).add(row["split"])
    leaking = [g for g, s in splits_by_group.items() if len(s) > 1]
    if leaking:
        raise SystemExit(f"{len(leaking)} groups span several splits, e.g. {leaking[:3]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "label", "group", "split"])
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter((r["split"], r["label"]) for r in rows)
    print(f"\nWrote {len(rows):,} rows to {args.output}")
    for split in ("train", "val", "test"):
        print(f"  {split:5s}: real {counts[(split, 0)]:,} | fake {counts[(split, 1)]:,}")
    if not args.extra:
        print(
            "\nWARNING: every 'fake' here is a StyleGAN face or a filtered copy of one. A model "
            "trained on this manifest detects StyleGAN faces, not current generators; pass "
            "--extra with real photos and genuine diffusion / GPT / Gemini images for that."
        )


if __name__ == "__main__":
    main()
