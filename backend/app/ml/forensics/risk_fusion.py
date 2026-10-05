"""Risk scoring engine and multi-signal evidence fusion (Modules 21 & 22)."""

from __future__ import annotations

from typing import Any


def compute_risk_and_fusion(
    ai_scores: dict[str, Any],
    tampering: dict[str, Any],
    ela: dict[str, Any],
    stego: dict[str, Any],
    file_security: dict[str, Any],
    metadata: dict[str, Any],
    provenance: dict[str, Any],
    camera_stats: dict[str, Any] | None = None,
    watermark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compute multi-signal calibrated Image Security Risk Score (0-100) and perform Evidence Fusion.
    """
    watermark = watermark or {}
    camera_stats = camera_stats or {}
    fswap = tampering.get("face_swap", {})

    # 1. Individual Dimension Scores (0.0 to 100.0)
    ai_gen_prob = float(ai_scores.get("ensemble_fake_prob", 0.0))
    scene_ai_prob = float(ai_scores.get("scene_ai_prob", 0.0))
    face_fake_prob = float(ai_scores.get("face_fake_prob", 0.0))

    # Evaluate AI generation component from full-scene ViT, facial models, and ensemble
    ai_component = round(max(ai_gen_prob, scene_ai_prob, face_fake_prob) * 100.0, 1)

    # Physical Sensor / CFA correlation:
    synthetic_sensor = camera_stats.get("synthetic_sensor_detected", False) or (
        camera_stats.get("cfa_periodicity_ratio", 3.0) < 1.65 and not camera_stats.get("cfa_artifacts_detected", False)
    ) or (camera_stats.get("sensor_noise_std", 2.0) < 0.60) or (camera_stats.get("fourier_spectral_slope", 2.0) < 1.30)
    camera_make_str = str(metadata.get("camera_make", "")).strip().lower()
    camera_unknown = (not metadata.get("exif_present", False)) or any(
        camera_make_str.startswith(k) for k in ("unknown", "unspecified", "none")
    ) or camera_make_str == ""

    # Combine AI generation scores from ViT scene detector, facial models, and ensemble
    ai_component = round(max(ai_gen_prob, scene_ai_prob, face_fake_prob) * 100.0, 1)

    # Positive authenticity evidence: traces a camera leaves that generators do
    # not. A low face-model score is not one — that model only knows StyleGAN
    # faces and scores modern AI faces as real — nor is a "natural" spectral
    # slope, which textured AI renders also produce.
    authentic_signals = 0
    if camera_stats.get("cfa_artifacts_detected", False):
        authentic_signals += 1
    if metadata.get("exif_present", False) and not camera_unknown:
        authentic_signals += 1

    # Boost AI score if genuine synthetic sensor is detected with supportive AI model probability
    if synthetic_sensor and (scene_ai_prob >= 0.60 or ai_gen_prob >= 0.60):
        ai_component = max(ai_component, 86.0)
    elif scene_ai_prob >= 0.50:
        ai_component = max(ai_component, round(scene_ai_prob * 100.0, 1))


    # Watermark influence
    if watermark.get("watermark_detected"):
        w_type = watermark.get("watermark_type")
        if w_type == "AI_GENERATOR_STAMP":
            ai_component = max(ai_component, 96.0)
        elif w_type == "FREQUENCY_WATERMARK":
            ai_component = max(ai_component, 85.0)
        elif w_type in ("VISIBLE_LOGO_BADGE", "SEMI_TRANSPARENT_OVERLAY") and (ai_gen_prob >= 0.45 or scene_ai_prob >= 0.50):
            ai_component = max(ai_component, 82.0)

    # Tampering component
    tampering_component = 0.0
    if fswap.get("face_swap_detected"):
        # Unvalidated heuristic (fires on ~30% of real portraits): moderate weight only.
        tampering_component = max(tampering_component, 40.0)
    if tampering.get("copy_move_detected"):
        tampering_component = max(tampering_component, 75.0 if tampering.get("cloned_feature_pairs", 0) >= 8 else 50.0)
    if tampering.get("synthetic_matte_detected"):
        tampering_component = max(tampering_component, 82.0)
    if tampering.get("splicing_detected"):
        tampering_component = max(tampering_component, 75.0)
    if ela.get("compression_anomaly_detected"):
        tampering_component += 20.0
    if watermark.get("watermark_detected") and watermark.get("watermark_type") in ("VISIBLE_LOGO_BADGE", "SEMI_TRANSPARENT_OVERLAY"):
        tampering_component = max(tampering_component, 45.0)

    tampering_component = round(min(tampering_component, 100.0), 1)

    # Metadata component
    metadata_component = 0.0
    if metadata.get("ai_metadata_detected"):
        metadata_component += 80.0
    if metadata.get("editing_software_detected"):
        metadata_component += 50.0
    if metadata.get("timeline_consistency") in ("ANOMALOUS_FUTURE_TIMESTAMP", "MODIFIED_BY_EDITOR"):
        metadata_component += 30.0
    if camera_unknown and synthetic_sensor and (scene_ai_prob >= 0.45 or ai_gen_prob >= 0.45 or tampering.get("synthetic_matte_detected")):
        metadata_component = max(metadata_component, 65.0)
    metadata_component = round(min(metadata_component, 100.0), 1)

    # Steganography component
    stego_component = round(float(stego.get("suspicion_percentage", 0.0)), 1)

    # File anomaly component
    file_component = 0.0
    if file_security.get("embedded_objects"):
        file_component += 75.0
    if file_security.get("trailing_data_detected"):
        file_component += 45.0
    if file_security.get("extension_mismatch"):
        file_component += 50.0
    if not file_security.get("structure_valid"):
        file_component += 40.0
    file_component = round(min(file_component, 100.0), 1)

    # Provenance component
    provenance_component = 15.0 if not provenance.get("c2pa_detected") else 0.0

    # 2. Calibrated Overall Risk Score (0 - 100)
    weights = {
        "ai": 0.30,
        "tampering": 0.25,
        "file": 0.15,
        "metadata": 0.15,
        "stego": 0.10,
        "provenance": 0.05,
    }

    raw_risk = (
        ai_component * weights["ai"]
        + tampering_component * weights["tampering"]
        + file_component * weights["file"]
        + metadata_component * weights["metadata"]
        + stego_component * weights["stego"]
        + provenance_component * weights["provenance"]
    )

    if provenance.get("ai_generation_disclosed"):
        ai_component = max(ai_component, 98.0)
        raw_risk = max(raw_risk, 95.0)

    # High risk tracks a detection, not the CFA/noise heuristics (true for
    # most real web photos) or a matte on its own.
    if scene_ai_prob >= 0.65 or ai_gen_prob >= 0.65:
        raw_risk = max(raw_risk, 82.0)
    if tampering.get("synthetic_matte_detected") and scene_ai_prob >= 0.65:
        raw_risk = max(raw_risk, 86.0)

    if provenance.get("threat_intel", {}).get("threat_level") in ("HIGH", "ELEVATED"):
        raw_risk = max(raw_risk, 85.0)

    overall_risk_score = round(int(min(max(raw_risk, 0.0), 100.0)))

    if overall_risk_score >= 70:
        risk_tier = "CRITICAL_RISK" if overall_risk_score >= 85 else "HIGH_RISK"
    elif overall_risk_score >= 40:
        risk_tier = "ELEVATED_RISK"
    elif overall_risk_score >= 20:
        risk_tier = "MODERATE_RISK"
    else:
        risk_tier = "LOW_RISK"

    # 3. Evidence Correlation & Fusion Engine (Module 22)
    # Only signals that separate real from AI images are counted. Measured on
    # 196 real photos / 341 AI images, several former "signals" fired at
    # chance and are kept as context instead: no CFA trace (100% of real JPEG
    # photos), missing camera EXIF (most web images), the Fourier/wavelet
    # artifact (50% of real vs 47% of AI), the face-seam heuristic (30% of real
    # faces vs 27% of AI faces) and a black/chroma matte (2.0% vs 1.8%).
    # Counting them made one detector score look like "3 independent signals".
    corroborating_signals = []
    context_signals = []
    if provenance.get("ai_generation_disclosed"):
        gen_name = provenance.get("disclosed_generator") or "C2PA Disclosed Generative AI"
        corroborating_signals.append(f"Content Credentials / Provenance ({gen_name})")

    if ai_gen_prob >= 0.60 or scene_ai_prob >= 0.55:
        corroborating_signals.append(f"AI Generative Pattern (scene detectors: {round(max(ai_gen_prob, scene_ai_prob)*100, 1)}%)")

    if metadata.get("ai_metadata_detected"):
        corroborating_signals.append(f"AI Generator Metadata ({metadata.get('ai_generator_name') or 'generator parameters'})")

    if watermark.get("watermark_detected"):
        w_type = watermark.get("watermark_type")
        subtype = watermark.get("subtype", "Watermark")
        if w_type == "AI_GENERATOR_STAMP":
            corroborating_signals.append(f"AI Watermark Stamp ({subtype})")
        elif w_type in ("VISIBLE_LOGO_BADGE", "SEMI_TRANSPARENT_OVERLAY"):
            corroborating_signals.append(f"Visible Watermark ({subtype})")
        elif w_type == "FREQUENCY_WATERMARK":
            corroborating_signals.append(f"Digital Frequency Watermark ({subtype})")

    if tampering.get("copy_move_detected") and tampering.get("cloned_feature_pairs", 0) >= 12:
        corroborating_signals.append(f"Pixel Cloning / Copy-Move Duplication ({tampering.get('cloned_feature_pairs', 0)} keypoints)")

    if ela.get("compression_anomaly_detected"):
        corroborating_signals.append("Compression ELA Divergence")
    if stego.get("payload_likelihood") in ("HIGH", "MEDIUM"):
        corroborating_signals.append("Statistical Stego / LSB Anomaly")
    if file_security.get("embedded_objects"):
        corroborating_signals.append("Container Structural Payload (Embedded Objects)")
    elif file_security.get("trailing_data_detected") and file_security.get("trailing_bytes_count", 0) > 100:
        # Small trailing data (<= 100 bytes) is common from WhatsApp/social media recompression
        corroborating_signals.append("Container Structural Payload (Significant Trailing Data)")

    if not camera_stats.get("cfa_artifacts_detected", False):
        context_signals.append("No camera CFA demosaicing trace (normal after resizing/recompression)")
    if camera_unknown:
        context_signals.append("No camera make/model in metadata")
    if metadata.get("editing_software_detected"):
        context_signals.append(f"Edited with {metadata.get('software', 'editing software')}")
    if tampering.get("synthetic_matte_detected"):
        context_signals.append("Flat black/chroma background region (matte)")
    if fswap.get("face_swap_detected"):
        context_signals.append("Face-region inconsistency heuristic fired (unvalidated)")

    signal_count = len(corroborating_signals)
    if signal_count >= 3:
        fusion_verdict = "MULTI_SIGNAL_CONSENSUS_MANIPULATION"
        fusion_confidence = "VERY_HIGH"
    elif signal_count >= 2:
        fusion_verdict = "CORROBORATED_MANIPULATION"
        fusion_confidence = "HIGH"
    elif signal_count == 1:
        if provenance.get("ai_generation_disclosed"):
            fusion_verdict = "CORROBORATED_MANIPULATION"
            fusion_confidence = "HIGH"
        else:
            fusion_verdict = "ISOLATED_ANOMALY"
            fusion_confidence = "MODERATE"
    elif authentic_signals:
        fusion_verdict = "CONSISTENT_AUTHENTIC_SIGNALS"
        fusion_confidence = "HIGH"
    else:
        # Nothing flagged, but nothing camera-specific confirmed either:
        # absence of detected manipulation is not evidence of authenticity.
        fusion_verdict = "NO_MANIPULATION_SIGNALS_DETECTED"
        fusion_confidence = "LOW"

    # 4. Granular Threat Taxonomy Assignment
    if tampering.get("synthetic_matte_detected") and scene_ai_prob >= 0.45:
        dominant_threat = "Synthetic Background / Inpainting Matte"
        threat_code = "SYNTHETIC_BACKGROUND_REPLACEMENT"
    elif ai_gen_prob >= 0.50 or scene_ai_prob >= 0.45 or (synthetic_sensor and scene_ai_prob >= 0.35) or provenance.get("ai_generation_disclosed"):
        gen_label = provenance.get("disclosed_generator") or metadata.get("ai_generator_name") or "Diffusion / Neural Generator"
        dominant_threat = f"Synthetic AI Generation ({gen_label})"
        threat_code = "SYNTHETIC_AI_GENERATION"
    elif tampering.get("copy_move_detected"):
        dominant_threat = "Cloning / Photographic Splicing"
        threat_code = "SPLICING_TAMPERING"
    else:
        dominant_threat = "Authentic Camera Photograph"
        threat_code = "AUTHENTIC_PHOTOGRAPH"

    return {
        "overall_risk_score": overall_risk_score,
        "risk_tier": risk_tier,
        "dominant_threat": dominant_threat,
        "threat_code": threat_code,
        "dimension_breakdown": {
            "ai_generation": ai_component,
            "tampering_splicing": tampering_component,
            "file_security": file_component,
            "metadata_timeline": metadata_component,
            "stego": stego_component,
            "provenance_penalty": provenance_component,
        },
        "evidence_fusion": {
            "fusion_verdict": fusion_verdict,
            "fusion_confidence": fusion_confidence,
            "dominant_threat": dominant_threat,
            "threat_code": threat_code,
            "corroborating_signals": corroborating_signals,
            "context_signals": context_signals,
            "orthogonal_signals_count": signal_count,
        },
    }
