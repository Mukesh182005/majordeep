"""Balanced dev subsample for the Phase 3 audio-heuristics measurement."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.audio_heuristics_dev import balanced_subsample  # noqa: E402


def _rows():
    rows = [{"utt_id": f"b{i}", "split": "dev", "label": 0, "attack_id": "-"} for i in range(50)]
    for attack in ("A01", "A02", "A03", "A04", "A05", "A06"):
        rows += [{"utt_id": f"{attack}_{i}", "split": "dev", "label": 1, "attack_id": attack} for i in range(30)]
    rows += [{"utt_id": f"t{i}", "split": "train", "label": 0, "attack_id": "-"} for i in range(50)]
    rows += [{"utt_id": f"e{i}", "split": "eval", "label": 1, "attack_id": "A07"} for i in range(50)]
    return rows


def test_counts_spread_and_dev_only():
    chosen = balanced_subsample(_rows(), n_per_class=20, seed=0)
    labels = Counter(r["label"] for r in chosen)
    assert labels == {0: 20, 1: 20}
    per_attack = Counter(r["attack_id"] for r in chosen if r["label"] == 1)
    assert sorted(per_attack.values()) == [3, 3, 3, 3, 4, 4]  # 20 spread over 6 attacks
    assert all(r["split"] == "dev" for r in chosen)
    assert len({r["utt_id"] for r in chosen}) == 40


def test_fixed_seed_is_reproducible_and_seed_matters():
    first = [r["utt_id"] for r in balanced_subsample(_rows(), 20, seed=0)]
    assert first == [r["utt_id"] for r in balanced_subsample(_rows(), 20, seed=0)]
    assert first != [r["utt_id"] for r in balanced_subsample(_rows(), 20, seed=1)]
