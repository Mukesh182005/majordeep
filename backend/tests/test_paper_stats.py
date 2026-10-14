"""Statistics used for the paper, checked against known answers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.metrics import roc_auc  # noqa: E402
from ml.evaluation.stats import (  # noqa: E402
    bootstrap_auc_ci,
    delong_covariance,
    delong_test,
    expected_calibration_error,
    mcnemar_test,
    rate_with_ci,
    wilson_interval,
)

LABELS = np.r_[np.zeros(40), np.ones(60)].astype(int)


class TestAUC:
    def test_perfect_separation_is_one(self):
        scores = np.r_[np.linspace(0, 0.4, 40), np.linspace(0.6, 1, 60)]
        assert roc_auc(LABELS, scores) == pytest.approx(1.0)
        ci = bootstrap_auc_ci(LABELS, scores, n_resamples=200)
        assert ci["auc"] == pytest.approx(1.0) and ci["ci95"] == pytest.approx([1.0, 1.0])

    def test_reversed_scores_are_zero(self):
        scores = np.r_[np.linspace(0.6, 1, 40), np.linspace(0, 0.4, 60)]
        assert roc_auc(LABELS, scores) == pytest.approx(0.0)

    def test_bootstrap_is_reproducible_and_brackets_the_estimate(self):
        rng = np.random.default_rng(0)
        scores = np.r_[rng.normal(0, 1, 40), rng.normal(1, 1, 60)]
        first, second = bootstrap_auc_ci(LABELS, scores, seed=3), bootstrap_auc_ci(LABELS, scores, seed=3)
        assert first == second
        assert first["ci95"][0] <= first["auc"] <= first["ci95"][1]


class TestDeLong:
    def test_identical_columns_give_p_one(self):
        rng = np.random.default_rng(1)
        scores = np.r_[rng.normal(0, 1, 40), rng.normal(1, 1, 60)]
        result = delong_test(LABELS, scores, scores)
        assert result["p_value"] == 1.0 and result["difference"] == 0.0

    def test_auc_matches_trapezoid_auc_with_ties(self):
        rng = np.random.default_rng(2)
        scores = np.round(np.r_[rng.normal(0, 1, 40), rng.normal(0.8, 1, 60)], 1)
        aucs, _ = delong_covariance(LABELS, scores)
        assert aucs[0] == pytest.approx(roc_auc(LABELS, scores))

    def test_detects_a_clear_difference(self):
        rng = np.random.default_rng(4)
        labels = np.r_[np.zeros(300), np.ones(300)].astype(int)
        good = np.r_[rng.normal(0, 1, 300), rng.normal(2, 1, 300)]
        weak = good + rng.normal(0, 3, 600)
        assert delong_test(labels, good, weak)["p_value"] < 0.001


class TestWilson:
    def test_hand_computed_half(self):
        # 5/10: centre 0.5, half-width 1.96 * sqrt(0.025 + 1.96^2/400) / (1 + 1.96^2/10)
        low, high = wilson_interval(5, 10)
        assert low == pytest.approx(0.2366, abs=1e-4) and high == pytest.approx(0.7634, abs=1e-4)

    def test_zero_successes(self):
        low, high = wilson_interval(0, 10)
        assert low == 0.0 and high == pytest.approx(0.2775, abs=1e-4)

    def test_rate_with_ci(self):
        result = rate_with_ci([True, False, True, True])
        assert (result["k"], result["n"], result["rate"]) == (3, 4, 0.75)


class TestCalibration:
    def test_perfectly_calibrated_bins_give_zero(self):
        probs = np.r_[np.full(10, 0.1), np.full(10, 0.9)]
        labels = np.r_[np.r_[np.ones(1), np.zeros(9)], np.r_[np.ones(9), np.zeros(1)]]
        assert expected_calibration_error(labels, probs)["ece"] == pytest.approx(0.0, abs=1e-12)

    def test_overconfident_model(self):
        probs = np.full(10, 0.95)
        labels = np.r_[np.ones(5), np.zeros(5)]
        result = expected_calibration_error(labels, probs, n_bins=15)
        assert result["ece"] == pytest.approx(0.45)
        assert sum(b["count"] for b in result["bins"]) == 10

    def test_probability_one_lands_in_the_last_bin(self):
        result = expected_calibration_error([1, 1], [1.0, 1.0], n_bins=15)
        assert result["bins"][-1]["count"] == 2


def test_mcnemar():
    same = mcnemar_test([True, False, True], [True, False, True])
    assert same["p_value"] == 1.0
    a = np.r_[np.ones(20, bool), np.zeros(5, bool)]
    b = np.r_[np.zeros(20, bool), np.ones(5, bool)]
    result = mcnemar_test(a, b)
    assert (result["only_a_correct"], result["only_b_correct"]) == (20, 5) and result["p_value"] < 0.01
