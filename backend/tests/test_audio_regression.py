"""Accuracy regression and end-to-end checks for the served audio model (real data).

* ``test_served_model_auc_stays_near_the_eval_auc``: scores the labelled clips
  in ``AUDIO_REGRESSION_DIR`` (made by ``scripts/export_audio_regression_set.py``)
  with the served LCNN through the serving path and asserts their AUC is within
  0.05 of the LA eval AUC recorded in ``results/audio_eval.json``.
* ``test_uploaded_la_eval_clip_gets_the_trained_verdict``: uploads one ASVspoof
  2019 LA eval clip through ``/api/upload`` and checks the verdict comes from
  the trained model with the frozen thresholds.

Both need the real checkpoint (never committed) and skip without it; the
second also needs ``DEEPSENTINEL_DATA``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
CALIBRATION = REPO / "paper" / "config" / "audio_calibration.json"
FROZEN = REPO / "paper" / "config" / "frozen_audio_config.json"
SR = 16000


@pytest.fixture()
def served_model(monkeypatch):
    """Point the settings at the real served LCNN, its calibration and frozen verdict config."""
    from app.config import settings
    from app.ml import registry

    if not CALIBRATION.is_file() or not FROZEN.is_file():
        pytest.skip("paper/config audio calibration or frozen config missing")
    checkpoint = REPO / json.loads(CALIBRATION.read_text(encoding="utf-8"))["checkpoint"]
    if not checkpoint.is_file():
        pytest.skip(f"{checkpoint.name} not present (weights are never committed)")
    monkeypatch.setattr(settings, "checkpoint_dir", checkpoint.parent)
    monkeypatch.setattr(settings, "audio_lcnn_calibration_file", CALIBRATION)
    monkeypatch.setattr(settings, "audio_verdict_config_file", FROZEN)
    monkeypatch.setattr(settings, "audio_model_source", "lcnn_asvspoof")
    registry.reset_cache()
    yield
    registry.reset_cache()


def test_served_model_auc_stays_near_the_eval_auc(served_model):
    folder = os.environ.get("AUDIO_REGRESSION_DIR")
    if not folder:
        pytest.skip("AUDIO_REGRESSION_DIR not set (see scripts/export_audio_regression_set.py)")
    from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
    from app.ml.preprocessing import load_audio

    from ml.evaluation.metrics import roc_auc

    folder = Path(folder)
    with open(folder / "labels.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    labels, scores = [], []
    for row in rows:
        path = folder / row["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], f"{path.name} changed"
        waveform, _ = load_audio(path, SR)
        labels.append(int(row["label"]))
        scores.append(score_lcnn_asvspoof(waveform, SR)["cm_score"])  # higher = bona fide
    labels = np.array(labels)
    assert 0 < labels.sum() < labels.size, "need both classes"
    auc = roc_auc((labels == 0).astype(int), np.array(scores))

    reference = json.loads((REPO / "results" / "audio_eval.json").read_text(encoding="utf-8"))
    expected = reference["asvspoof2019_la_eval"]["auc_bonafide_vs_spoof"]
    assert abs(auc - expected) <= 0.05, f"regression-set AUC {auc:.4f} vs LA eval AUC {expected:.4f}"


def test_uploaded_la_eval_clip_gets_the_trained_verdict(served_model, client):
    data = os.environ.get("DEEPSENTINEL_DATA")
    manifest = REPO / "data/processed/asvspoof2019_la/manifest.csv"
    if not data or not manifest.is_file():
        pytest.skip("ASVspoof 2019 LA data not available")
    from app.main import app
    from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
    from app.ml.preprocessing import load_audio
    from fastapi.testclient import TestClient

    from ml.preprocessing.build_asvspoof2019_la import read_manifest

    row = next(r for r in read_manifest(manifest, ("eval",)) if r["attack_id"] == "A16")
    path = Path(data) / "ASVspoof2019" / "LA" / row["relative_path"]
    peer = TestClient(app, client=("198.51.100.90", 50000))
    created = peer.post("/api/upload", files={"file": (path.name, path.read_bytes(), "audio/flac")})
    assert created.status_code == 202, created.text
    result = peer.get(f"/api/jobs/{created.json()['id']}/result").json()

    assert result["model_name"] == "LCNN (LFCC), ASVspoof 2019 LA"
    assert result["weights_status"] == "trained" and result["experimental"] is False
    waveform, _ = load_audio(path, SR)
    p = score_lcnn_asvspoof(waveform, SR)["probability"]
    assert result["fake_probability"] == round(p, 4)
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    expected = ("MANIPULATED" if p >= frozen["flagged_at_or_above"]
                else "AUTHENTIC" if p < frozen["authentic_below"] else "INCONCLUSIVE")
    assert result["verdict"] == expected
    assert result["evidence"]["segment_scores_source"] == "lcnn_asvspoof"
