"""AI-image detection safeguards: screenshots, scene-detector fusion, verdict honesty.

Regression tests for an AI-generated image (shared as a screenshot) that came
back "authentic": viewer borders were analysed as image content, a
below-chance detector was averaged in, and a low score was reported as proof
of authenticity.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from PIL import Image, ImageDraw, PngImagePlugin

from app.config import settings
from app.ml.base import AnalysisResult, json_safe
from app.ml.forensics.recapture import crop_recapture_borders
from app.models import Verdict


def _textured(width: int, height: int, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(30, 225, size=(height, width, 3), dtype=np.uint8))


def _screenshot_of(content: Image.Image, pad=(130, 90, 130, 90)) -> Image.Image:
    left, top, right, bottom = pad
    canvas = Image.new("RGB", (content.width + left + right, content.height + top + bottom), (0, 0, 0))
    canvas.paste(content, (left, top))
    return canvas


class TestRecaptureCropping:
    def test_letterboxed_content_is_isolated(self):
        cropped, info = crop_recapture_borders(_screenshot_of(_textured(400, 300), pad=(100, 40, 100, 40)))
        assert info["framed"]
        assert info["content_box"] == [100, 40, 500, 340]
        assert cropped.size == (400, 300)

    def test_nested_viewer_chrome_is_peeled(self):
        # Toolbar strip on top, a grid-lined editor gutter on the left, then a black letterbox.
        canvas = Image.new("RGB", (600, 400), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, 599, 7), fill=(230, 230, 232))
        draw.rectangle((0, 0, 9, 399), fill=(245, 245, 245))
        for y in range(0, 400, 9):
            draw.line((0, y, 9, y), fill=(200, 200, 200))
        canvas.paste(_textured(400, 300, seed=1), (110, 50))

        _, info = crop_recapture_borders(canvas)
        assert info["content_box"] == [110, 50, 510, 350]

    def test_subject_cut_out_on_black_is_not_cropped(self):
        # A composite's black matte must survive for the matte detector.
        image = Image.new("RGB", (800, 600), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((300, 120, 500, 600), fill=(200, 160, 140))
        draw.ellipse((350, 40, 450, 160), fill=(210, 170, 150))
        _, info = crop_recapture_borders(image)
        assert not info["letterbox_detected"]

    def test_unframed_image_is_untouched(self):
        image = _textured(640, 480, seed=2)
        cropped, info = crop_recapture_borders(image)
        assert cropped is image
        assert info["content_box"] is None and not info["framed"]

    def test_flat_strip_on_one_edge_is_trimmed_but_not_called_a_screenshot(self):
        canvas = Image.new("RGB", (600, 412), (255, 255, 255))
        canvas.paste(_textured(600, 400, seed=3), (0, 12))
        _, info = crop_recapture_borders(canvas)
        assert info["letterbox_detected"] and not info["framed"]


class TestVerdictOverride:
    def test_override_wins_over_the_probability(self):
        result = AnalysisResult(0.05, "m", "v", "trained", verdict_override=Verdict.INCONCLUSIVE)
        assert result.verdict is Verdict.INCONCLUSIVE

    def test_an_inconclusive_override_never_reports_high_confidence(self):
        result = AnalysisResult(0.02, "m", "v", "trained", verdict_override=Verdict.INCONCLUSIVE)
        assert result.confidence <= settings.uncertain_band * 2

    def test_without_override_the_probability_decides(self):
        result = AnalysisResult(0.02, "m", "v", "trained")
        assert result.verdict is Verdict.AUTHENTIC
        assert result.confidence == pytest.approx(0.96)


def test_json_safe_makes_evidence_strict_json():
    evidence = {"a": float("nan"), "b": [1.0, float("inf"), {"c": np.float32(0.5)}], "d": np.int64(3), "e": "x"}
    cleaned = json_safe(evidence)
    assert cleaned == {"a": None, "b": [1.0, None, {"c": 0.5}], "d": 3, "e": "x"}
    json.dumps(cleaned, allow_nan=False)  # what browsers accept


class _FakePipe:
    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores

    def __call__(self, image, top_k=None):
        return [{"label": label, "score": score} for label, score in self.scores.items()]


def _detector(model_id: str, weight: float, scores: dict[str, float], real: set[str]):
    from app.ml.image_pipeline import LoadedSceneDetector, SceneDetectorSpec

    return LoadedSceneDetector(SceneDetectorSpec(model_id, weight, "test"), _FakePipe(scores), frozenset(real))


class TestSceneFusion:
    def test_fuses_in_log_odds_space_using_each_models_real_label(self, monkeypatch):
        import app.ml.image_pipeline as ip

        detectors = [
            _detector("primary", 0.75, {"artificial": 0.9, "real": 0.1}, {"real"}),
            _detector("secondary", 0.25, {"ai": 0.2, "hum": 0.8}, {"hum"}),
        ]
        monkeypatch.setattr(ip, "get_scene_detector", lambda: detectors)

        scene = ip.score_scene(Image.new("RGB", (64, 64)))
        expected = 1 / (1 + math.exp(-(0.75 * math.log(9) + 0.25 * math.log(0.25))))
        assert scene["scene_ai_prob"] == pytest.approx(expected, abs=1e-6)
        assert scene["model_scores"] == {"primary": 0.9, "secondary": 0.2}

    def test_one_over_eager_model_cannot_flag_a_photo_alone(self, monkeypatch):
        # The old max-of-experts rule returned 0.99 here.
        import app.ml.image_pipeline as ip

        detectors = [
            _detector("primary", 0.75, {"artificial": 0.02, "real": 0.98}, {"real"}),
            _detector("secondary", 0.25, {"artificial": 0.99, "human": 0.01}, {"human"}),
        ]
        monkeypatch.setattr(ip, "get_scene_detector", lambda: detectors)
        assert ip.score_scene(Image.new("RGB", (64, 64)))["scene_ai_prob"] < 0.35

    def test_no_detector_means_no_score_rather_than_zero(self, monkeypatch):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "get_scene_detector", lambda: [])
        assert ip.score_scene(Image.new("RGB", (64, 64)))["scene_ai_prob"] is None


def _fixed_scene(probability):
    return lambda image: {"scene_ai_prob": probability, "model_scores": {} if probability is None else {"test/model": probability}}


class TestImageVerdicts:
    def test_unflagged_screenshot_is_inconclusive_not_authentic(self, tmp_path, monkeypatch, face_photo):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "score_scene", _fixed_scene(0.03))
        source = tmp_path / "screenshot.png"
        _screenshot_of(face_photo).save(source)

        result = ip.analyze_image(source, tmp_path / "evidence", "shot-job")
        evidence = result.evidence
        assert evidence["recapture"]["framed"]
        assert evidence["image_size"] == [772, 692]
        assert evidence["analysis_region"] == [130, 90, 642, 602]
        assert result.verdict is Verdict.INCONCLUSIVE
        assert evidence["threat_code"] == "SCREEN_RECAPTURE_UNVERIFIABLE"
        assert result.confidence <= settings.uncertain_band * 2

    def test_detected_ai_screenshot_is_still_flagged(self, tmp_path, monkeypatch, face_photo):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "score_scene", _fixed_scene(0.93))
        source = tmp_path / "ai_screenshot.png"
        _screenshot_of(face_photo).save(source)

        result = ip.analyze_image(source, tmp_path / "evidence", "ai-shot-job")
        assert result.verdict is Verdict.MANIPULATED

    def test_missing_detectors_never_yield_authentic(self, tmp_path, monkeypatch, face_photo):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "score_scene", _fixed_scene(None))
        source = tmp_path / "photo.png"
        face_photo.save(source)

        result = ip.analyze_image(source, tmp_path / "evidence", "no-detector-job")
        assert result.verdict is not Verdict.AUTHENTIC
        assert result.evidence["verdict_basis"] in ("scene_detectors_unavailable", "detector_score")

    def test_c2pa_ai_disclosure_decides_even_when_pixels_look_real(self, tmp_path, monkeypatch, face_photo):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "score_scene", _fixed_scene(0.02))
        info = PngImagePlugin.PngInfo()
        info.add_text("c2pa", '{"digitalSourceType": "trainedAlgorithmicMedia"}')
        source = tmp_path / "declared_ai.png"
        face_photo.save(source, pnginfo=info)

        result = ip.analyze_image(source, tmp_path / "evidence", "c2pa-job")
        assert result.verdict is Verdict.MANIPULATED
        assert result.fake_probability >= 0.97

    def test_faceless_image_reports_no_face_scores(self, tmp_path, monkeypatch):
        import app.ml.image_pipeline as ip

        monkeypatch.setattr(ip, "score_scene", _fixed_scene(0.1))
        source = tmp_path / "scene.png"
        Image.new("RGB", (256, 256), (40, 90, 140)).save(source)

        result = ip.analyze_image(source, tmp_path / "evidence", "faceless-job")
        assert result.evidence["faces_detected"] == 0
        assert result.evidence["face_scores"] == []
        json.dumps(json_safe(result.evidence), allow_nan=False)


def test_video_scene_score_reaches_the_pipeline(tmp_path, monkeypatch):
    """The video path used to call ensemble records as functions; every call
    raised inside a bare ``except`` and the scene score was always 0.0."""
    cv2 = pytest.importorskip("cv2")
    import app.ml.video as video

    monkeypatch.setattr(video, "score_scene", _fixed_scene(0.9))
    clip = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (128, 128))
    for _ in range(10):
        frame = np.full((128, 128, 3), 128, dtype=np.uint8)
        cv2.circle(frame, (64, 64), 32, (220, 180, 150), -1)
        writer.write(frame)
    writer.release()

    result = video.analyze_video(clip, tmp_path / "evidence", "video-scene-job")
    stage3 = next(m for m in result.evidence["pipeline_modules"] if m.get("stage") == 3)
    assert "Full-scene ViT GenAI: 90.0%" in stage3["desc"]
