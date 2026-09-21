"""Unit tests for unified multi-modal video forensics and AI generator attribution."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from app.ml.video.generator_attribution import analyze_generator_attribution
from app.ml.video.fusion import compute_video_risk, fuse_video_forensics


class TestGeneratorAttribution:
    def test_attributes_synthetic_diffusion_video(self):
        # Construct synthetic frames with smoothed noise and steep Fourier gradient
        frames = []
        for i in range(5):
            # Smooth digital gradient (low sensor shot noise)
            arr = np.zeros((128, 128, 3), dtype=np.uint8)
            arr[:, :] = [(i * 25) % 255, 120, 180]
            frames.append((float(i), Image.fromarray(arr)))

        res = analyze_generator_attribution(
            frames_pil=frames,
            spatial_genai_prob=0.85,
            optical_flow_score=0.45,
        )
        assert res["is_ai_generated"] is True
        assert res["no_watermark_detection"] is True
        assert res["attribution_confidence"] >= 0.70
        assert "OpenAI Sora" in res["predicted_platform"] or "Google Gemini" in res["predicted_platform"] or "Kling" in res["predicted_platform"] or "Modern AI Generator" in res["explanation"]
        assert len(res["detected_signatures"]) >= 1

    def test_distinguishes_authentic_optical_noise(self):
        # Construct frames with high natural sensor shot noise
        rng = np.random.default_rng(42)
        frames = []
        for i in range(5):
            arr = rng.integers(60, 200, (128, 128, 3), dtype=np.uint8)
            frames.append((float(i), Image.fromarray(arr)))

        res = analyze_generator_attribution(
            frames_pil=frames,
            spatial_genai_prob=0.08,
            optical_flow_score=0.10,
        )
        assert res["is_ai_generated"] is False
        assert "Authentic Camera" in res["predicted_platform"]


class TestMultiModalFusion:
    def test_fuses_image_audio_video_modalities(self):
        fusion = fuse_video_forensics(
            spatial_prob=0.88,
            frame_scores=[{"timestamp_s": 0.0, "fake_probability": 0.88}],
            temporal_jitter=0.42,
            motion_metrics={"mean_motion_anomaly": 0.45, "face_background_divergence": 2.1},
            compression_score=0.35,
            container_info={"screen_recording_analysis": {"screen_recording_detected": False}},
            facial_dynamics={"landmark_jitter_score": 0.38, "blink_analysis": {}},
            lipsync_info={"lip_sync_anomaly_detected": False},
            scenes=[{"scene_id": 1}],
            duration_s=6.0,
            vit_genai_prob=0.82,
            image_forensics={"camera_cfa": {"synthetic_sensor_detected": True, "fourier_spectral_slope": 2.75}},
            audio_forensics={"fusion_decision": {"calibrated_fake_probability": 0.75}},
            attribution_info={"is_ai_generated": True, "predicted_platform": "OpenAI Sora / ChatGPT", "attribution_confidence": 0.92, "detected_signatures": ["Missing sensor noise"]},
        )

        assert fusion["final_probability"] >= 0.85
        assert "AI-Generated Video Media" in fusion["dominant_threat"]
        assert fusion["threat_code"] == "AI_GENERATED_VIDEO"
        assert any("OpenAI Sora" in s for s in fusion["corroborating_signals"])
        assert any("Image Forensics" in s for s in fusion["corroborating_signals"])


class TestFullMultiModalOrchestration:
    def test_executes_unified_video_pipeline(self, tmp_path):
        import cv2
        from app.ml.video import analyze_video

        # Create dummy AVI video with drawn features
        vid_file = tmp_path / "synthetic_ai_test.avi"
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        out = cv2.VideoWriter(str(vid_file), fourcc, 10.0, (128, 128))
        for i in range(10):
            frame = np.full((128, 128, 3), fill_value=128, dtype=np.uint8)
            cv2.circle(frame, (64, 64), 32, (220, 180, 150), -1)
            out.write(frame)
        out.release()

        evidence_dir = tmp_path / "evidence_mm"
        res = analyze_video(vid_file, evidence_dir, "job_mm_test")

        assert 0.0 <= res.fake_probability <= 1.0
        assert res.evidence["media"] == "video"
        assert "generator_attribution" in res.evidence
        assert "image_forensics" in res.evidence
        assert len(res.evidence["pipeline_modules"]) >= 8
