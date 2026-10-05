"""Video deepfake detection pipeline orchestrator.

Unified multi-modal architecture executing:
  1. Spatial Image Forensics (28-module image suite + ViT full-scene generative AI)
  2. Acoustic Audio Forensics (10-engine speech physics, voice cloning & ENF phase)
  3. Temporal Video Forensics (Dense optical flow, landmark acceleration, EAR blinks)
  4. AI Generator Attribution Engine (Intrinsic no-watermark detection: Sora, Gemini/Veo, Kling, Runway, Luma)
  5. Conformal Multi-Modal Risk Fusion & Threat Attribution

Generates comprehensive evidence: Grad-CAM heatmap, Farneback optical flow plate, ELA plate, and timeline.
"""

from __future__ import annotations

import importlib
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from app.config import settings
from app.ml.base import AnalysisResult
from app.ml.faces import extract_faces
from app.ml.forensics import run_comprehensive_forensics
from app.ml.gradcam import compute_gradcam, overlay_heatmap
from app.ml.image_pipeline import score_scene
from app.ml.preprocessing import normalize_waveform, preprocess_image, sample_video_frames
from app.ml.registry import UNTRAINED, get_image_model
from app.ml.video.audio_crossmodal import analyze_crossmodal_lipsync
from app.ml.video.compression_dna import extract_compression_fingerprint
from app.ml.video.container_forensics import analyze_video_container
from app.ml.video.face_temporal import analyze_facial_temporal_dynamics
from app.ml.video.fusion import fuse_video_forensics
from app.ml.video.generator_attribution import analyze_generator_attribution
from app.ml.video.lip_forensics import analyze_lip_forensics
from app.ml.video.optical_flow import compute_optical_flow_anomaly
from app.ml.video.rppg_biometrics import extract_rppg_biometrics
from app.ml.video.scenes import detect_scenes_and_shots
from app.ml.video.spatiotemporal_forensics import analyze_spatiotemporal_tensor
from app.ml.video.temporal_jitter import compute_temporal_jitter

logger = logging.getLogger(__name__)

# Primary/largest face per frame keeps inference performant.
_MAX_FACES_PER_FRAME = 1


def analyze_video(
    path: str | Path,
    evidence_dir: str | Path,
    job_id: str,
) -> AnalysisResult:
    """Orchestrate the unified multi-modal video forensics pipeline."""
    t0 = time.perf_counter()
    pipeline_modules: list[dict[str, Any]] = []

    file_path = Path(path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 1: Container & Bitstream Forensics ────────────────────────────────
    st1_start = time.perf_counter()
    container_info = analyze_video_container(file_path)
    compression_score = extract_compression_fingerprint(file_path)
    screen_rec = container_info.get("screen_recording_analysis", {})
    st1_ms = int((time.perf_counter() - st1_start) * 1000)
    pipeline_modules.append({
        "stage": 1,
        "name": "Container & Bitstream Forensics",
        "duration_ms": st1_ms,
        "status": "PASSED" if not container_info.get("metadata_inconsistencies") else "SUSPICIOUS",
        "desc": f"Format: {container_info.get('container_format')} | Atoms: {len(container_info.get('atom_hierarchy', []))} | Screen capture: {'DETECTED' if screen_rec.get('screen_recording_detected') else 'NEGATIVE'}",
    })

    # ── Stage 2: Frame Sampling & Scene Detection ────────────────────────────────
    st2_start = time.perf_counter()
    frames_pil, video_meta = sample_video_frames(
        file_path,
        target_fps=settings.video_sample_fps,
        max_frames=settings.video_max_frames,
    )
    if not frames_pil:
        raise ValueError("No decodable frames found in video file.")

    scenes = detect_scenes_and_shots(frames_pil)
    st2_ms = int((time.perf_counter() - st2_start) * 1000)
    pipeline_modules.append({
        "stage": 2,
        "name": "Scene & Shot Boundary Segmentation",
        "duration_ms": st2_ms,
        "status": "PASSED",
        "desc": f"Sampled {len(frames_pil)} frames across {len(scenes)} distinct shots ({video_meta.get('duration_seconds', 0):.1f}s duration)",
    })

    # ── Stage 3: Spatial Facial & Generative AI Detection ────────────────────────
    st3_start = time.perf_counter()
    loaded = get_image_model()
    frame_scores: list[dict[str, Any]] = []
    frame_tensors: list[tuple[float, object, object]] = []
    np_frames: list[np.ndarray] = []
    face_boxes: list[tuple[int, int, int, int] | None] = []

    for timestamp_s, pil_frame in frames_pil:
        np_frames.append(np.array(pil_frame, dtype=np.uint8))
        crops = extract_faces(pil_frame)[:_MAX_FACES_PER_FRAME]
        crop = crops[0]

        face_boxes.append(crop.box)

        tensor = preprocess_image(crop.image, loaded.input_size).to(loaded.device)
        with torch.no_grad():
            prob = float(torch.sigmoid(loaded.module(tensor)).item())

        frame_scores.append({
            "frame_index": len(frame_scores),
            "timestamp_s": round(timestamp_s, 3),
            "fake_probability": round(prob, 4),
            "face_detected": crop.box is not None,
        })
        frame_tensors.append((timestamp_s, tensor, crop.image))

    # The face model is trained on face crops; on a frame without a face it
    # scores scenery, which is noise. Only frames with a detected face count.
    face_frames = [i for i, s in enumerate(frame_scores) if s["face_detected"]]
    if face_frames:
        worst_idx = max(face_frames, key=lambda i: frame_scores[i]["fake_probability"])
        worst_prob = float(frame_scores[worst_idx]["fake_probability"])
    else:
        worst_idx = len(frame_scores) // 2  # representative keyframe for scene analysis
        worst_prob = 0.0
    worst_pil = frames_pil[worst_idx][1]
    faces_in_any = len(face_frames)
    # The face model's score is shown per frame, but it only feeds the verdict
    # when a validated face model is configured (see settings.face_model_in_verdict).
    face_display_prob = worst_prob
    if not settings.face_model_in_verdict:
        worst_prob = 0.0

    # Full-scene generative-AI detectors on the worst frame — the same fused
    # ensemble the image pipeline uses. (This block used to call each
    # ensemble entry directly; entries are records, not callables, so every
    # call raised, the bare ``except`` swallowed it, and the score was 0.0.)
    vit_genai_prob = 0.0
    try:
        scene = score_scene(worst_pil)
        if scene["scene_ai_prob"] is not None:
            vit_genai_prob = float(scene["scene_ai_prob"])
        else:
            logger.warning("No scene detector available for video job %s; scene AI score omitted.", job_id)
    except Exception as exc:
        logger.warning("Scene AI detection on video keyframe failed: %s", exc)

    st3_ms = int((time.perf_counter() - st3_start) * 1000)
    pipeline_modules.append({
        "stage": 3,
        "name": "Spatial Neural & Generative AI Backbone",
        "duration_ms": st3_ms,
        "status": "AI_FLAGGED" if max(worst_prob, vit_genai_prob) >= 0.65 else "PASSED",
        "desc": f"Face score: {round(face_display_prob * 100, 1)}%{'' if settings.face_model_in_verdict else ' (informational)'} | Full-scene ViT GenAI: {round(vit_genai_prob * 100, 1)}%",
    })

    # ── Stage 4: Comprehensive 28-Module Image Forensics on Keyframe ─────────────
    st4_start = time.perf_counter()
    image_forensics = None
    try:
        keyframe_path = evidence_dir / f"{job_id}_keyframe.png"
        if not keyframe_path.exists():
            worst_pil.save(keyframe_path, format="PNG")
        worst_box_param = [face_boxes[worst_idx]] if face_boxes[worst_idx] is not None else None
        image_forensics = run_comprehensive_forensics(
            file_path=keyframe_path,
            image=worst_pil,
            evidence_dir=evidence_dir,
            job_id=f"{job_id}_frame",
            ai_scores={
                "ensemble_fake_prob": max(worst_prob, vit_genai_prob),
                "scene_ai_prob": vit_genai_prob,
                "face_fake_prob": worst_prob,
                "model_score": worst_prob,
                "vit_genai_score": vit_genai_prob,
            },
            face_boxes=worst_box_param,  # type: ignore
        )
    except Exception as exc:
        logger.warning("Comprehensive image forensics on video keyframe encountered error: %s", exc)

    st4_ms = int((time.perf_counter() - st4_start) * 1000)
    st4_status = "AI_FLAGGED" if image_forensics and image_forensics.get("camera_cfa", {}).get("synthetic_sensor_detected") else "PASSED"
    pipeline_modules.append({
        "stage": 4,
        "name": "28-Module Image Forensic Engine",
        "duration_ms": st4_ms,
        "status": st4_status,
        "desc": f"Evaluated CFA periodicity ({image_forensics.get('camera_cfa', {}).get('cfa_periodicity_ratio', 1.0) if image_forensics else 1.0}), Fourier radial slope alpha, ELA, and synthetic background matte voids",
    })

    # ── Stage 5: Temporal Jitter & Ocular Trajectory ─────────────────────────────
    st5_start = time.perf_counter()
    temporal_jitter = compute_temporal_jitter(face_boxes)
    facial_dynamics = analyze_facial_temporal_dynamics(frames_pil, face_boxes)
    st5_ms = int((time.perf_counter() - st5_start) * 1000)
    st5_bad = temporal_jitter >= 0.45 or facial_dynamics.get("landmark_jitter_score", 0.0) >= 0.40
    pipeline_modules.append({
        "stage": 5,
        "name": "Temporal Jitter & Facial Dynamics",
        "duration_ms": st5_ms,
        "status": "ANOMALY_DETECTED" if st5_bad else "PASSED",
        "desc": f"Bounding-box jitter: {temporal_jitter:.2f} | Landmark jitter: {facial_dynamics.get('landmark_jitter_score', 0):.2f} | Blinks: {facial_dynamics.get('blink_analysis', {}).get('blinks_detected', 0)}",
    })

    # ── Stage 6: Remote Photoplethysmography (rPPG) Cardiovascular Biometrics ───
    st6_start = time.perf_counter()
    rppg_info = extract_rppg_biometrics(frames_pil, face_boxes)
    st6_ms = int((time.perf_counter() - st6_start) * 1000)
    st6_status = "AI_FLAGGED" if rppg_info.get("is_synthetic_biometric_void") else ("PASSED" if rppg_info.get("biometric_pulse_detected") else "INCONCLUSIVE")
    pulse_summary = "CONFIRMED" if rppg_info.get("biometric_pulse_detected") else ("INCONCLUSIVE (Clip <8s)" if rppg_info.get("status") in ("INSUFFICIENT_FACE_SAMPLES", "INSUFFICIENT_SKIN_PATCHES") else "VOID/ABSENT")
    pipeline_modules.append({
        "stage": 6,
        "name": "Remote Photoplethysmography (rPPG) Biometrics",
        "duration_ms": st6_ms,
        "status": st6_status,
        "desc": f"Capillary pulse: {pulse_summary} | Heart rate: {rppg_info.get('estimated_heart_rate_bpm', 0.0)} BPM | Cardiac SNR: {rppg_info.get('cardiac_snr_db', 0.0)} dB",
    })

    # ── Stage 7: Spatio-Temporal 4D Tensor Dynamics ──────────────────────────────
    st7_start = time.perf_counter()
    spatiotemporal_info = analyze_spatiotemporal_tensor(frames_pil, face_boxes)
    st7_ms = int((time.perf_counter() - st7_start) * 1000)
    pipeline_modules.append({
        "stage": 7,
        "name": "Spatio-Temporal 4D Tensor Dynamics",
        "duration_ms": st7_ms,
        "status": spatiotemporal_info.get("status", "PASSED"),
        "desc": f"Anomaly score: {spatiotemporal_info.get('spatiotemporal_anomaly_score', 0.0):.2f} | Latent denoise jumps: {spatiotemporal_info.get('latent_noise_jump_rate', 0.0):.2f} | SlowFast vibration: {spatiotemporal_info.get('slowfast_boundary_vibration', 0.0):.2f}",
    })

    # ── Stage 8: LipForensics Phonetic Articulatory Dynamics ─────────────────────
    st8_start = time.perf_counter()
    lip_forensics_info = analyze_lip_forensics(frames_pil, face_boxes)
    st8_ms = int((time.perf_counter() - st8_start) * 1000)
    pipeline_modules.append({
        "stage": 8,
        "name": "LipForensics Articulatory Kinematics",
        "duration_ms": st8_ms,
        "status": lip_forensics_info.get("status", "PASSED"),
        "desc": f"Lip manipulation prob: {round(lip_forensics_info.get('lip_manipulation_probability', 0.0) * 100, 1)}% | Articulatory jerk: {lip_forensics_info.get('articulatory_jerk_anomaly', 0.0):.2f} | Oral texture stability: {lip_forensics_info.get('oral_cavity_texture_stability', 1.0):.2f}",
    })

    # ── Stage 9: Dense Optical Flow Motion Field ─────────────────────────────────
    st9_start = time.perf_counter()
    motion_score, motion_metrics = compute_optical_flow_anomaly(
        np_frames, face_boxes, evidence_dir=evidence_dir, job_id=job_id
    )
    st9_ms = int((time.perf_counter() - st9_start) * 1000)
    pipeline_modules.append({
        "stage": 9,
        "name": "Optical Flow Motion Decomposition",
        "duration_ms": st9_ms,
        "status": "ANOMALY_DETECTED" if motion_score >= 0.45 else "PASSED",
        "desc": f"Farneback flow anomaly: {motion_score:.3f} | Face/Background vector divergence: {motion_metrics.get('face_background_divergence', 0.0):.2f} px",
    })

    # ── Stage 10: Acoustic Voice & Cross-Modal Forensics ─────────────────────────
    st10_start = time.perf_counter()
    lipsync_info = analyze_crossmodal_lipsync(file_path, frames_pil, face_boxes)
    audio_forensics = None
    try:
        from app.ml.preprocessing import extract_audio_waveform

        audio_np, sr = extract_audio_waveform(file_path)
        if audio_np is not None and len(audio_np) > 0 and sr is not None:
            norm_wave = normalize_waveform(audio_np)
            from app.ml.audio import run_comprehensive_audio_forensics

            audio_forensics = run_comprehensive_audio_forensics(
                file_path=file_path,
                waveform=norm_wave,
                sample_rate=sr,
                evidence_dir=evidence_dir,
                job_id=f"{job_id}_audio",
            )
    except Exception as exc:
        logger.debug("Audio demuxing and acoustic forensics skipped: %s", exc)

    st10_ms = int((time.perf_counter() - st10_start) * 1000)
    st10_bad = lipsync_info.get("lip_sync_anomaly_detected", False) or (
        audio_forensics and audio_forensics.get("fusion_decision", {}).get("calibrated_fake_probability", 0.0) >= 0.65
    )
    pipeline_modules.append({
        "stage": 10,
        "name": "Acoustic Speech & Cross-Modal Lip-Sync",
        "duration_ms": st10_ms,
        "status": "ANOMALY_DETECTED" if st10_bad else "PASSED",
        "desc": f"Speech track: {'PRESENT' if lipsync_info.get('audio_stream_detected') else 'ABSENT'} | Audiovisual sync: {lipsync_info.get('audiovisual_correlation', 0.0):.2f} | Acoustic fake: {round(audio_forensics.get('fusion_decision', {}).get('calibrated_fake_probability', 0.0) * 100, 1) if audio_forensics else 0.0}%",
    })

    # ── Stage 11: AI Generator Attribution (No-Watermark Detection) ──────────────
    st11_start = time.perf_counter()
    attribution_info = analyze_generator_attribution(
        frames_pil=frames_pil,
        spatial_genai_prob=max(worst_prob, vit_genai_prob),
        optical_flow_score=motion_score,
        container_info=container_info,
    )
    st11_ms = int((time.perf_counter() - st11_start) * 1000)
    pipeline_modules.append({
        "stage": 11,
        "name": "AI Generator Attribution Engine",
        "duration_ms": st11_ms,
        "status": "AI_FLAGGED" if attribution_info.get("is_ai_generated") else "PASSED",
        "desc": f"Predicted origin: {attribution_info.get('predicted_platform')} ({round(attribution_info.get('attribution_confidence', 0) * 100, 1)}% confidence) | Detection without watermarks: ACTIVE",
    })

    duration_s = float(video_meta.get("duration_seconds", 10.0))

    # ── Multi-Modal Conformal Fusion ─────────────────────────────────────────────
    fusion = fuse_video_forensics(
        spatial_prob=worst_prob,
        frame_scores=frame_scores,
        temporal_jitter=temporal_jitter,
        motion_metrics=motion_metrics,
        compression_score=compression_score,
        container_info=container_info,
        facial_dynamics=facial_dynamics,
        lipsync_info=lipsync_info,
        scenes=scenes,
        duration_s=duration_s,
        vit_genai_prob=vit_genai_prob,
        image_forensics=image_forensics,
        audio_forensics=audio_forensics,
        attribution_info=attribution_info,
        rppg_info=rppg_info,
        spatiotemporal_info=spatiotemporal_info,
        lip_forensics_info=lip_forensics_info,
    )

    # ── Generate Visual Evidence Artifacts ───────────────────────────────────────
    heatmap_name: str | None = None
    try:
        _, worst_tensor, worst_crop = frame_tensors[worst_idx]
        cam = compute_gradcam(loaded.module, worst_tensor)
        heatmap_path = evidence_dir / f"{job_id}_heatmap.png"
        overlay_heatmap(worst_crop, cam, heatmap_path)
        heatmap_name = heatmap_path.name
    except Exception as exc:
        logger.warning("Grad-CAM failed for video job %s: %s", job_id, exc)

    chart_name: str | None = None
    try:
        chart_path = evidence_dir / f"{job_id}_timeline.png"
        _save_timeline_chart(frame_scores, chart_path)
        chart_name = chart_path.name
    except Exception as exc:
        logger.warning("Timeline chart failed for video job %s: %s", job_id, exc)

    total_processing_ms = int((time.perf_counter() - t0) * 1000)

    return AnalysisResult(
        fake_probability=fusion["final_probability"],
        model_name=f"{loaded.name} + Multi-Modal Video Forensic Suite",
        model_version=loaded.version,
        weights_status=loaded.weights_status,
        evidence={
            "media": "video",
            **video_meta,
            "frames_analysed": len(frame_scores),
            "faces_detected_in_frames": faces_in_any,
            "worst_frame_index": worst_idx,
            "worst_frame_timestamp_s": frame_scores[worst_idx]["timestamp_s"],
            "frame_scores": frame_scores,
            "risk_score": fusion["risk_score"],
            "risk_tier": fusion.get("risk_tier", "LOW_RISK"),
            "dominant_threat": fusion["dominant_threat"],
            "threat_code": fusion["threat_code"],
            "video_category": fusion.get("video_category", "Authentic Camera Recording"),
            "corroborating_signals": fusion["corroborating_signals"],
            "segment_timeline": fusion["segment_timeline"],
            "pipeline_modules": pipeline_modules,
            "container_forensics": container_info,
            "scenes": scenes,
            "facial_dynamics": facial_dynamics,
            "temporal_metrics": {
                "jitter_score": temporal_jitter,
                "motion_anomaly": motion_score,
                "compression_anomaly": compression_score,
                "face_bg_divergence": motion_metrics.get("face_background_divergence", 0.0),
                "optical_flow": motion_metrics,
            },
            "crossmodal_lipsync": lipsync_info,
            "image_forensics": image_forensics,
            "audio_forensics": audio_forensics,
            "generator_attribution": attribution_info,
            "rppg_biometrics": rppg_info,
            "spatiotemporal_forensics": spatiotemporal_info,
            "lip_forensics": lip_forensics_info,
            "vit_genai_prob": round(vit_genai_prob, 4),
            "heatmap_file": heatmap_name,
            "timeline_file": chart_name,
            "optical_flow_file": motion_metrics.get("flow_heatmap_file"),
            "backbone": f"{settings.image_model_backbone} + FrameAggregator + ImageForensics + AudioSentinel",
            "input_size": loaded.input_size,
            "notes": fusion["notes"],
            "processing_ms": total_processing_ms,
        },
    )


def _save_timeline_chart(frame_scores: list[dict[str, Any]], out_path: Path) -> None:
    """Render a multi-track per-frame confidence curve and save as PNG."""
    if not frame_scores:
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    timestamps = [s["timestamp_s"] for s in frame_scores]
    probs = [s["fake_probability"] for s in frame_scores]

    threshold_high = settings.fake_threshold + settings.uncertain_band
    threshold_low = settings.fake_threshold - settings.uncertain_band

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.fill_between(timestamps, probs, alpha=0.25, color="#ef4444")
    ax.plot(timestamps, probs, color="#ef4444", linewidth=2, label="AI Manipulation Probability")
    ax.axhline(
        threshold_high, color="#ef4444", linestyle="--",
        linewidth=1, alpha=0.7, label="Manipulated threshold",
    )
    ax.axhline(
        threshold_low, color="#22c55e", linestyle="--",
        linewidth=1, alpha=0.7, label="Authentic threshold",
    )
    ax.axhspan(threshold_low, threshold_high, alpha=0.07, color="#f59e0b", label="Inconclusive band")

    if frame_scores:
        worst = max(frame_scores, key=lambda s: s["fake_probability"])
        ax.axvline(worst["timestamp_s"], color="#ef4444", linewidth=1, alpha=0.5, linestyle=":")
        ax.annotate(
            f"worst: {worst['fake_probability']:.2f}",
            xy=(worst["timestamp_s"], worst["fake_probability"]),
            xytext=(worst["timestamp_s"] + 0.2, worst["fake_probability"] - 0.1),
            fontsize=8, color="#ef4444",
        )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Fake probability")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Per-Frame Temporal Forensic Confidence Timeline")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(str(out_path), dpi=120, bbox_inches="tight")
    plt.close(fig)
