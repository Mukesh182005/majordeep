"""GenD face-swap scorer and its use in the video pipeline, with a stub model (no downloads)."""

from __future__ import annotations

import numpy as np
import pytest
import torch
from PIL import Image

from app.config import settings


class _StubExtractor:
    def preprocess(self, image):
        return torch.zeros(3, 224, 224)


class _StubGenD(torch.nn.Module):
    """Returns fixed logits: one row per input, cycling through ``rows``."""

    def __init__(self, rows):
        super().__init__()
        self.rows = torch.tensor(rows, dtype=torch.float32)
        self.feature_extractor = _StubExtractor()
        self.anchor = torch.nn.Parameter(torch.zeros(1))  # gives the stub a device

    def forward(self, x):
        idx = torch.arange(x.shape[0]) % len(self.rows)
        return self.rows[idx]


def _logits_for(p_fake: float) -> list[float]:
    """Two logits whose softmax gives [1 - p, p]."""
    return [0.0, float(np.log(p_fake / (1 - p_fake)))]


def test_square_crop_is_1_3_times_the_box_and_square_at_the_edge():
    from app.ml.gend import square_face_crop

    image = Image.new("RGB", (400, 300), (10, 20, 30))
    crop = square_face_crop(image, (150, 100, 250, 220))  # 100 x 120 box
    assert crop.size == (round(1.3 * 120), round(1.3 * 120))
    edge = square_face_crop(image, (0, 0, 80, 60))
    assert edge.size[0] == edge.size[1] == round(1.3 * 80)
    assert edge.getpixel((0, 0)) == (0, 0, 0)  # padded outside the frame


def test_score_faces_returns_softmax_index_1_in_order(monkeypatch):
    from app.ml import gend

    monkeypatch.setattr(gend, "get_gend", lambda: _StubGenD([_logits_for(0.2), _logits_for(0.9)]))
    faces = [Image.new("RGB", (50, 50)) for _ in range(4)]
    assert gend.score_faces(faces, batch_size=4) == pytest.approx([0.2, 0.9, 0.2, 0.9], abs=1e-5)


def test_score_faces_is_empty_without_a_model(monkeypatch):
    from app.ml import gend

    monkeypatch.setattr(gend, "get_gend", lambda: None)
    assert gend.score_faces([Image.new("RGB", (50, 50))]) == []


@pytest.fixture()
def clip(tmp_path):
    cv2 = pytest.importorskip("cv2")
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (128, 128))
    for i in range(20):
        frame = np.full((128, 128, 3), (i * 10) % 255, dtype=np.uint8)
        cv2.ellipse(frame, (64, 64), (30, 40), 0, 0, 360, (200, 180, 160), -1)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture()
def stubbed_video(monkeypatch):
    """Every frame has one face; GenD scores every face 0.9; scene and fusion inputs are recorded."""
    import app.ml.video as video
    from app.ml import gend
    from app.ml.faces import FaceCrop

    def faces(frame):
        return [FaceCrop(image=frame.crop((30, 20, 98, 108)), box=(30, 20, 98, 108), confidence=0.99,
                         detection_box=(40, 30, 88, 98))]

    seen = {"scene_calls": 0}

    def scene(image):
        seen["scene_calls"] += 1
        return {"scene_ai_prob": 0.1, "model_scores": {"test/model": 0.1}}

    real_fuse = video.fuse_video_forensics

    def fuse(**kwargs):
        seen["spatial_prob"] = kwargs["spatial_prob"]
        return real_fuse(**kwargs)

    monkeypatch.setattr(video, "extract_faces", faces)
    monkeypatch.setattr(video, "score_scene", scene)
    monkeypatch.setattr(video, "fuse_video_forensics", fuse)
    monkeypatch.setattr(gend, "get_gend", lambda: _StubGenD([_logits_for(0.9)]))
    return seen


def test_gend_mean_feeds_the_verdict_only_when_switched_on(clip, tmp_path, monkeypatch, stubbed_video):
    from app.ml.video import analyze_video

    monkeypatch.setattr(settings, "gend_in_verdict", True)
    result = analyze_video(clip, tmp_path / "on", "gend-on")
    ev = result.evidence
    assert stubbed_video["spatial_prob"] == pytest.approx(0.9, abs=1e-3)
    assert ev["gend_face_mean"] == pytest.approx(0.9, abs=1e-3)
    assert ev["gend_in_verdict"] is True
    assert all(s["fake_probability"] == pytest.approx(0.9, abs=1e-3) for s in ev["frame_scores"])
    assert all("legacy_face_probability" in s for s in ev["frame_scores"])


def test_without_the_flag_the_old_rule_is_unchanged(clip, tmp_path, monkeypatch, stubbed_video):
    from app.ml.video import analyze_video

    monkeypatch.setattr(settings, "gend_in_verdict", False)
    monkeypatch.setattr(settings, "face_model_in_verdict", False)
    result = analyze_video(clip, tmp_path / "off", "gend-off")
    assert stubbed_video["spatial_prob"] == 0.0
    assert result.evidence["gend_in_verdict"] is False
    stage3 = next(m for m in result.evidence["pipeline_modules"] if m["stage"] == 3)
    assert "not in verdict" in stage3["desc"]


def test_scene_detectors_score_several_frames(clip, tmp_path, monkeypatch, stubbed_video):
    from app.ml.video import analyze_video

    monkeypatch.setattr(settings, "video_scene_frames", 8)
    result = analyze_video(clip, tmp_path / "scene", "scene-frames")
    n_frames = result.evidence["frames_analysed"]
    assert len(result.evidence["scene_frame_scores"]) == min(8, n_frames)
    assert stubbed_video["scene_calls"] >= min(8, n_frames)


def test_scene_only_ai_video_is_labelled_not_validated(tmp_path, monkeypatch):
    """A video judged AI-generated by the scene detectors alone says they are not validated on video."""
    cv2 = pytest.importorskip("cv2")
    import app.ml.video as video

    monkeypatch.setattr(video, "score_scene", lambda image: {"scene_ai_prob": 0.95, "model_scores": {"t": 0.95}})
    clip = tmp_path / "gen.avi"
    writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (96, 96))
    for i in range(10):
        writer.write(np.full((96, 96, 3), 30 + i, dtype=np.uint8))
    writer.release()
    result = video.analyze_video(clip, tmp_path / "ev", "gen-job")
    assert result.evidence["threat_code"] == "AI_GENERATED_VIDEO"
    assert "not validated on video" in result.evidence["dominant_threat"]
    assert any("not validated for video" in n for n in result.evidence["notes"])
