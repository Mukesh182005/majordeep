"""AI-generated video detector (app/ml/aivideo.py) and how the video verdict uses it."""

import json

import numpy as np
import pytest

import app.ml.aivideo as aivideo
from app.config import settings


@pytest.fixture
def head(tmp_path, monkeypatch):
    """A 6-dim head on 2-dim embeddings that scores the first coordinate."""
    d = tmp_path / "aivideo_clip"
    d.mkdir()
    (d / "head.json").write_text(json.dumps({
        "coef": [8.0, 0, 0, 0, 0, 0], "intercept": -4.0, "mean": [0.0] * 6, "scale": [1.0] * 6, "threshold": 0.7,
    }))
    monkeypatch.setattr(settings, "checkpoint_dir", tmp_path)
    monkeypatch.setattr(aivideo, "_HEAD", None)
    return d


def test_features_are_mean_std_and_consecutive_change(monkeypatch):
    emb = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    monkeypatch.setattr(aivideo, "frame_embeddings", lambda frames: emb)
    f = aivideo.video_features([None] * 3)
    np.testing.assert_allclose(f[:2], emb.mean(axis=0))
    np.testing.assert_allclose(f[2:4], emb.std(axis=0))
    np.testing.assert_allclose(f[4:], [1.0, 1.0])


def test_score_uses_the_head_and_its_threshold(head, monkeypatch):
    monkeypatch.setattr(aivideo, "frame_embeddings", lambda frames: np.array([[1.0, 0.0], [1.0, 0.0]], np.float32))
    out = aivideo.score_video_frames([None, None])
    assert out["threshold"] == 0.7
    assert out["probability"] == pytest.approx(1 / (1 + np.exp(-4.0)))


def test_detector_is_off_without_a_head(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "checkpoint_dir", tmp_path)
    monkeypatch.setattr(aivideo, "_HEAD", None)
    assert aivideo.score_video_frames([None]) is None


def _fuse(aivideo_info):
    from app.ml.video.fusion import fuse_video_forensics

    return fuse_video_forensics(
        spatial_prob=0.0, frame_scores=[], temporal_jitter=0.0, motion_metrics={}, compression_score=0.0,
        container_info={}, facial_dynamics={}, lipsync_info={}, scenes=[], duration_s=4.0,
        aivideo_info=aivideo_info,
    )


def test_flag_decides_only_when_in_verdict():
    shown = _fuse({"probability": 0.9, "threshold": 0.7, "in_verdict": False})
    assert shown["threat_code"] != "AI_GENERATED_VIDEO"
    assert any("shown only, not in the verdict" in s for s in shown["corroborating_signals"])
    decided = _fuse({"probability": 0.9, "threshold": 0.7, "in_verdict": True})
    assert decided["threat_code"] == "AI_GENERATED_VIDEO"
    assert decided["final_probability"] >= 0.88
    assert "AI-video detector" in decided["dominant_threat"]


def test_below_threshold_does_not_flag():
    out = _fuse({"probability": 0.6, "threshold": 0.7, "in_verdict": True})
    assert out["threat_code"] != "AI_GENERATED_VIDEO"
