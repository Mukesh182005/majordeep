#!/usr/bin/env python3
"""Deprecated: use ``python scripts/expand_training_dataset.py --no-derived``.

This script listed the faces-140k train / valid / test folders as train / val /
test and added nothing else, so it did not leak. The leak behind the
164,000-image validation set was in the old ``expand_training_dataset.py``
(see KNOWN_ISSUES.md). Kept so that old commands still work: it now runs the
checked builder, which produces the same splits and refuses any manifest in
which a group spans two splits or an upload appears.

Usage (from the repo root):
    python scripts/build_manifest_140k.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from expand_training_dataset import main  # noqa: E402

if __name__ == "__main__":
    print("build_manifest_140k.py is deprecated; running expand_training_dataset.py --no-derived")
    sys.argv = [sys.argv[0], "--no-derived", *sys.argv[1:]]
    main()
