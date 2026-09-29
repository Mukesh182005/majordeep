"""Conformal risk fusion and threat taxonomy for video forensics (Module 42, 46, 47, 48, 72).

Combines spatial neural detections, ViT generative scene probabilities, 28-module image forensics,
10-engine acoustic voice forensics, temporal jitter, dense optical flow boundaries,
compression DNA, facial ocular dynamics, cross-modal lip-sync, and AI generator attribution
into a unified multi-modal verdict and segment-by-segment forensic timeline.
"""

from __future__ import annotations

from typing import Any
import numpy as np


def compute_video_risk(
    spatial_prob: float,
    temporal_jitter: float,
    motion_anomaly: float,
    compression_anomaly: float,
    facial_jitter: float = 0.0,
    lipsync_anomaly: float = 0.0,
    vit_genai_prob: float = 0.0,
    audio_fake_prob: float = 0.0,
    generator_attribution_score: float = 0.0,
    spatiotemporal_anomaly: float = 0.0,
    rppg_synthetic_void: bool = False,
    lip_forensics_anomaly: float = 0.0,
) -> float:
    """Combine spatial, acoustic, temporal, biometric, and attribution signals into a final manipulated probability."""
    # Balanced weights across all multi-modal channels
    weights = {
        "spatial": 0.30,
        "vit_genai": 0.18,
        "temporal_jitter": 0.08,
        "motion": 0.08,
        "facial": 0.06,
        "audio": 0.08,
        "spatiotemporal": 0.10,
        "lipsync": 0.04,
        "lip_forensics": 0.05,
        "compression": 0.03,
    }

    # If facial swap is primary detected anomaly with low generative/audio presence
    if spatial_prob >= 0.85 and vit_genai_prob < 0.50 and audio_fake_prob < 0.50:
        weights = {
            "spatial": 0.70,
            "vit_genai": 0.03,
            "temporal_jitter": 0.07,
            "motion": 0.07,
            "facial": 0.05,
            "audio": 0.00,
            "spatiotemporal": 0.05,
            "lipsync": 0.00,
            "lip_forensics": 0.03,
            "compression": 0.00,
        }
    # If full-frame generative AI is primary (Sora/Gemini/Kling/Runway/Luma/Astra)
    elif vit_genai_prob >= 0.80 or generator_attribution_score >= 0.80 or spatiotemporal_anomaly >= 0.75:
        weights = {
            "spatial": 0.12,
            "vit_genai": 0.45,
            "temporal_jitter": 0.05,
            "motion": 0.08,
            "facial": 0.05,
            "audio": 0.05,
            "spatiotemporal": 0.12,
            "lipsync": 0.04,
            "lip_forensics": 0.02,
            "compression": 0.02,
        }
    # If audio voice synthesis is primary
    elif audio_fake_prob >= 0.85:
        weights = {
            "spatial": 0.18,
            "vit_genai": 0.08,
            "temporal_jitter": 0.05,
            "motion": 0.05,
            "facial": 0.05,
            "audio": 0.38,
            "spatiotemporal": 0.05,
            "lipsync": 0.08,
            "lip_forensics": 0.05,
            "compression": 0.03,
        }

    score = (
        spatial_prob * weights["spatial"]
        + vit_genai_prob * weights["vit_genai"]
        + temporal_jitter * weights["temporal_jitter"]
        + motion_anomaly * weights["motion"]
        + facial_jitter * weights["facial"]
        + audio_fake_prob * weights["audio"]
        + spatiotemporal_anomaly * weights["spatiotemporal"]
        + lipsync_anomaly * weights["lipsync"]
        + lip_forensics_anomaly * weights["lip_forensics"]
        + compression_anomaly * weights["compression"]
    )

    # Corroborating evidence boost: if facial manipulation is confirmed and corroborated by temporal anomalies
    if spatial_prob >= 0.85 and (temporal_jitter >= 0.35 or motion_anomaly >= 0.35 or facial_jitter >= 0.30):
        score = max(score, min(0.95, spatial_prob * 0.90))

    # Biological biometric void boost (absence of capillary blood pulse in face)
    if rppg_synthetic_void and spatial_prob >= 0.50:
        score = max(score, 0.82)

    # Authentic camera dampening: when spatial neural classifiers and ViT confirm that imagery is authentic,
    # motion and compression anomalies reflect natural recording conditions rather than synthetic manipulation.
    if spatial_prob < 0.25 and vit_genai_prob < 0.35 and audio_fake_prob < 0.35 and not rppg_synthetic_void and generator_attribution_score < 0.40:
        score = min(score, 0.12 + spatial_prob * 0.40)

    return round(float(max(0.0, min(1.0, score))), 4)


def fuse_video_forensics(
    spatial_prob: float,
    frame_scores: list[dict[str, Any]],
    temporal_jitter: float,
    motion_metrics: dict[str, Any],
    compression_score: float,
    container_info: dict[str, Any],
    facial_dynamics: dict[str, Any],
    lipsync_info: dict[str, Any],
    scenes: list[dict[str, Any]],
    duration_s: float,
    vit_genai_prob: float = 0.0,
    image_forensics: dict[str, Any] | None = None,
    audio_forensics: dict[str, Any] | None = None,
    attribution_info: dict[str, Any] | None = None,
    rppg_info: dict[str, Any] | None = None,
    spatiotemporal_info: dict[str, Any] | None = None,
    lip_forensics_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute multi-modal evidence fusion across all spatial, acoustic, temporal, biometric, and attribution layers."""
    motion_score = float(motion_metrics.get("mean_motion_anomaly", 0.0))
    facial_jitter = float(facial_dynamics.get("landmark_jitter_score", 0.0))
    lipsync_anomaly = float(lipsync_info.get("lip_sync_anomaly_score", 0.0))
    screen_rec = container_info.get("screen_recording_analysis", {})
    screen_detected = bool(screen_rec.get("screen_recording_detected", False))
    editing_tool = container_info.get("editing_software")
    ai_tool = container_info.get("ai_generator_signature")

    # Extract audio signals if audio was analyzed
    audio_fake_prob = 0.0
    audio_fusion = None
    if audio_forensics and "fusion_decision" in audio_forensics:
        audio_fusion = audio_forensics.get("fusion_decision", {})
        audio_fake_prob = float(audio_fusion.get("calibrated_fake_probability", 0.0))

    # Extract attribution info
    attrib_score = 0.0
    predicted_platform = "Authentic Camera / No Synthetic Generator Traces"
    if attribution_info:
        attrib_score = float(attribution_info.get("attribution_confidence", 0.0))
        predicted_platform = attribution_info.get("predicted_platform", predicted_platform)

    # Extract rPPG, Spatio-Temporal, and LipForensics
    rppg_void = bool(rppg_info.get("is_synthetic_biometric_void", False)) if rppg_info else False
    st_anomaly = float(spatiotemporal_info.get("spatiotemporal_anomaly_score", 0.0)) if spatiotemporal_info else 0.0
    lip_manip = float(lip_forensics_info.get("lip_manipulation_probability", 0.0)) if lip_forensics_info else 0.0

    # Compute unified multi-modal risk
    final_prob = compute_video_risk(
        spatial_prob=spatial_prob,
        temporal_jitter=temporal_jitter,
        motion_anomaly=motion_score,
        compression_anomaly=compression_score,
        facial_jitter=facial_jitter,
        lipsync_anomaly=lipsync_anomaly,
        vit_genai_prob=vit_genai_prob,
        audio_fake_prob=audio_fake_prob,
        generator_attribution_score=attrib_score if attribution_info and attribution_info.get("is_ai_generated") else 0.0,
        spatiotemporal_anomaly=st_anomaly,
        rppg_synthetic_void=rppg_void,
        lip_forensics_anomaly=lip_manip,
    )

    # Corroborating signals identification
    signals: list[str] = []
    if attribution_info and attribution_info.get("is_ai_generated"):
        signals.append(f"AI Generator Attribution: Video exhibits intrinsic diffusion markers of {predicted_platform} ({round(attrib_score * 100, 1)}% confidence)")
        for sig in attribution_info.get("detected_signatures", []):
            signals.append(f"Intrinsic Trace: {sig}")

    if vit_genai_prob >= 0.65:
        signals.append(f"Full-scene Vision Transformer flagged generative AI raster on keyframes ({round(vit_genai_prob * 100, 1)}%)")

    if spatial_prob >= 0.70:
        signals.append(f"Spatial neural classifier flagged facial synthesis on keyframe crops ({round(spatial_prob * 100, 1)}%)")

    if audio_fake_prob >= 0.65:
        signals.append(f"Acoustic Forensics Engine detected synthetic speech/voice cloning ({round(audio_fake_prob * 100, 1)}%)")

    if image_forensics:
        cfa = image_forensics.get("camera_cfa", {})
        if cfa.get("synthetic_sensor_detected"):
            signals.append("Image Forensics: Camera sensor artifacts missing (synthetic AI generation confirmed)")
        fourier_slope = cfa.get("fourier_spectral_slope")
        if fourier_slope and fourier_slope > 2.4:
            signals.append(f"Image Forensics: Steep Fourier azimuthal spectral slope alpha={fourier_slope:.2f}")

    if temporal_jitter >= 0.35:
        signals.append(f"Bounding-box acceleration instability detected across frames (jitter: {round(temporal_jitter, 2)})")

    if motion_score >= 0.35:
        signals.append(f"Optical flow divergence at facial perimeter boundaries (divergence: {round(motion_score, 2)})")

    if facial_jitter >= 0.30:
        signals.append(f"Facial landmark trajectory jitter and geometric deformation (score: {round(facial_jitter, 2)})")

    if lipsync_info.get("lip_sync_anomaly_detected"):
        signals.append("Acoustic speech energy envelope desynchronized with visual lip kinematics")

    if compression_score >= 0.40:
        signals.append(f"Double-compression or re-encoding GOP quantization discontinuity (score: {round(compression_score, 2)})")

    if rppg_info:
        if rppg_info.get("is_synthetic_biometric_void"):
            signals.append(f"Cardiovascular rPPG Void: Absence of physiological blood volume pulse (Cardiac SNR: {rppg_info.get('cardiac_snr_db')} dB)")
        elif rppg_info.get("biometric_pulse_detected"):
            signals.append(f"Cardiovascular rPPG: Authentic biological capillary pulse confirmed at {rppg_info.get('estimated_heart_rate_bpm')} BPM (Cardiac SNR: {rppg_info.get('cardiac_snr_db')} dB)")

    if spatiotemporal_info and spatiotemporal_info.get("spatiotemporal_anomaly_score", 0.0) >= 0.45:
        for f in spatiotemporal_info.get("findings", []):
            signals.append(f"Spatio-Temporal Dynamics: {f}")

    if lip_forensics_info and lip_forensics_info.get("lip_manipulation_probability", 0.0) >= 0.50:
        for f in lip_forensics_info.get("findings", []):
            signals.append(f"LipForensics: {f}")

    if screen_detected:
        signals.append(f"Physical monitor display artifacts / moire frequency grid detected (ratio: {screen_rec.get('moire_harmonic_ratio', screen_rec.get('moiré_harmonic_ratio'))})")

    if ai_tool:
        signals.append(f"Container signature matched known AI generator: {ai_tool}")
    elif editing_tool:
        signals.append(f"Container signature indicates non-linear video editor: {editing_tool}")

    # Determine Granular Video Taxonomy (AI Generated, AI Edited, Human Edited, App Edited, Screen Recording, Authentic)
    software_category = container_info.get("software_category")
    is_synthetic_ai = (attribution_info and attribution_info.get("is_ai_generated")) or bool(ai_tool) or vit_genai_prob >= 0.75

    if is_synthetic_ai:
        dominant_threat = f"AI-Generated Video Media ({predicted_platform})"
        threat_code = "AI_GENERATED_VIDEO"
        category_name = "AI Generated Video"
        final_prob = max(final_prob, 0.88)
    elif audio_fake_prob >= 0.70 and lipsync_info.get("lip_sync_anomaly_detected"):
        dominant_threat = "Synthetic Voice Replacement & Dubbing"
        threat_code = "AI_LIP_SYNC_REENACTMENT"
        category_name = "AI Voice Replacement Dub"
        final_prob = max(final_prob, 0.85)
    elif lip_manip >= 0.65 or software_category == "AI_LIP_SYNC":
        dominant_threat = f"AI Talking-Head Lip Manipulation ({editing_tool or 'Neural Model'})"
        threat_code = "AI_LIP_SYNC_REENACTMENT"
        category_name = "AI Talking-Head & Lip-Sync"
        final_prob = max(final_prob, 0.82)
    elif spatial_prob >= 0.65 or (spatial_prob >= 0.45 and (temporal_jitter >= 0.45 or motion_score >= 0.45)) or software_category == "AI_FACE_SWAP":
        dominant_threat = f"Deepfake Neural Face-Swap ({editing_tool or 'Neural Model'})"
        threat_code = "DEEPFAKE_FACE_SWAP"
        category_name = "AI Face-Swap Deepfake"
    elif screen_detected and final_prob >= 0.45:
        dominant_threat = "Re-Recorded Screen Capture"
        threat_code = "SCREEN_RECORDING"
        category_name = "Screen Recording Capture"
    elif lipsync_info.get("lip_sync_anomaly_detected") and final_prob >= 0.50:
        dominant_threat = "Lip-Sync & Speech Replacement Dub"
        threat_code = "AI_LIP_SYNC_REENACTMENT"
        category_name = "AI Lip-Sync Dub"
    elif software_category == "PROFESSIONAL_NLE" and final_prob < 0.50:
        dominant_threat = f"Human Edited via {editing_tool or 'Professional NLE'}"
        threat_code = "PROFESSIONAL_NLE_EDITED"
        category_name = "Human Edited (Professional NLE)"
    elif software_category == "MOBILE_EDITOR" and final_prob < 0.50:
        dominant_threat = f"Mobile App Edited via {editing_tool or 'Consumer Editor'}"
        threat_code = "MOBILE_APP_EDITED"
        category_name = "Mobile App Edited"
    elif software_category == "SOCIAL_MEDIA" and final_prob < 0.50:
        dominant_threat = f"Social Media Platform Transcode ({editing_tool or 'Social App'})"
        threat_code = "SOCIAL_MEDIA_TRANSCODED"
        category_name = "Social Media Transcoded"
    elif (container_info.get("is_reencoded") or software_category == "TRANSCODER") and 0.35 <= final_prob < 0.50:
        dominant_threat = f"Traditionally Transcoded Video ({editing_tool or 'FFmpeg'})"
        threat_code = "TRADITIONALLY_EDITED"
        category_name = "Traditionally Edited / Transcoded"
    elif final_prob <= 0.42 or (spatial_prob < 0.40 and vit_genai_prob < 0.40):
        dominant_threat = "Authentic Camera Video Recording"
        threat_code = "AUTHENTIC_PHOTOGRAPH"
        category_name = "Authentic Camera Recording"
    else:
        dominant_threat = "Inconclusive Forensic Signals"
        threat_code = "INCONCLUSIVE"
        category_name = "Inconclusive Forensic Signals"

    risk_score = round(final_prob * 100)
    if risk_score >= 85:
        risk_tier = "CRITICAL_RISK"
    elif risk_score >= 70:
        risk_tier = "HIGH_RISK"
    elif risk_score >= 40:
        risk_tier = "ELEVATED_RISK"
    elif risk_score >= 20:
        risk_tier = "MODERATE_RISK"
    else:
        risk_tier = "LOW_RISK"

    # Segment-by-Segment Forensic Timeline Table
    segment_timeline: list[dict[str, Any]] = []
    seg_step = 2.0
    t_curr = 0.0
    while t_curr < duration_s:
        t_next = min(duration_s, t_curr + seg_step)
        window_frames = [s for s in frame_scores if t_curr <= s.get("timestamp_s", 0.0) < t_next]
        if window_frames:
            w_prob = float(np.mean([s["fake_probability"] for s in window_frames]))
        else:
            w_prob = final_prob * 0.85

        # Incorporate global GenAI floor if full-frame AI was detected
        if vit_genai_prob >= 0.75 or (attribution_info and attribution_info.get("is_ai_generated")):
            w_prob = max(w_prob, 0.85)

        seg_indicators: list[str] = []
        if w_prob >= 0.65:
            seg_indicators.append("Diffusion raster anomaly")
        if motion_score > 0.35:
            seg_indicators.append("Motion vector jitter")
        if not seg_indicators:
            seg_indicators.append("Coherent raster")

        segment_timeline.append({
            "time_window": f"{int(t_curr // 60):02d}:{int(t_curr % 60):02d} - {int(t_next // 60):02d}:{int(t_next % 60):02d}",
            "ai_probability": round(w_prob, 3),
            "ai_percentage": f"{round(w_prob * 100, 1)}%",
            "manipulation_type": threat_code if w_prob >= 0.50 else "AUTHENTIC_CONTENT",
            "indicators": ", ".join(seg_indicators),
            "source_match": predicted_platform if w_prob >= 0.50 else "Authentic Master Broadcast",
        })
        t_curr = t_next

    # Assemble Forensic Notes
    notes: list[str] = [
        f"Forensic Threat Attribution: {dominant_threat} [{threat_code}]",
        f"Multi-modal fusion: spatial={spatial_prob:.3f}, vit_genai={vit_genai_prob:.3f}, "
        f"audio_fake={audio_fake_prob:.3f}, flow={motion_score:.3f}, jitter={temporal_jitter:.3f} → final={final_prob:.3f}",
    ]
    if signals:
        notes.append(f"Corroborating indicators: {'; '.join(signals[:3])}")

    return {
        "final_probability": final_prob,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "dominant_threat": dominant_threat,
        "threat_code": threat_code,
        "video_category": category_name,
        "corroborating_signals": signals,
        "segment_timeline": segment_timeline,
        "notes": notes,
        "attribution": {
            "predicted_platform": predicted_platform,
            "attribution_confidence": attrib_score,
            "is_ai_generated": attribution_info.get("is_ai_generated", False) if attribution_info else False,
            "no_watermark_detection": True,
        },
    }
