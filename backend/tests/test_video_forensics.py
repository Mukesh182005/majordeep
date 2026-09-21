"""Unit tests for enterprise video forensic engine modules."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from app.ml.video.container_forensics import analyze_video_container
from app.ml.video.scenes import detect_scenes_and_shots
from app.ml.video.face_temporal import analyze_facial_temporal_dynamics
from app.ml.video.optical_flow import compute_optical_flow_anomaly
from app.ml.video.audio_crossmodal import analyze_crossmodal_lipsync
from app.ml.video.source_circulation import compute_source_circulation_intelligence
from app.ml.video.fusion import compute_video_risk, fuse_video_forensics


class TestVideoContainerForensics:
    def test_handles_nonexistent_file_gracefully(self, tmp_path):
        res = analyze_video_container(tmp_path / "missing.mp4")
        assert res["container_format"] == "UNKNOWN"
        assert res["atom_hierarchy"] == []

    def test_parses_simulated_mp4_box_atoms(self, tmp_path):
        dummy_mp4 = tmp_path / "sample.mp4"
        # Construct synthetic MP4 with ftyp and moov atoms
        ftyp_body = b"mp42\x00\x00\x00\x00isommp42"
        ftyp_size = len(ftyp_body) + 8
        ftyp_header = ftyp_size.to_bytes(4, "big") + b"ftyp"
        
        moov_body = b"\x00" * 32
        moov_size = len(moov_body) + 8
        moov_header = moov_size.to_bytes(4, "big") + b"moov"

        dummy_mp4.write_bytes(ftyp_header + ftyp_body + moov_header + moov_body)

        res = analyze_video_container(dummy_mp4)
        assert res["container_format"] == "mp42"
        assert len(res["atom_hierarchy"]) >= 2
        assert res["atom_hierarchy"][0]["atom"] == "ftyp"
        assert res["atom_hierarchy"][1]["atom"] == "moov"
        assert len(res["file_info"]["sha256"]) == 64


class TestSceneDetection:
    def test_segments_frames_into_scenes(self):
        # Create 6 synthetic frames with a sharp visual cut in the middle
        frames = []
        for i in range(3):
            # Bright red scene
            img = Image.new("RGB", (64, 64), (240, 20, 20))
            frames.append((float(i), img))
        for i in range(3, 6):
            # Dark blue scene
            img = Image.new("RGB", (64, 64), (20, 20, 240))
            frames.append((float(i), img))

        scenes = detect_scenes_and_shots(frames, min_scene_duration_s=0.5, threshold=0.30)
        assert len(scenes) >= 2
        assert scenes[0]["start_time_s"] == 0.0
        assert scenes[-1]["end_time_s"] == 5.0


class TestFacialTemporalDynamics:
    def test_analyzes_facial_dynamics(self):
        frames = [(float(i), Image.new("RGB", (120, 120), (180, 140, 120))) for i in range(5)]
        boxes: list[tuple[int, int, int, int] | None] = [(20, 20, 100, 100) for _ in range(5)]
        res = analyze_facial_temporal_dynamics(frames, boxes)
        assert res["faces_tracked"] == 5
        assert "landmark_jitter_score" in res
        assert "blink_analysis" in res


class TestOpticalFlowDecomposition:
    def test_computes_motion_fields(self, tmp_path):
        frames = [np.full((80, 80, 3), fill_value=i * 15, dtype=np.uint8) for i in range(4)]
        boxes: list[tuple[int, int, int, int] | None] = [(10, 10, 70, 70) for _ in range(4)]
        score, metrics = compute_optical_flow_anomaly(frames, boxes, evidence_dir=tmp_path, job_id="test_flow")
        assert 0.0 <= score <= 1.0
        assert "face_background_divergence" in metrics


class TestSourceCirculation:
    def test_generates_circulation_intelligence(self):
        frames = [(float(i), Image.new("RGB", (80, 80), (100, 150, 200))) for i in range(4)]
        res = compute_source_circulation_intelligence(frames, "fake_sha256", 15.0)
        assert len(res["keyframe_perceptual_hashes"]) == 4
        assert len(res["discovered_sources"]) >= 1
        assert "nodes" in res["genealogy_graph"]
        assert "edges" in res["genealogy_graph"]


class TestVideoRiskFusion:
    def test_threat_taxonomy_assignment(self):
        frame_scores = [{"timestamp_s": 0.0, "fake_probability": 0.92}]
        fusion = fuse_video_forensics(
            spatial_prob=0.92,
            frame_scores=frame_scores,
            temporal_jitter=0.48,
            motion_metrics={"mean_motion_anomaly": 0.52, "face_background_divergence": 2.4},
            compression_score=0.45,
            container_info={"screen_recording_analysis": {"screen_recording_detected": False}},
            facial_dynamics={"landmark_jitter_score": 0.42, "blink_analysis": {}},
            lipsync_info={"lip_sync_anomaly_detected": False},
            scenes=[{"scene_id": 1}],
            duration_s=8.0,
        )
        assert fusion["final_probability"] >= 0.80
        assert fusion["threat_code"] in ("DEEPFAKE_FACE_SWAP", "AI_GENERATED_VIDEO")
        assert len(fusion["corroborating_signals"]) >= 2
        assert len(fusion["segment_timeline"]) >= 1


class TestFullVideoOrchestration:
    def test_runs_8_stage_video_pipeline(self, tmp_path):
        import cv2
        from app.ml.video import analyze_video

        # Create a small valid AVI video using cv2.VideoWriter
        vid_file = tmp_path / "test_clip.avi"
        fourcc_fn = getattr(cv2, "VideoWriter_fourcc", getattr(cv2.VideoWriter, "fourcc", None))
        fourcc = fourcc_fn(*"MJPG") if fourcc_fn is not None else 0
        out = cv2.VideoWriter(str(vid_file), fourcc, 10.0, (128, 128))
        for i in range(12):
            frame = np.full((128, 128, 3), fill_value=(i * 20) % 255, dtype=np.uint8)
            # Draw a face-like oval
            cv2.ellipse(frame, (64, 64), (30, 40), 0, 0, 360, (200, 180, 160), -1)
            out.write(frame)
        out.release()

        evidence_dir = tmp_path / "evidence"
        result = analyze_video(vid_file, evidence_dir, "test_job_full")

        assert 0.0 <= result.fake_probability <= 1.0
        assert result.evidence["media"] == "video"
        assert len(result.evidence["pipeline_modules"]) >= 8
        assert "dominant_threat" in result.evidence
        assert "threat_code" in result.evidence
        assert "segment_timeline" in result.evidence
        assert "container_forensics" in result.evidence
        assert "scenes" in result.evidence
        assert "facial_dynamics" in result.evidence
        assert (evidence_dir / result.evidence["timeline_file"]).exists()

