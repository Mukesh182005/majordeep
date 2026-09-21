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
    faces_count = int(ai_scores.get("faces_count", 0))

    # Evaluate AI generation component from full-scene ViT, facial models, and ensemble
    ai_component = round(max(ai_gen_prob, scene_ai_prob, face_fake_prob) * 100.0, 1)

    # Physical Sensor / CFA correlation:
    synthetic_sensor = camera_stats.get("synthetic_sensor_detected", False) or (
        camera_stats.get("cfa_periodicity_ratio", 3.0) < 1.8 and camera_stats.get("sensor_noise_std", 2.0) < 1.8
    ) or (camera_stats.get("sensor_noise_std", 2.0) < 0.60)
    camera_make_str = str(metadata.get("camera_make", "")).strip().lower()
    camera_unknown = (not metadata.get("exif_present", False)) or any(
        camera_make_str.startswith(k) for k in ("unknown", "unspecified", "none")
    ) or camera_make_str == ""

    if synthetic_sensor and (scene_ai_prob >= 0.22 or ai_gen_prob >= 0.22 or camera_unknown):
        ai_component = max(ai_component, 85.0)
    elif scene_ai_prob >= 0.22:
        ai_component = max(ai_component, 78.0)

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
        tampering_component = max(tampering_component, 85.0)
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
    if camera_unknown and synthetic_sensor and (scene_ai_prob >= 0.20 or ai_gen_prob >= 0.20 or tampering.get("synthetic_matte_detected")):
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

    if synthetic_sensor and (scene_ai_prob >= 0.22 or ai_gen_prob >= 0.22):
        raw_risk = max(raw_risk, 82.0)
    if tampering.get("synthetic_matte_detected") and (scene_ai_prob >= 0.20 or synthetic_sensor):
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
    corroborating_signals = []
    if provenance.get("ai_generation_disclosed"):
        gen_name = provenance.get("disclosed_generator") or "C2PA Disclosed Generative AI"
        corroborating_signals.append(f"Content Credentials / Provenance ({gen_name})")

    if fswap.get("face_swap_detected"):
        corroborating_signals.append(f"Deepfake Face-Swap Blending ({', '.join(fswap.get('anomalies', []))})")

    if ai_gen_prob >= 0.50 or scene_ai_prob >= 0.22:
        corroborating_signals.append(f"AI Generative Pattern (ViT / Diffusion Probe: {round(max(ai_gen_prob, scene_ai_prob)*100, 1)}%)")

    if synthetic_sensor and (scene_ai_prob >= 0.20 or ai_gen_prob >= 0.20 or (watermark.get("watermark_detected") and watermark.get("watermark_type") == "AI_GENERATOR_STAMP") or tampering.get("synthetic_matte_detected")):
        corroborating_signals.append("Missing Physical Bayer CFA Grid (Synthetic Sensor Footprint)")

    if camera_unknown and synthetic_sensor and (scene_ai_prob >= 0.20 or ai_gen_prob >= 0.20 or tampering.get("synthetic_matte_detected")):
        corroborating_signals.append("Missing Camera Hardware EXIF (Typical of AI Generation)")

    if tampering.get("synthetic_matte_detected"):
        corroborating_signals.append("Synthetic Background Alpha / Blackout Matte (Digital Composition)")

    if camera_stats.get("wavelet_grid_peak_ratio", 1.0) > 6.5 or (camera_stats.get("fourier_spectral_slope", 2.0) < 1.35 and synthetic_sensor):
        corroborating_signals.append(f"Wavelet / Fourier Frequency Artifact (Slope: {camera_stats.get('fourier_spectral_slope', 2.0)})")

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
    elif tampering.get("splicing_detected") and not fswap.get("face_swap_detected") and not tampering.get("synthetic_matte_detected"):
        corroborating_signals.append("Pixel Splicing Boundary Discontinuity")

    if ela.get("compression_anomaly_detected"):
        corroborating_signals.append("Compression ELA Divergence")
    if metadata.get("ai_metadata_detected") or metadata.get("editing_software_detected"):
        corroborating_signals.append("Metadata Inconsistency")
    if stego.get("payload_likelihood") in ("HIGH", "MEDIUM"):
        corroborating_signals.append("Statistical Stego / LSB Anomaly")
    if file_security.get("trailing_data_detected") or file_security.get("embedded_objects"):
        corroborating_signals.append("Container Structural Payload")

    signal_count = len(corroborating_signals)
    if signal_count >= 3:
        fusion_verdict = "MULTI_SIGNAL_CONSENSUS_MANIPULATION"
        fusion_confidence = "VERY_HIGH"
    elif signal_count >= 2:
        fusion_verdict = "CORROBORATED_MANIPULATION"
        fusion_confidence = "HIGH"
    elif signal_count == 1:
        if (
            fswap.get("face_swap_detected")
            or (tampering.get("copy_move_detected") and tampering.get("cloned_feature_pairs", 0) >= 8)
            or tampering.get("synthetic_matte_detected")
            or provenance.get("ai_generation_disclosed")
        ):
            fusion_verdict = "CORROBORATED_MANIPULATION"
            fusion_confidence = "HIGH"
        else:
            fusion_verdict = "ISOLATED_ANOMALY"
            fusion_confidence = "MODERATE"
    else:
        fusion_verdict = "CONSISTENT_AUTHENTIC_SIGNALS"
        fusion_confidence = "HIGH"

    # 4. Granular Threat Taxonomy Assignment
    if fswap.get("face_swap_detected"):
        dominant_threat = "Deepfake Face-Swap / Morph"
        threat_code = "DEEPFAKE_FACE_SWAP"
    elif tampering.get("synthetic_matte_detected"):
        dominant_threat = "Synthetic Background / Inpainting Matte"
        threat_code = "SYNTHETIC_BACKGROUND_REPLACEMENT"
    elif ai_gen_prob >= 0.50 or scene_ai_prob >= 0.22 or synthetic_sensor or provenance.get("ai_generation_disclosed"):
        gen_label = provenance.get("disclosed_generator") or metadata.get("ai_generator_name") or "Diffusion / Neural Generator"
        dominant_threat = f"Synthetic AI Generation ({gen_label})"
        threat_code = "SYNTHETIC_AI_GENERATION"
    elif tampering.get("copy_move_detected") or tampering.get("splicing_detected"):
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
            "orthogonal_signals_count": signal_count,
        },
    }
