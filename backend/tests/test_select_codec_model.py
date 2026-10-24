"""ml/evaluation/select_codec_model.py: pooled EER and the plan's choice and replacement rules."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation import select_codec_model as scm  # noqa: E402


def test_pooled_eer_counts_every_split_as_trials():
    clean = [np.array([-2.0, -1.0, 1.0, 2.0])]
    labels = [np.array([0, 0, 1, 1])]
    assert scm.pooled_eer(clean, labels)[0] == 0.0
    # A second split where bona fide scores look spoofed raises the pooled EER.
    noisy = clean + [np.array([1.5, 1.5, 1.0, 2.0])]
    assert scm.pooled_eer(noisy, labels + [np.array([0, 0, 1, 1])])[0] > 0.0


def test_lowest_pooled_eer_is_served_and_replaces_only_if_better():
    decision = scm.choose({0: 0.02, 1: 0.015, 2: 0.015}, current=0.05)
    assert decision["served_seed"] == 1 and decision["replaces_current"] is True
    assert scm.choose({0: 0.06, 1: 0.07, 2: 0.08}, current=0.05)["replaces_current"] is False
    assert scm.choose({0: 0.05, 1: 0.07, 2: 0.08}, current=0.05)["replaces_current"] is False
