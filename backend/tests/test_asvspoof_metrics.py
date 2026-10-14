"""ASVspoof EER and t-DCF, checked against known answers and the official code."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.asvspoof_metrics import (  # noqa: E402
    COST_MODEL_2019,
    det_curve,
    eer,
    evaluate_scores,
    load_asv_scores,
    min_tdcf,
)

# Hand example. Sorted scores: 0.05 s, 0.1 s, 0.2 s, 0.3 b, 0.7 s, 0.8 b, 0.9 b.
# At threshold 0.3: miss = 1/3 (0.3 <= 0.3), false alarm = 1/4 (0.7 > 0.3) -> EER 7/24.
BONA = np.array([0.9, 0.8, 0.3])
SPOOF = np.array([0.7, 0.2, 0.1, 0.05])


class TestEER:
    def test_perfect_separation_gives_zero(self):
        assert eer(np.linspace(1, 2, 50), np.linspace(-2, -1, 500))[0] == 0.0

    def test_identical_distributions_give_about_half(self):
        rng = np.random.default_rng(0)
        value = eer(rng.standard_normal(20000), rng.standard_normal(20000))[0]
        assert value == pytest.approx(0.5, abs=0.02)

    def test_hand_computed_example(self):
        value, threshold = eer(BONA, SPOOF)
        assert value == pytest.approx(7 / 24)
        assert threshold == pytest.approx(0.3)

    def test_det_curve_endpoints(self):
        p_miss, p_fa, thresholds = det_curve(BONA, SPOOF)
        assert (p_miss[0], p_fa[0]) == (0.0, 1.0)
        assert (p_miss[-1], p_fa[-1]) == (1.0, 0.0)
        assert thresholds.size == BONA.size + SPOOF.size + 1


class TestTDCF:
    # ASV: targets high, nontargets low, spoofs accepted. The EER threshold is
    # -1 (a nontarget score), so with ">=" one nontarget of three is accepted.
    TAR, NON, SPOOF_ASV = [5.0, 6.0, 7.0], [-3.0, -2.0, -1.0], [4.0, 5.0, 6.0]

    def test_hand_computed_example(self):
        result = min_tdcf(BONA, SPOOF, self.TAR, self.NON, self.SPOOF_ASV)
        assert result["asv_p_fa"] == pytest.approx(1 / 3)
        assert result["asv_p_miss"] == 0.0 and result["asv_p_miss_spoof"] == 0.0
        assert result["C1"] == pytest.approx(0.9405 - 0.0095 * 10 / 3)
        assert result["C2"] == pytest.approx(0.5)
        # Best threshold 0.2: no bona fide missed, one spoof of four passed -> 0.25.
        assert result["min_tdcf"] == pytest.approx(0.25)
        assert result["cm_threshold"] == pytest.approx(0.2)

    def test_perfect_countermeasure_costs_nothing(self):
        assert min_tdcf([2.0, 3.0, 4.0], [-1.0, -2.0], self.TAR, self.NON, self.SPOOF_ASV)["min_tdcf"] == 0.0

    def test_normalised_cost_never_exceeds_one(self):
        rng = np.random.default_rng(3)
        result = min_tdcf(rng.normal(size=300), rng.normal(size=900), self.TAR, self.NON, self.SPOOF_ASV)
        assert 0.0 < result["min_tdcf"] <= 1.0

    def test_rejects_hard_decisions(self):
        with pytest.raises(ValueError):
            min_tdcf([1.0, 1.0], [0.0, 0.0], self.TAR, self.NON, self.SPOOF_ASV)

    def test_priors_are_the_2019_values(self):
        assert COST_MODEL_2019["Ptar"] + COST_MODEL_2019["Pnon"] + COST_MODEL_2019["Pspoof"] == pytest.approx(1.0)
        assert (COST_MODEL_2019["Cfa_asv"], COST_MODEL_2019["Cfa_cm"]) == (10.0, 10.0)


def test_evaluate_scores_per_attack_and_asv_file(tmp_path):
    scores = np.r_[BONA, SPOOF]
    labels = np.r_[np.zeros(3), np.ones(4)].astype(int)
    attacks = np.array(["-", "-", "-", "A07", "A08", "A08", "A07"])
    asv_file = tmp_path / "asv.txt"
    asv_file.write_text(
        "bonafide target 5\nbonafide target 6\nbonafide target 7\n"
        "bonafide nontarget -3\nbonafide nontarget -2\nbonafide nontarget -1\n"
        "A07 spoof 4\nA08 spoof 5\nA08 spoof 6\n",
        encoding="utf-8",
    )
    result = evaluate_scores(scores, labels, attacks, load_asv_scores(asv_file))
    assert result["eer"] == pytest.approx(7 / 24)
    assert result["min_tdcf"] == pytest.approx(0.25)
    assert set(result["per_attack"]) == {"A07", "A08"}
    # A07 spoofs (0.7, 0.05) vs bona fide (0.9, 0.8, 0.3): EER at threshold 0.3 is (1/3 + 1/2) / 2.
    assert result["per_attack"]["A07"]["eer"] == pytest.approx((1 / 3 + 1 / 2) / 2)
    assert 0.0 <= result["auc_bonafide_vs_spoof"] <= 1.0
    no_asv = evaluate_scores(scores, labels, attacks, None)
    assert no_asv["min_tdcf"] is None and "not computed" in no_asv["tdcf_note"]


# --------------------------------------------------------------------------- official code
def _official_module():
    candidates = [os.environ.get("ASVSPOOF_OFFICIAL_METRICS")]
    if os.environ.get("DEEPSENTINEL_DATA"):
        candidates.append(str(Path(os.environ["DEEPSENTINEL_DATA"]) / "tools/asvspoof_eval_metrics_official.py"))
    candidates.append("C:/deepsentinel_data/tools/asvspoof_eval_metrics_official.py")
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            spec = importlib.util.spec_from_file_location("asvspoof_official_metrics", candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


OFFICIAL = _official_module()


@pytest.mark.skipif(OFFICIAL is None, reason="official ASVspoof eval_metrics.py not available locally")
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_official_code_on_random_scores(seed):
    rng = np.random.default_rng(seed)
    bona = np.round(rng.normal(1.0, 1.0, 400), 2)  # rounding creates ties
    spoof = np.round(rng.normal(-0.5, 1.2, 1500), 2)
    tar, non, spoof_asv = rng.normal(3, 1, 300), rng.normal(-2, 1, 900), rng.normal(1.5, 1.5, 700)

    ours_eer, ours_thr = eer(bona, spoof)
    off_eer, off_thr = OFFICIAL.compute_eer(bona, spoof)
    assert ours_eer == pytest.approx(off_eer, abs=1e-12) and ours_thr == pytest.approx(off_thr)

    asv_eer, asv_thr = OFFICIAL.compute_eer(tar, non)
    p_fa, p_miss, p_miss_spoof, _ = OFFICIAL.obtain_asv_error_rates(tar, non, spoof_asv, asv_thr)
    curve, _ = OFFICIAL.compute_tDCF_legacy(bona, spoof, p_fa, p_miss, p_miss_spoof, dict(COST_MODEL_2019), False)
    ours = min_tdcf(bona, spoof, tar, non, spoof_asv)
    assert ours["min_tdcf"] == pytest.approx(float(np.min(curve)), abs=1e-12)
