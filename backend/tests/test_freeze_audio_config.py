"""ml/evaluation/freeze_audio_config.py still rebuilds the committed rule for the served model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ml.evaluation import freeze_audio_config as fac  # noqa: E402


def test_default_calibration_reproduces_the_committed_rule():
    committed = json.loads((REPO / "paper/config/frozen_audio_config.json").read_text(encoding="utf-8"))
    if not (REPO / json.loads(fac.CALIBRATION_FILE.read_text(encoding="utf-8"))["fit_data"]["file"]).is_file():
        pytest.skip("dev score file not present")
    rebuilt = fac.build_config()
    for key in ("checkpoint_sha256", "threshold", "inconclusive_band", "authentic_below", "flagged_at_or_above",
                "decision_rule", "synthesis_risk_weights"):
        assert rebuilt[key] == committed[key], key
    for cls in ("bonafide", "spoof"):
        assert rebuilt["dev_verdict_rates_information_only"][cls] == committed["dev_verdict_rates_information_only"][cls]
