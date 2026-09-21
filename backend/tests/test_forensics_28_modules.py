"""Tests for the 28-module Cybersecurity Digital Image Forensics Platform."""

from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from app.ml.forensics.file_security import analyze_file_security
from app.ml.forensics.hashing import compute_all_hashes, compute_hash_similarity
from app.ml.forensics.metadata_timeline import analyze_metadata_and_timeline
from app.ml.forensics.tampering import analyze_tampering, compute_ela
from app.ml.forensics.steganography import analyze_steganography
from app.ml.forensics.camera_cfa import analyze_camera_and_cfa
from app.ml.forensics.provenance_threat import analyze_provenance_and_threats
from app.ml.forensics.adversarial_ood import analyze_adversarial_and_ood
from app.ml.forensics.risk_fusion import compute_risk_and_fusion
from app.ml.forensics.custody import generate_chain_of_custody, get_model_audit_info
from app.ml.forensics import run_comprehensive_forensics


@pytest.fixture
def sample_image(tmp_path: Path) -> tuple[Path, Image.Image]:
    # Create a synthetic image with high-contrast gradient
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    for i in range(200):
        for j in range(200):
            arr[i, j] = [i % 256, (i * 2 + j) % 256, (j * 3) % 256]
    img = Image.fromarray(arr)
    file_path = tmp_path / "test_sample.jpg"
    img.save(file_path, "JPEG", quality=95)
    return file_path, img


def test_file_security_and_magic_bytes(sample_image):
    file_path, _ = sample_image
    sec = analyze_file_security(file_path)
    assert sec["format"] == "JPEG"
    assert sec["structure_valid"] is True
    assert sec["extension_mismatch"] is False
    assert sec["trailing_data_detected"] is False


def test_trailing_data_detection(tmp_path: Path, sample_image):
    file_path, _ = sample_image
    trailing_file = tmp_path / "trailing.jpg"
    content = file_path.read_bytes() + b"SECRET_TRAILING_PAYLOAD_12345"
    trailing_file.write_bytes(content)

    sec = analyze_file_security(trailing_file)
    assert sec["trailing_data_detected"] is True
    assert sec["trailing_bytes_count"] == len(b"SECRET_TRAILING_PAYLOAD_12345")


def test_cryptographic_and_perceptual_hashing(sample_image):
    file_path, img = sample_image
    hashes = compute_all_hashes(file_path, img)
    assert len(hashes["sha256"]) == 64
    assert len(hashes["md5"]) == 32
    assert len(hashes["sha1"]) == 40
    assert len(hashes["sha512"]) == 128
    assert hashes["phash"] != "unavailable"
    assert hashes["dhash"] != "unavailable"


def test_tampering_and_ela(tmp_path: Path, sample_image):
    file_path, img = sample_image
    tamper = analyze_tampering(img)
    assert "copy_move_detected" in tamper
    assert "gradient_discontinuity_score" in tamper

    ela = compute_ela(img, tmp_path, "job_test_1")
    assert 0.0 <= ela["ela_score"] <= 1.0
    assert (tmp_path / ela["heatmap_file"]).exists()


def test_steganography_and_bitplanes(tmp_path: Path, sample_image):
    file_path, img = sample_image
    stego = analyze_steganography(img, tmp_path, "job_test_2")
    assert stego["payload_likelihood"] in ("LOW", "MEDIUM", "HIGH")
    assert "channel_entropies" in stego
    assert (tmp_path / stego["heatmap_file"]).exists()


def test_camera_and_cfa(tmp_path: Path, sample_image):
    file_path, img = sample_image
    cam = analyze_camera_and_cfa(img, tmp_path, "job_test_3")
    assert "camera_fingerprint_detected" in cam
    assert "cfa_artifacts_detected" in cam
    assert (tmp_path / cam["heatmap_file"]).exists()


def test_risk_scoring_and_fusion(tmp_path: Path, sample_image):
    file_path, img = sample_image
    ai_scores = {"ensemble_fake_prob": 0.88}
    forensics = run_comprehensive_forensics(
        file_path=file_path,
        image=img,
        evidence_dir=tmp_path,
        job_id="job_test_full",
        ai_scores=ai_scores,
    )
    risk = forensics["risk_engine"]
    assert 0 <= risk["overall_risk_score"] <= 100
    assert "evidence_fusion" in risk
    assert "fusion_verdict" in risk["evidence_fusion"]
    assert forensics["chain_of_custody"]["evidence_id"].startswith("DFE-")
    assert (tmp_path / forensics["heatmaps"]["combined_heatmap"]).exists()
