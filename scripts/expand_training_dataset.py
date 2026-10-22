#!/usr/bin/env python3
"""Build the image-detector training manifest without train/validation leakage.

Sources:
1. faces-140k (real FFHQ faces vs StyleGAN faces). Its own train / valid / test
   folders are kept as train / val / test; the test folder stays held out.
   Each image is its own group, ``faces140k_<class>_<stem>``.
2. ``massive_social``: filtered copies made by
   ``scripts/generate_massive_social_dataset.py``. File ``<folder>_<i>.jpg`` in
   ``<platform>_<class>`` is a copy of the ``i mod n``-th image of the sorted
   faces-140k ``train/<class>`` folder. Every copy therefore carries its
   source's group and is placed in its source's split, so a copy can never sit
   in a different split from the face it was made from. (The previous version
   split copies at random, 85/15 per folder, and put 144,000 of them in
   validation: a 99.98% accuracy after one epoch measured memorisation.)
   Exception: the ``inpaint_fake`` files on disk were made from either class
   (in a 300-file sample, 274 are copies of the train/real image at that index
   and 26 of the train/fake image), so each one is matched to the candidate it
   is a copy of by comparing pixels outside the blurred patch.
3. ``expansion_300k``: derived images with no generator script in the
   repository, so their source images cannot be established. Excluded unless
   ``--include-unverified-derived`` is given, in which case they are
   training-only and a warning is printed.
4. ``--extra`` CSV files (``path,label[,group]``) for independently labelled
   data, e.g. real photos and images from current generators. They are split
   70/15/15 by group with ``split_by_group`` (stratified by label), so related
   images never straddle splits.

Nothing under an uploads folder is ever added. The previous version appended
every file in ``backend/storage/uploads`` (and a local IDE upload folder) with
label 1 = fake, teaching the model that users' own real photos were AI.

Note: the derived "diffusion" and "inpaint" classes are not diffusion output;
they are PIL blur / patch filters applied to StyleGAN faces (see
``generate_massive_social_dataset.py``). Detecting current generators needs
real generated images, supplied through ``--extra``.

Usage (from the repo root):
    python scripts/expand_training_dataset.py
    python scripts/expand_training_dataset.py --no-derived
    python scripts/expand_training_dataset.py --extra data/labelled/modern_ai.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ml.common import split_by_group  # noqa: E402

DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "processed" / "faces" / "manifest.csv"
FACES_140K = Path("faces-140k") / "real_vs_fake" / "real-vs-fake"
SOURCED_DERIVED = "massive_social"
UNVERIFIED_DERIVED = ("expansion_300k",)
UPLOAD_FOLDER_NAMES = {"uploads", ".user_uploaded"}
MIXED_SOURCE_FOLDERS = {"inpaint_fake"}
COPY_MATCH_MAX_MAE = 5.0  # grey levels; measured copies <= 0.4, other faces >= 15.8

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
FACES_SPLITS = {"train": "train", "valid": "val", "test": "test"}
LABELS = {"real": 0, "fake": 1}


class LeakageError(ValueError):
    """The manifest would let the same content, or an upload, reach two splits."""


def _images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT)


def _derived_label(folder_name: str) -> int | None:
    name = folder_name.lower()
    if name.endswith("_fake"):
        return 1
    if name.endswith("_real"):
        return 0
    return None


def faces_group(class_name: str, stem: str) -> str:
    return f"faces140k_{class_name}_{stem}"


def faces_140k_rows(raw_root: Path) -> list[dict]:
    rows = []
    for folder_split, split in FACES_SPLITS.items():
        for class_name, label in LABELS.items():
            folder = raw_root / FACES_140K / folder_split / class_name
            if not folder.exists():
                continue
            files = _images(folder)
            print(f"  faces-140k {folder_split}/{class_name}: {len(files):,} -> {split}")
            rows += [
                {"path": str(p), "label": label, "group": faces_group(class_name, p.stem), "split": split}
                for p in files
            ]
    return rows


def _border_thumbnail(path: Path, size: int = 32) -> np.ndarray:
    """Grayscale thumbnail without the central box that encode_inpaint_fake may blur."""
    with Image.open(path) as im:
        pixels = np.asarray(im.convert("L").resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32)
    mask = np.ones((size, size), dtype=bool)
    mask[int(size * 0.375 - 2):int(size * 0.625 + 2) + 1, int(size * 0.325 - 2):int(size * 0.675 + 2) + 1] = False
    return pixels[mask]


def _copied_class(copy: Path, candidates: dict[str, Path]) -> str:
    """The class whose candidate source the copy was made from."""
    thumb = _border_thumbnail(copy)
    mae = {cls: float(np.abs(_border_thumbnail(src) - thumb).mean()) for cls, src in candidates.items()}
    best = min(mae, key=lambda cls: mae[cls])
    if mae[best] > COPY_MATCH_MAX_MAE:
        raise SystemExit(f"{copy}: not a copy of any candidate source {mae}")
    return best


def massive_social_rows(raw_root: Path, split_of_group: dict[str, str]) -> list[dict]:
    """Copies from generate_massive_social_dataset.py, each grouped with its source face."""
    root = raw_root / SOURCED_DERIVED
    if not root.exists():
        return []
    # Same source lists as the generator: sorted(SRC.glob("*.jpg")) over faces-140k train/<class>.
    sources = {cls: sorted((raw_root / FACES_140K / "train" / cls).glob("*.jpg")) for cls in LABELS}
    rows = []
    for folder in sorted(d for d in root.iterdir() if d.is_dir()):
        label = _derived_label(folder.name)
        if label is None:
            print(f"  skipping {root.name}/{folder.name}: name does not end in _real/_fake")
            continue
        classes = tuple(LABELS) if folder.name in MIXED_SOURCE_FOLDERS else ("fake" if label == 1 else "real",)
        for cls in classes:
            if not sources[cls]:
                raise SystemExit(f"{root.name}/{folder.name}: faces-140k train/{cls} is needed to find sources")
        pattern = re.compile(rf"^{re.escape(folder.name)}_(\d+)$")
        files = _images(folder)
        source_classes = Counter()
        for p in files:
            match = pattern.match(p.stem)
            if not match:
                raise SystemExit(f"{p}: name does not follow <folder>_<index>; its source cannot be found")
            index = int(match.group(1))
            candidates = {cls: sources[cls][index % len(sources[cls])] for cls in classes}
            cls = classes[0] if len(classes) == 1 else _copied_class(p, candidates)
            source_classes[cls] += 1
            group = faces_group(cls, candidates[cls].stem)
            if group not in split_of_group:
                raise SystemExit(f"{p}: source {group} is not in the faces-140k rows")
            rows.append({"path": str(p), "label": label, "group": group, "split": split_of_group[group]})
        per_split = Counter(r["split"] for r in rows[-len(files):]) if files else Counter()
        print(f"  {root.name}/{folder.name}: {len(files):,} -> split of source face {dict(per_split)}, "
              f"source class {dict(source_classes)}")
    return rows


def unverified_derived_rows(raw_root: Path) -> list[dict]:
    rows = []
    for name in UNVERIFIED_DERIVED:
        root = raw_root / name
        if not root.exists():
            continue
        for folder in sorted(d for d in root.iterdir() if d.is_dir()):
            label = _derived_label(folder.name)
            if label is None:
                print(f"  skipping {root.name}/{folder.name}: name does not end in _real/_fake")
                continue
            files = _images(folder)
            print(f"  WARNING {root.name}/{folder.name}: {len(files):,} -> train only, source images unknown")
            rows += [
                {"path": str(p), "label": label, "group": f"{root.name}_{folder.name}_{p.stem}", "split": "train"}
                for p in files
            ]
    return rows


def extra_rows(csv_path: Path, seed: int = 42) -> list[dict]:
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for line_no, record in enumerate(csv.DictReader(fh), start=2):
            path = Path(record["path"])
            if not path.is_absolute():
                path = (csv_path.parent / path).resolve()
            label = int(record["label"])
            if label not in (0, 1):
                raise SystemExit(f"{csv_path}:{line_no}: label must be 0 (real) or 1 (fake), got {label}")
            group = f"extra_{record.get('group') or path.stem}"
            rows.append({"path": str(path), "label": label, "group": group, "split": ""})
    assignment = split_by_group([r["group"] for r in rows], seed=seed, labels=[r["label"] for r in rows])
    for row in rows:
        row["split"] = assignment[row["group"]]
    print(f"  {csv_path.name}: {len(rows):,} labelled images (split by group)")
    return rows


def check_rows(rows: list[dict]) -> None:
    """Raise LeakageError if a group or file spans splits, or if any upload is present."""
    uploads = [r["path"] for r in rows
               if UPLOAD_FOLDER_NAMES & {part.lower() for part in Path(r["path"]).parts[:-1]}]
    if uploads:
        raise LeakageError(f"{len(uploads)} files come from an uploads folder, e.g. {uploads[:3]}")
    for key in ("group", "path"):
        splits: dict[str, set[str]] = {}
        for row in rows:
            splits.setdefault(row[key], set()).add(row["split"])
        leaking = [k for k, s in splits.items() if len(s) > 1]
        if leaking:
            raise LeakageError(f"{len(leaking)} {key}s span several splits, e.g. {leaking[:3]}")


def build_rows(raw_root: Path, extras: list[Path], derived: bool = True,
               include_unverified: bool = False, seed: int = 42) -> list[dict]:
    rows = faces_140k_rows(raw_root)
    if derived:
        rows += massive_social_rows(raw_root, {r["group"]: r["split"] for r in rows})
        if include_unverified:
            rows += unverified_derived_rows(raw_root)
    for csv_path in extras:
        rows += extra_rows(csv_path, seed)
    check_rows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT,
                        help="folder holding faces-140k/, massive_social/ (default: data/raw)")
    parser.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--extra", type=Path, action="append", default=[], help="CSV with path,label[,group]")
    parser.add_argument("--no-derived", action="store_true", help="exclude every derived set")
    parser.add_argument("--include-unverified-derived", action="store_true",
                        help=f"add {', '.join(UNVERIFIED_DERIVED)} (training only; source images unknown)")
    parser.add_argument("--seed", type=int, default=42, help="seed for splitting --extra groups")
    args = parser.parse_args()

    print("Indexing sources...")
    try:
        rows = build_rows(args.raw_root, args.extra, derived=not args.no_derived,
                          include_unverified=args.include_unverified_derived, seed=args.seed)
    except LeakageError as exc:
        raise SystemExit(f"Refusing to write the manifest: {exc}") from exc
    if not rows:
        raise SystemExit(f"No images found under {args.raw_root}.")

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
