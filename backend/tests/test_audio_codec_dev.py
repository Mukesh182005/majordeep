"""ml/evaluation/audio_codec_dev.py: the frozen rule on logits, per-condition metrics and the codec guard."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation import audio_codec_dev as acd  # noqa: E402

CALIBRATION = {"a": 1.0, "b": 0.0}
FROZEN = {"authentic_below": 0.417, "flagged_at_or_above": 0.577}


def test_frozen_verdicts_follow_the_backend_boundaries():
    # p = sigmoid(logit): 0.577 <-> logit 0.3106, 0.417 <-> logit -0.3352
    logits = np.array([2.0, 0.3107, 0.0, -0.3351, -0.3353, -2.0])
    assert acd.frozen_verdicts(logits, CALIBRATION, FROZEN).tolist() == [
        "flagged", "flagged", "inconclusive", "inconclusive", "authentic", "authentic"]


def _rows(mp3_bonafide_logit: float) -> list[dict]:
    rows = []
    for i in range(40):
        label = int(i >= 20)
        for condition in ("original", "mp3_64k", "opus_32k"):
            logit = (3.0 if label else -3.0) + 0.01 * i
            if condition == "mp3_64k" and not label:
                logit = mp3_bonafide_logit
            rows.append({"utt_id": f"u{i}", "label": str(label), "attack_id": "A01" if label else "-",
                         "condition": condition, "checkpoint": "m.pt", "mean_spoof_logit": str(logit),
                         "n_windows": "1", "error": ""})
    rows.append({"utt_id": "u0", "label": "0", "attack_id": "-", "condition": "aac_64k", "checkpoint": "m.pt",
                 "mean_spoof_logit": "", "n_windows": "", "error": "CalledProcessError"})
    return rows


def test_guard_fires_only_for_the_family_that_flags_bona_fide():
    summary = acd.summarise_checkpoint(_rows(mp3_bonafide_logit=2.0), "m.pt", CALIBRATION, FROZEN)
    assert summary["conditions"]["original"]["eer"] == 0.0
    assert summary["conditions"]["mp3_64k"]["bonafide_flagged_rate"] == 1.0
    assert summary["guard"]["families"] == {"mp3": True, "opus": False}
    assert "aac_64k" not in summary["conditions"]  # only errors: no metrics, not silently zero

    clean = acd.summarise_checkpoint(_rows(mp3_bonafide_logit=-3.0), "m.pt", CALIBRATION, FROZEN)
    assert clean["guard"]["families"] == {"mp3": False, "opus": False}


def test_without_calibration_only_ranking_metrics():
    summary = acd.summarise_checkpoint(_rows(-3.0), "m.pt")
    assert "guard" not in summary and "bonafide_flagged_rate" not in summary["conditions"]["original"]
