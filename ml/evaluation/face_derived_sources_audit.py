#!/usr/bin/env python3
"""Audit which faces-140k images the massive_social copies were made from (Phase 8).

``scripts/expand_training_dataset.py`` places each copy in its source face's
split. This script checks that the source rule holds on the files on disk:

* every folder except ``inpaint_fake``: for a random sample of copies (seed 0),
  the perceptual-hash distance (pHash, 64 bits) between the copy and its
  index-mapped source, against the distance to an unrelated face;
* ``inpaint_fake``, whose blurred patch disturbs the hash: every file is matched
  to the train/real or train/fake image at its index by comparing pixels
  outside the patch area (the builder's own rule), and the split of the matched
  source is recorded.

Writes ``paper_results/face_manifest_audit/derived_sources.json`` with provenance.

Usage (PowerShell, from the repository root)::

    python ml/evaluation/face_derived_sources_audit.py
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from ml.common import REPO_ROOT  # noqa: E402

OUT_DIR = REPO_ROOT / "paper_results/face_manifest_audit"
MATCH_BITS = 10


def _phash(path: Path) -> int:
    import imagehash
    from PIL import Image

    with Image.open(path) as im:
        return int(str(imagehash.phash(im.convert("RGB"))), 16)


def main() -> int:
    from expand_training_dataset import (
        DEFAULT_RAW_ROOT,
        FACES_140K,
        MIXED_SOURCE_FOLDERS,
        SOURCED_DERIVED,
        _copied_class,
        _derived_label,
        _images,
    )

    from ml.provenance import collect_provenance

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--per-folder", type=int, default=150)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    faces = args.raw_root / FACES_140K
    sources = {cls: sorted((faces / "train" / cls).glob("*.jpg")) for cls in ("real", "fake")}
    rng = random.Random(args.seed)
    folders = {}
    for folder in sorted(d for d in (args.raw_root / SOURCED_DERIVED).iterdir() if d.is_dir()):
        label = _derived_label(folder.name)
        if label is None:
            continue
        files = _images(folder)
        pattern = re.compile(rf"^{re.escape(folder.name)}_(\d+)$")
        index = {p: int(pattern.match(p.stem).group(1)) for p in files}
        if folder.name in MIXED_SOURCE_FOLDERS:
            classes = Counter()
            for k, p in enumerate(files, start=1):
                i = index[p]
                classes[_copied_class(p, {c: sources[c][i % len(sources[c])] for c in sources})] += 1
                if k % 5000 == 0:
                    print(f"  {folder.name}: {k:,}/{len(files):,}", flush=True)
            folders[folder.name] = {
                "files": len(files), "label": label, "method": "pixels outside the patch area, every file",
                "source_class": dict(classes), "source_split": {"train": len(files)},
            }
        else:
            cls = "fake" if label == 1 else "real"
            sample = sorted(rng.sample(files, min(args.per_folder, len(files))))
            mapped = np.array([bin(_phash(p) ^ _phash(sources[cls][index[p] % len(sources[cls])])).count("1")
                               for p in sample])
            unrelated = np.array([bin(_phash(p) ^ _phash(sources[cls][(index[p] + 7) % len(sources[cls])])).count("1")
                                  for p in sample])
            folders[folder.name] = {
                "files": len(files), "label": label, "method": f"pHash on a random sample of {len(sample)}",
                "sampled": len(sample), "mapped_source_within_bits": int((mapped <= MATCH_BITS).sum()),
                "mapped_distance_max": int(mapped.max()), "unrelated_distance_min": int(unrelated.min()),
                "source_class": {cls: len(files)}, "source_split": {"train": len(files)},
            }
        print(folder.name, json.dumps(folders[folder.name]), flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "purpose": "Phase 8: source images of the massive_social copies",
        "match_bits": MATCH_BITS,
        "source_rule": "copy <folder>_<i> is made from sorted(faces-140k train/<class>)[i mod n]",
        "total_copies": sum(f["files"] for f in folders.values()),
        "folders": folders,
        "provenance": collect_provenance(seeds=args.seed),
    }
    (OUT_DIR / "derived_sources.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {(OUT_DIR / 'derived_sources.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
