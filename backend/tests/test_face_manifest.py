"""Group-safe face manifest (Phase 8): no shared content across splits, no uploads."""

from __future__ import annotations

import csv
import shutil
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from expand_training_dataset import FACES_140K, LeakageError, build_rows, check_rows  # noqa: E402

# inpaint_fake copy index -> class of the source it is copied from (index mod 4 picks the image).
INPAINT_SOURCES = {0: "real", 1: "fake", 2: "real", 3: "real", 4: "fake", 5: "real"}


def _touch(path: Path) -> Path:
    """A distinct 64x64 JPEG: a random 4x4 colour grid, seeded by the file name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(zlib.crc32(path.name.encode()))
    grid = rng.integers(0, 256, size=(4, 4, 3), dtype=np.uint8)
    Image.fromarray(grid).resize((64, 64), Image.Resampling.NEAREST).save(path, quality=95)
    return path


@pytest.fixture()
def raw_root(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    faces = raw / FACES_140K
    for split, n in (("train", 4), ("valid", 2), ("test", 2)):
        for cls in ("real", "fake"):
            for i in range(n):
                _touch(faces / split / cls / f"{split}_{cls}_{i}.jpg")
    # Copies as generate_massive_social_dataset.py names them; 6 > 4 sources, so sources repeat.
    for folder in ("instagram_real", "instagram_fake", "diffusion_fake"):
        for i in range(6):
            _touch(raw / "massive_social" / folder / f"{folder}_{i:06d}.jpg")
    inpaint = raw / "massive_social" / "inpaint_fake"
    inpaint.mkdir(parents=True)
    for i, cls in INPAINT_SOURCES.items():
        shutil.copy(faces / "train" / cls / f"train_{cls}_{i % 4}.jpg", inpaint / f"inpaint_fake_{i:06d}.jpg")
    _touch(raw / "expansion_300k" / "mobile_real" / "mobile_real_000000.jpg")
    return raw


def _split_of(rows: list[dict]) -> dict[str, str]:
    return {r["path"]: r["split"] for r in rows}


def test_official_splits_kept_and_test_never_in_training(raw_root):
    rows = build_rows(raw_root, [])
    faces = [r for r in rows if "faces-140k" in r["path"]]
    for row in faces:
        folder_split = Path(row["path"]).parent.parent.name
        assert row["split"] == {"train": "train", "valid": "val", "test": "test"}[folder_split]
    test_groups = {r["group"] for r in rows if r["split"] == "test"}
    assert test_groups and not test_groups & {r["group"] for r in rows if r["split"] != "test"}


def test_copies_carry_their_source_group_and_split(raw_root):
    rows = build_rows(raw_root, [])
    copies = [r for r in rows if "massive_social" in r["path"]]
    assert len(copies) == 24
    by_group = {r["group"]: r for r in rows if "faces-140k" in r["path"]}
    for copy in copies:
        source = by_group[copy["group"]]
        assert copy["split"] == source["split"] == "train"
        if "inpaint_fake" not in copy["path"]:
            assert copy["label"] == source["label"]
    # Copy 4 of instagram_real is made from the first sorted train/real image (4 mod 4 = 0).
    copy4 = next(r for r in copies if r["path"].endswith("instagram_real_000004.jpg"))
    assert copy4["group"] == "faces140k_real_train_real_0"


def test_inpaint_copies_matched_to_the_class_they_were_copied_from(raw_root):
    rows = [r for r in build_rows(raw_root, []) if "inpaint_fake" in r["path"]]
    groups = {Path(r["path"]).stem: r["group"] for r in rows}
    for i, cls in INPAINT_SOURCES.items():
        assert groups[f"inpaint_fake_{i:06d}"] == f"faces140k_{cls}_train_{cls}_{i % 4}"
    assert all(r["label"] == 1 for r in rows)


def test_inpaint_copy_without_a_source_is_refused(raw_root):
    _touch(raw_root / "massive_social" / "inpaint_fake" / "inpaint_fake_000099.jpg")
    with pytest.raises(SystemExit, match="not a copy"):
        build_rows(raw_root, [])


def test_no_group_or_file_in_two_splits(raw_root):
    rows = build_rows(raw_root, [], include_unverified=True)
    splits: dict[str, set[str]] = {}
    for row in rows:
        splits.setdefault(row["group"], set()).add(row["split"])
    assert all(len(s) == 1 for s in splits.values())


def test_unverified_derived_excluded_by_default(raw_root):
    assert not any("expansion_300k" in r["path"] for r in build_rows(raw_root, []))
    included = [r for r in build_rows(raw_root, [], include_unverified=True) if "expansion_300k" in r["path"]]
    assert len(included) == 1 and included[0]["split"] == "train"


def test_extra_rows_split_by_group(raw_root, tmp_path):
    extra = tmp_path / "extra.csv"
    with extra.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["path", "label", "group"])
        for g in range(20):
            for k in range(3):
                writer.writerow([str(_touch(tmp_path / "labelled" / f"g{g}_{k}.jpg")), g % 2, f"scene{g}"])
    rows = [r for r in build_rows(raw_root, [extra]) if r["group"].startswith("extra_")]
    assert len(rows) == 60
    assert {r["split"] for r in rows} == {"train", "val", "test"}


def test_uploads_are_refused(raw_root, tmp_path):
    extra = tmp_path / "extra.csv"
    upload = _touch(tmp_path / "backend" / "storage" / "uploads" / "photo.jpg")
    extra.write_text(f"path,label\n{upload},0\n", encoding="utf-8")
    with pytest.raises(LeakageError, match="uploads"):
        build_rows(raw_root, [extra])


def test_check_rows_catches_leaks():
    with pytest.raises(LeakageError, match="groups span"):
        check_rows([{"path": "a.jpg", "group": "g", "split": "train"},
                    {"path": "b.jpg", "group": "g", "split": "test"}])
    with pytest.raises(LeakageError, match="paths span"):
        check_rows([{"path": "a.jpg", "group": "g1", "split": "train"},
                    {"path": "a.jpg", "group": "g2", "split": "test"}])
    check_rows([{"path": "a.jpg", "group": "g", "split": "train"},
                {"path": "b.jpg", "group": "g", "split": "train"}])
