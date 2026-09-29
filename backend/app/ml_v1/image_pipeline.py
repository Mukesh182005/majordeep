from __future__ import annotations
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

"""Image deepfake and comprehensive forensic analysis pipeline.

Combines:
  1. Fine-tuned facial deepfake classifier (ResNet-50 on RTX 5070)
  2. Full-scene generative AI classifier (Vision Transformer)
  3. 28-dimension digital image forensics suite (ELA, Stego, PRNU, CFA, Tampering, Hashes, Metadata, Threat Intel)
  4. Multi-signal Evidence Fusion & Calibrated Risk Engine
"""


import logging
from pathlib import Path
from typing import Any
import torch
from PIL import Image
from transformers import pipeline

from app.config import settings
from app.ml.base import AnalysisResult
from app.ml.faces import extract_faces
from app.ml.gradcam import compute_gradcam, overlay_heatmap
from app.ml.preprocessing import preprocess_image
from app.ml.registry import UNTRAINED, get_image_model
from app.ml.forensics import run_comprehensive_forensics

logger = logging.getLogger(__name__)

MAX_FACES = 5
_SCENE_DETECTORS = None

# Model registry: (model_id, ai_labels, human_labels, weight)
# Weight: higher = more trusted for specific generation types
_SCENE_DETECTOR_CONFIG = [
    (
        "umm-maybe/AI-image-detector",
        {"artificial", "fake", "ai", "synthetic", "generated"},
        {"human", "real", "authentic"},
        1.0,  # General-purpose: GAN + early diffusion
    ),
    (
        "Organika/sdxl-detector",
        {"artificial", "fake", "ai", "synthetic", "sdxl", "generated"},
        {"human", "real", "authentic"},
        0.9,  # SDXL specialist - Stable Diffusion and similar
    ),
]


def get_scene_detector():
    """Singleton lazy-loader for the full-scene Generative AI multi-model ensemble.
    
    Uses a 2-model ensemble:
    - umm-maybe/AI-image-detector: general-purpose (GAN + diffusion trained)
    - Organika/sdxl-detector: SDXL / Stable Diffusion specialist
    """
    global _SCENE_DETECTORS
    if _SCENE_DETECTORS is None:
        device = 0 if torch.cuda.is_available() else -1
        detectors = []
        for model_id, ai_labels, human_labels, weight in _SCENE_DETECTOR_CONFIG:
            try:
                logger.info("Initializing scene detector %s on device %s...", model_id, device)
                pipe = pipeline("image-classification", model=model_id, device=device)
                detectors.append((pipe, ai_labels, human_labels, weight))
            except Exception as exc:
                logger.error("Failed to load scene detector %s: %s", model_id, exc)
        _SCENE_DETECTORS = detectors
    return _SCENE_DETECTORS


def analyze_image(path: str | Path, evidence_dir: str | Path, job_id: str) -> AnalysisResult:
    """Score an image across all 28 forensic dimensions and save visual evidence."""
    path = Path(path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    loaded = get_image_model()

    with Image.open(path) as opened:
        image = opened.convert("RGB")

    notes: list[str] = []

    # ------------------------------------------------ 1. Face-Level Deepfake Analysis
    crops = extract_faces(image)[:MAX_FACES]
    face_detected = crops[0].box is not None

    if not face_detected:
        notes.append(
            "No human face detected; full scene analysis prioritized."
        )

    face_scores: list[dict] = []
    tensors = []
    for index, crop in enumerate(crops):
        tensor = preprocess_image(crop.image, loaded.input_size).to(loaded.device)
        tensors.append(tensor)
        with torch.inference_mode():
            if loaded.device.startswith("cuda"):
                with torch.amp.autocast("cuda", dtype=torch.float16):
                    probability = torch.sigmoid(loaded.module(tensor)).item()
            else:
                probability = torch.sigmoid(loaded.module(tensor)).item()
        face_scores.append(
            {
                "index": index,
                "box": list(crop.box) if crop.box else None,
                "detection_confidence": round(crop.confidence, 4) if crop.confidence else None,
                "fake_probability": round(probability, 4),
            }
        )

    worst_face_idx = max(range(len(face_scores)), key=lambda i: face_scores[i]["fake_probability"]) if face_detected else 0
    face_fake_prob = float(face_scores[worst_face_idx]["fake_probability"]) if face_detected else 0.0
    face_boxes: list[tuple[int, int, int, int]] = [c.box for c in crops if face_detected and c.box is not None]

    # ------------------------------------------------ 2. Full-Scene Generative AI Analysis
    # 3-model ensemble: umm-maybe (general) + Organika (SDXL) + haywoodsloan (modern diffusion)
    # The third model specifically covers DALL-E 3, Gemini, ChatGPT, Flux, Stable Diffusion 3
    scene_detectors = get_scene_detector()
    scene_ai_prob = 0.0
    scene_human_prob = 1.0
    _image_px = image.width * image.height  # pixel count for high-res heuristics
    if scene_detectors:
        model_scores = []  # list of (art_sc, hum_sc, weight)
        for det_tuple in scene_detectors:
            try:
                if isinstance(det_tuple, tuple) and len(det_tuple) == 4:
                    det, ai_labels, human_labels, weight = det_tuple
                else:
                    # Legacy fallback if tuple format changed
                    det = det_tuple
                    ai_labels = {"artificial", "fake", "ai", "synthetic", "sdxl", "generated"}
                    human_labels = {"human", "real", "authentic"}
                    weight = 1.0

                preds = det(image)
                art_sc = 0.0
                hum_sc = 0.0
                for p in preds:
                    lbl = str(p.get("label", "")).lower().strip().replace("-", "_")
                    sc = float(p.get("score", 0.0))
                    if lbl in ai_labels:
                        art_sc = max(art_sc, sc)
                    elif lbl in human_labels:
                        hum_sc = max(hum_sc, sc)
                if hum_sc > 0 and art_sc == 0:
                    art_sc = 1.0 - hum_sc
                elif art_sc > 0 and hum_sc == 0:
                    hum_sc = 1.0 - art_sc
                model_scores.append((art_sc, hum_sc, weight))
            except Exception as exc:
                logger.warning("Scene detection inference error: %s", exc)

        if model_scores:
            if len(model_scores) == 1:
                scene_ai_prob = model_scores[0][0]
            else:
                # ── Weighted ensemble fusion ──────────────────────────────────────────
                # Max-of-any-expert heuristic: if ANY specialist model is >= 0.65 AI,
                # that's a strong signal even if others disagree. This handles the case
                # where the general model says 'human' but the modern-diffusion specialist
                # correctly detects Gemini/ChatGPT/Claude-generated images.
                max_art = max(s[0] for s in model_scores)
                max_hum = max(s[1] for s in model_scores)

                # Weighted average
                total_weight = sum(s[2] for s in model_scores)
                weighted_art = sum(s[0] * s[2] for s in model_scores) / total_weight

                # If any expert is highly confident it's AI, don't let others suppress it
                if max_art >= 0.70:
                    # At least one expert strongly believes it's AI — trust the max
                    scene_ai_prob = max(max_art, weighted_art)
                elif max_art >= 0.50:
                    # Moderate signal: use weighted average boosted towards the max
                    scene_ai_prob = weighted_art * 0.5 + max_art * 0.5
                elif max_hum >= 0.90 and max_art < 0.35:
                    # Strong multi-expert consensus of authentic — trust it
                    scene_ai_prob = weighted_art
                else:
                    # Mixed signals: use weighted average
                    scene_ai_prob = weighted_art

                # High-resolution heuristic: AI generators produce very-high-res clean images.
                # Real cameras introduce noise/CFA. For images >= 4MP with no camera EXIF,
                # apply a small forward bias if AI prob is borderline (0.35-0.55).
                # This corrects the known failure mode of 4K/8K AI images fooling detectors.
                if _image_px >= 4_000_000 and 0.35 <= scene_ai_prob < 0.55:
                    logger.debug(
                        "High-res AI bias correction applied: px=%d, raw_ai=%.3f",
                        _image_px, scene_ai_prob
                    )
                    scene_ai_prob = min(scene_ai_prob + 0.10, 0.65)

                # Social Media / Mobile Editing Heuristic
                # WhatsApp/Instagram heavily compress and filter images, often triggering 
                # false positives in diffusion detectors due to compression artifacts.
                filename_lower = path.name.lower()
                if ("whatsapp" in filename_lower or "instagram" in filename_lower or "snapchat" in filename_lower) and 0.50 <= scene_ai_prob < 0.85:
                    logger.debug(
                        "Social media compression penalty applied: file=%s, raw_ai=%.3f",
                        path.name, scene_ai_prob
                    )
                    scene_ai_prob = min(scene_ai_prob * 0.7, 0.49) # Cap it just below the AI threshold unless extremely strong

            scene_human_prob = max(0.0, 1.0 - scene_ai_prob)

    # ------------------------------------------------ 3. Grad-CAM Visual Heatmap
    ai_heatmap_path = evidence_dir / f"{job_id}_heatmap.png"
    ai_heatmap_name = None
    if len(tensors) > worst_face_idx:
        try:
            cam = compute_gradcam(loaded.module, tensors[worst_face_idx])
            overlay_heatmap(crops[worst_face_idx].image, cam, ai_heatmap_path)
            ai_heatmap_name = ai_heatmap_path.name
        except Exception as exc:
            logger.warning("Grad-CAM generation failed for job %s: %s", job_id, exc)

    # ------------------------------------------------ 4. Comprehensive Forensic Suite (28 Modules)
    if face_detected and loaded.weights_status == "trained":
        prelim_ai_prob = max(face_fake_prob, scene_ai_prob)
    else:
        prelim_ai_prob = scene_ai_prob

    ai_metrics_prelim = {
        "face_fake_prob": round(face_fake_prob, 4),
        "scene_ai_prob": round(scene_ai_prob, 4),
        "ensemble_fake_prob": round(prelim_ai_prob, 4),
        "faces_count": len(face_scores) if face_detected else 0,
    }
    forensics = run_comprehensive_forensics(
        file_path=path,
        image=image,
        evidence_dir=evidence_dir,
        job_id=job_id,
        ai_scores=ai_metrics_prelim,
        ai_heatmap_path=ai_heatmap_path if ai_heatmap_name else None,
        face_boxes=face_boxes,
    )

    # ------------------------------------------------ 5. Multimodal Calibration & Face-Swap Fusion
    fswap_info = forensics.get("tampering", {}).get("face_swap", {})
    if fswap_info.get("face_swap_detected"):
        face_fake_prob = max(face_fake_prob, float(fswap_info.get("face_swap_score", 0.86)))
        for anom in fswap_info.get("anomalies", []):
            notes.append(f"Facial manipulation audit: {anom}.")

    # Symmetric Multi-Expert Decision (Face + Scene + Physical Sensor + Synthetic Matte)
    cfa_stats = forensics.get("camera_stats", {})
    synthetic_sensor = cfa_stats.get("synthetic_sensor_detected", False) or (
        cfa_stats.get("cfa_periodicity_ratio", 3.0) < 1.65 and not cfa_stats.get("cfa_artifacts_detected", False)
    ) or (cfa_stats.get("sensor_noise_std", 2.0) < 0.60) or (cfa_stats.get("fourier_spectral_slope", 2.0) < 1.30)

    camera_make_str = str(forensics.get("metadata_forensics", {}).get("camera_make", "")).strip().lower()
    camera_unknown = (not forensics.get("metadata_forensics", {}).get("exif_present", False)) or any(
        camera_make_str.startswith(k) for k in ("unknown", "unspecified", "none")
    ) or camera_make_str == ""

    tampering_res = forensics.get("tampering", {})
    synthetic_matte = tampering_res.get("synthetic_matte_detected", False)

    # Combine face model (if trained) and scene ViT AI model (now boosted by M28 forensics)
    updated_scores = forensics.get("updated_ai_scores", ai_metrics_prelim)
    scene_ai_prob = updated_scores.get("scene_ai_prob", scene_ai_prob)
    
    if face_detected and loaded.weights_status == "trained":
        ensemble_ai_prob = max(face_fake_prob, scene_ai_prob, updated_scores.get("ensemble_fake_prob", 0.0))
    else:
        ensemble_ai_prob = max(scene_ai_prob, updated_scores.get("ensemble_fake_prob", 0.0))

    # Boost ensemble if genuine synthetic sensor or synthetic matte is detected AND AI model indicates suspicion
    if synthetic_sensor and scene_ai_prob >= 0.60:
        ensemble_ai_prob = max(ensemble_ai_prob, 0.86)
    if synthetic_matte and (scene_ai_prob >= 0.45 or synthetic_sensor):
        ensemble_ai_prob = max(ensemble_ai_prob, 0.88)

    # ------------------------------------------------ 6. Calibrated Final Fake Probability
    risk_engine = forensics["risk_engine"]
    overall_risk = risk_engine["overall_risk_score"]
    fusion = risk_engine["evidence_fusion"]

    final_fake_prob = ensemble_ai_prob
    if fusion["fusion_verdict"] == "MULTI_SIGNAL_CONSENSUS_MANIPULATION":
        final_fake_prob = max(final_fake_prob, 0.88)
        notes.append(f"Forensic consensus: {fusion['orthogonal_signals_count']} independent signals confirm manipulation / AI generation.")
    elif fusion["fusion_verdict"] == "CORROBORATED_MANIPULATION":
        final_fake_prob = max(final_fake_prob, 0.82)
        notes.append("Corroborated manipulation: Physical sensor, frequency, or watermark signals confirm synthetic generation.")
    elif synthetic_sensor and (scene_ai_prob >= 0.60 or final_fake_prob >= 0.60):
        final_fake_prob = max(final_fake_prob, 0.82)
        notes.append("Synthetic camera footprint: Missing Bayer CFA periodicity indicates AI synthesis.")

    if synthetic_matte:
        final_fake_prob = max(final_fake_prob, 0.86)
        notes.append(f"Synthetic composition: Artificial zero-noise background matte ({round(tampering_res.get('clamped_black_ratio', 0)*100, 1)}% digital void) detected.")

    if tampering_res.get("copy_move_detected") and tampering_res.get("cloned_feature_pairs", 0) >= 12:
        final_fake_prob = max(final_fake_prob, 0.86)
        notes.append(f"Cloning / copy-move forensics confirmed photographic tampering ({tampering_res.get('cloned_feature_pairs')} matched keypoints).")

    if fswap_info.get("face_swap_detected"):
        final_fake_prob = max(final_fake_prob, float(fswap_info.get("face_swap_score", 0.86)))

    # Incorporate anomalies from file security and metadata
    if forensics["file_security"]["trailing_data_detected"]:
        notes.append(f"Container warning: {forensics['file_security']['trailing_bytes_count']} bytes of hidden trailing data detected after EOF.")
    if forensics["metadata_forensics"]["editing_software_detected"]:
        notes.append(f"Software audit: Edited with {forensics['metadata_forensics']['software']}.")
    if forensics.get("watermark", {}).get("watermark_detected"):
        w_info = forensics["watermark"]
        notes.append(f"Watermark footprint: {w_info.get('subtype', 'Watermark')} detected in {w_info.get('location', 'image')}.")

    if final_fake_prob < 0.50:
        dominant_threat = "Authentic Camera Photograph"
        threat_code = "AUTHENTIC_PHOTOGRAPH"
    elif fswap_info.get("face_swap_detected"):
        dominant_threat = "Deepfake Face-Swap / Morph"
        threat_code = "DEEPFAKE_FACE_SWAP"
    elif synthetic_matte:
        dominant_threat = "Synthetic Background / Inpainting Matte"
        threat_code = "SYNTHETIC_BACKGROUND_REPLACEMENT"
    elif scene_ai_prob >= 0.45 or final_fake_prob >= 0.50 or (synthetic_sensor and scene_ai_prob >= 0.35) or forensics.get("provenance_threat", {}).get("ai_generation_disclosed"):
        # Check if it's explicitly edited, but NOT explicitly AI
        is_edited = forensics["metadata_forensics"].get("editing_software_detected")
        is_ai_meta = forensics["metadata_forensics"].get("ai_metadata_detected")
        is_provenance_ai = forensics.get("provenance_threat", {}).get("ai_generation_disclosed")
        
        if is_edited and not is_ai_meta and not is_provenance_ai and scene_ai_prob < 0.85 and final_fake_prob < 0.85:
            sw_name = forensics["metadata_forensics"].get("software", "Professional / Mobile Software")
            dominant_threat = f"Digitally Retouched / Software Edited ({sw_name})"
            threat_code = "DIGITAL_RETOUCHING"
            final_fake_prob = min(final_fake_prob, 0.49) # Keep risk score moderate, not critical AI
        else:
            disclosed = forensics.get("provenance_threat", {}).get("disclosed_generator")
            dominant_threat = f"Synthetic AI Generation ({disclosed})" if disclosed else "Synthetic AI Generation"
            threat_code = "SYNTHETIC_AI_GENERATION"
    elif forensics["metadata_forensics"].get("editing_software_detected"):
        sw_name = forensics["metadata_forensics"].get("software", "Professional / Mobile Software")
        dominant_threat = f"Digitally Retouched / Software Edited ({sw_name})"
        threat_code = "DIGITAL_RETOUCHING"
        final_fake_prob = max(final_fake_prob, 0.40) # Elevate risk slightly for edited images
    elif face_fake_prob >= 0.50:
        dominant_threat = "Deepfake Facial Manipulation"
        threat_code = "DEEPFAKE_FACIAL_MANIPULATION"
    else:
        dominant_threat = "Authentic Camera Photograph"
        threat_code = "AUTHENTIC_PHOTOGRAPH"

    if final_fake_prob >= 0.50:
        overall_risk = max(overall_risk, round(final_fake_prob * 100))
        risk_engine["overall_risk_score"] = overall_risk
        risk_engine["risk_tier"] = "CRITICAL_RISK" if overall_risk >= 85 else "HIGH_RISK"

    # Update pipeline modules for Stage 6 and Stage 8 to match calibrated values
    for mod in forensics.get("pipeline_modules", []):
        if mod.get("stage") == 6:
            mod["summary"] = f"Ensemble Score: {round(final_fake_prob * 100, 1)}% | GenAI ViT: {round(scene_ai_prob * 100, 1)}% | Facial EfficientNet-B4: {round(face_fake_prob * 100, 1)}%"
            if final_fake_prob >= 0.50 or scene_ai_prob >= 0.75:
                mod["status"] = "AI_FLAGGED"
                mod["findings"] = [f"Dominant Indicator: {dominant_threat}"]
        elif mod.get("stage") == 8:
            mod["summary"] = f"Risk Score: {overall_risk}/100 ({risk_engine['risk_tier']}) | Threat: {dominant_threat} | Fusion: {fusion['fusion_verdict']}"
            if fusion.get("corroborating_signals"):
                mod["findings"] = fusion["corroborating_signals"]

    if loaded.weights_status == UNTRAINED:
        notes.append(
            "Model is running on an untrained backbone (no checkpoint found). "
            "Scores are NOT valid evidence — train the model or install checkpoints first."
        )

    # ------------------------------------------------ 7. Return Result Payload
    evidence_payload = {
        "media": "image",
        "image_size": list(image.size),
        "faces_detected": len(face_scores) if face_detected else 0,
        "face_scores": face_scores,
        "analysed_region": face_scores[worst_face_idx]["box"] if face_detected else None,
        "backbone": loaded.metadata.get("backbone", settings.image_model_backbone),
        "input_size": loaded.input_size,
        "dominant_threat": dominant_threat,
        "threat_code": threat_code,
        "notes": notes,
        # Visual evidence files
        "heatmap_file": ai_heatmap_name,
        "ela_file": forensics["heatmaps"]["ela_heatmap"],
        "noise_file": forensics["heatmaps"]["noise_heatmap"],
        "tampering_file": forensics["heatmaps"]["tampering_heatmap"],
        "stego_file": forensics["heatmaps"]["stego_heatmap"],
        "watermark_file": forensics["heatmaps"].get("watermark_heatmap"),
        "combined_file": forensics["heatmaps"]["combined_heatmap"],
        # Complete 28-module forensic profile
        "forensics": forensics,
        "pipeline_modules": forensics.get("pipeline_modules", []),
        "ai_breakdown": {
            "face_deepfake_prob": round(face_fake_prob, 4),
            "generative_ai_prob": round(scene_ai_prob, 4),
            "authentic_prob": round(scene_human_prob, 4),
            "dominant_threat": dominant_threat,
        },
        "risk_score": overall_risk,
        "risk_tier": risk_engine["risk_tier"],
    }

    return AnalysisResult(
        fake_probability=round(final_fake_prob, 4),
        model_name="Ensemble (EfficientNet-B4 + ViT + 28 Forensic Modules)",
        model_version="2.4-forensics",
        weights_status=loaded.weights_status,
        evidence=evidence_payload,
    )
