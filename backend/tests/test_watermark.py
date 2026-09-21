"""Tests for the Watermark Detection Module."""

from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from app.ml.forensics.watermark import analyze_watermark
from app.ml.forensics import run_comprehensive_forensics


@pytest.fixture
def clean_image(tmp_path: Path) -> tuple[Path, Image.Image]:
    arr = np.full((300, 300, 3), 128, dtype=np.uint8)
    for i in range(300):
        arr[i, :, 0] = i % 256
    img = Image.fromarray(arr)
    p = tmp_path / "clean.jpg"
    img.save(p, "JPEG")
    return p, img


@pytest.fixture
def watermarked_image(tmp_path: Path) -> tuple[Path, Image.Image]:
    # Create an image and stamp a DALL-E style chromatic badge in bottom-right corner
    arr = np.full((300, 300, 3), 120, dtype=np.uint8)
    # Five colored squares: Yellow, Cyan, Green, Red, Blue in bottom-right
    # Height: 280 to 295, Width: 240 to 290
    colors = [
        [255, 255, 0],   # Yellow
        [0, 255, 255],   # Cyan
        [0, 255, 0],     # Green
        [255, 0, 0],     # Red
        [0, 0, 255],     # Blue
    ]
    for idx, c in enumerate(colors):
        x_start = 240 + idx * 10
        x_end = x_start + 10
        arr[280:292, x_start:x_end] = c

    img = Image.fromarray(arr)
    p = tmp_path / "watermarked.jpg"
    img.save(p, "JPEG")
    return p, img


def test_clean_image_has_no_watermark(clean_image, tmp_path: Path):
    _, img = clean_image
    res = analyze_watermark(img, tmp_path, "job_clean")
    assert res["watermark_detected"] is False
    assert res["watermark_type"] == "NONE"


def test_ai_watermark_detection(watermarked_image, tmp_path: Path):
    _, img = watermarked_image
    res = analyze_watermark(img, tmp_path, "job_wm")
    assert res["watermark_detected"] is True
    assert res["watermark_type"] in ("AI_GENERATOR_STAMP", "VISIBLE_LOGO_BADGE")
    assert "bottom-right corner" in res["location"]
    assert res["confidence"] > 0.60
    assert (tmp_path / "job_wm_watermark.png").exists()


def test_watermark_in_comprehensive_forensics(watermarked_image, tmp_path: Path):
    file_path, img = watermarked_image
    ai_scores = {"ensemble_fake_prob": 0.50}
    forensics = run_comprehensive_forensics(
        file_path=file_path,
        image=img,
        evidence_dir=tmp_path,
        job_id="job_forensic_wm",
        ai_scores=ai_scores,
    )
    assert "watermark" in forensics
    assert forensics["watermark"]["watermark_detected"] is True
    assert "watermark_heatmap" in forensics["heatmaps"]
    # Evidence fusion should register watermark
    signals = forensics["risk_engine"]["evidence_fusion"]["corroborating_signals"]
    assert any("Watermark" in s for s in signals)
