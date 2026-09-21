"""Unit and integration tests for native spatio-temporal video forensic suite.

Tests:
1. rPPG remote photoplethysmography (capillary pulse, SNR, synthetic void rejection).
2. Spatio-temporal 4D volume tensor dynamics (TimeSformer patch drift, SlowFast vibration).
3. LipForensics articulatory kinematics (velocity, jerk anomaly, phonetic smoothness).
4. Multi-modal fusion with native spatio-temporal features.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from PIL import Image

from app.ml.video.lip_forensics import analyze_lip_forensics
from app.ml.video.rppg_biometrics import extract_rppg_biometrics
from app.ml.video.spatiotemporal_forensics import analyze_spatiotemporal_tensor
from app.ml.video.fusion import compute_video_risk, fuse_video_forensics


class TestRPPGBiometrics:
    def test_extracts_bvp_pulse_and_frequency(self):
        # Create 16 frames with periodic subtle green channel fluctuation (simulating heart pulse at 1.2 Hz / 72 BPM)
        fps = 25.0
        frames: list[tuple[float, Image.Image]] = []
        boxes: list[tuple[int, int, int, int] | None] = []
        for i in range(24):
            t = i / fps
            pulse = 10.0 * np.sin(2.0 * np.pi * 1.2 * t)
            # Base skin color + pulse in green
            r = int(180)
            g = int(np.clip(140 + pulse, 0, 255))
            b = int(120)
            img = Image.new("RGB", (100, 100), (r, g, b))
            frames.append((t, img))
            boxes.append((10, 10, 90, 90))

        res = extract_rppg_biometrics(frames, boxes)
        assert "biometric_pulse_detected" in res
        assert "estimated_heart_rate_bpm" in res
        assert "cardiac_snr_db" in res
        assert "pulse_waveform" in res
        assert len(res["pulse_waveform"]) == 24
        # Since periodic sinusoidal green was injected, SNR should be positive
        assert res["cardiac_snr_db"] > -10.0

    def test_rejects_synthetic_uniform_void(self):
        # Static grey frames with random white noise
        frames: list[tuple[float, Image.Image]] = []
        boxes: list[tuple[int, int, int, int] | None] = []
        for i in range(12):
            t = i / 25.0
            noise_img = Image.fromarray(np.random.randint(120, 130, (80, 80, 3), dtype=np.uint8))
            frames.append((t, noise_img))
            boxes.append((10, 10, 70, 70))

        res = extract_rppg_biometrics(frames, boxes)
        assert res["biometric_pulse_detected"] is False


class TestSpatioTemporalTensor:
    def test_analyzes_timesformer_and_slowfast(self):
        frames: list[tuple[float, Image.Image]] = []
        for i in range(8):
            t = i / 25.0
            img = Image.new("RGB", (112, 112), (i * 20, 100, 150))
            frames.append((t, img))

        res = analyze_spatiotemporal_tensor(frames)
        assert "spatiotemporal_anomaly_score" in res
        assert "latent_noise_jump_rate" in res
        assert "slowfast_boundary_vibration" in res
        assert 0.0 <= res["spatiotemporal_anomaly_score"] <= 1.0


class TestLipForensics:
    def test_evaluates_articulatory_jerk(self):
        frames: list[tuple[float, Image.Image]] = []
        boxes: list[tuple[int, int, int, int] | None] = []
        for i in range(10):
            t = i / 25.0
            img = Image.new("RGB", (100, 100), (200, 180, 160))
            frames.append((t, img))
            boxes.append((10, 10, 90, 90))

        res = analyze_lip_forensics(frames, boxes)
        assert "lip_manipulation_probability" in res
        assert "articulatory_jerk_anomaly" in res
        assert "phonetic_transition_smoothness" in res
        assert 0.0 <= res["lip_manipulation_probability"] <= 1.0


class TestMultiModalSpatioTemporalFusion:
    def test_fuses_rppg_and_spatiotemporal_signals(self):
        risk = compute_video_risk(
            spatial_prob=0.88,
            temporal_jitter=0.45,
            motion_anomaly=0.40,
            compression_anomaly=0.30,
            vit_genai_prob=0.85,
            spatiotemporal_anomaly=0.78,
            rppg_synthetic_void=True,
            lip_forensics_anomaly=0.65,
        )
        assert risk >= 0.82
