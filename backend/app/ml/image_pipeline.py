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
_SCENE_DETECTOR = None


def get_scene_detector():
    """Singleton lazy-loader for the full-scene Generative AI detection pipeline."""
    global _SCENE_DETECTOR
    if _SCENE_DETECTOR is None:
        device = 0 if torch.cuda.is_available() else -1
        try:
            logger.info("Initializing full-scene generative AI detector on device %s...", device)
            _SCENE_DETECTOR = pipeline(
                "image-classification",
                model="umm-maybe/AI-image-detector",
                device=device,
            )
        except Exception as exc:
            logger.error("Failed to load scene detector: %s", exc)
            _SCENE_DETECTOR = None
    return _SCENE_DETECTOR


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
    scene_detector = get_scene_detector()
    scene_ai_prob = 0.0
    scene_human_prob = 1.0
    if scene_detector is not None:
        try:
            preds = scene_detector(image)
            for p in preds:
                if p["label"] == "artificial":
                    scene_ai_prob = float(p["score"])
                elif p["label"] == "human":
                    scene_human_prob = float(p["score"])
        except Exception as exc:
            logger.warning("Scene detection inference error: %s", exc)
            notes.append("Full-scene generative AI inference encountered an anomaly.")

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
    if face_detected:
        # Full-scene AI generation and face-swap probes evaluate orthogonal threats
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
        cfa_stats.get("cfa_periodicity_ratio", 3.0) < 1.8 and cfa_stats.get("sensor_noise_std", 2.0) < 1.8
    ) or (cfa_stats.get("sensor_noise_std", 2.0) < 0.60)

    camera_make_str = str(forensics.get("metadata_forensics", {}).get("camera_make", "")).strip().lower()
    camera_unknown = (not forensics.get("metadata_forensics", {}).get("exif_present", False)) or any(
        camera_make_str.startswith(k) for k in ("unknown", "unspecified", "none")
    ) or camera_make_str == ""

    tampering_res = forensics.get("tampering", {})
    synthetic_matte = tampering_res.get("synthetic_matte_detected", False)

    if face_detected:
        ensemble_ai_prob = max(face_fake_prob, scene_ai_prob)
        if synthetic_sensor and (scene_ai_prob >= 0.22 or ensemble_ai_prob >= 0.22 or (camera_unknown and scene_ai_prob >= 0.18)):
            ensemble_ai_prob = max(ensemble_ai_prob, 0.84)
        if synthetic_matte and (scene_ai_prob >= 0.18 or synthetic_sensor):
            ensemble_ai_prob = max(ensemble_ai_prob, 0.88)
    else:
        ensemble_ai_prob = scene_ai_prob
        if synthetic_sensor and (scene_ai_prob >= 0.22 or (camera_unknown and scene_ai_prob >= 0.18)):
            ensemble_ai_prob = max(ensemble_ai_prob, 0.85)
        if synthetic_matte and (scene_ai_prob >= 0.18 or synthetic_sensor):
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
    elif synthetic_sensor and (scene_ai_prob >= 0.22 or final_fake_prob >= 0.22):
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
    elif scene_ai_prob >= face_fake_prob or synthetic_sensor or forensics.get("provenance_threat", {}).get("ai_generation_disclosed"):
        disclosed = forensics.get("provenance_threat", {}).get("disclosed_generator")
        dominant_threat = f"Synthetic AI Generation ({disclosed})" if disclosed else "Synthetic AI Generation"
        threat_code = "SYNTHETIC_AI_GENERATION"
    else:
        dominant_threat = "Deepfake Facial Manipulation"
        threat_code = "DEEPFAKE_FACIAL_MANIPULATION"

    if final_fake_prob >= 0.50:
        overall_risk = max(overall_risk, round(final_fake_prob * 100))
        risk_engine["overall_risk_score"] = overall_risk
        risk_engine["risk_tier"] = "CRITICAL_RISK" if overall_risk >= 85 else "HIGH_RISK"

    # Update pipeline modules for Stage 6 and Stage 8 to match calibrated values
    for mod in forensics.get("pipeline_modules", []):
        if mod.get("stage") == 6:
            mod["summary"] = f"Ensemble Score: {round(final_fake_prob * 100, 1)}% | GenAI ViT: {round(scene_ai_prob * 100, 1)}% | Facial EfficientNet-B4: {round(face_fake_prob * 100, 1)}%"
            if final_fake_prob >= 0.50 or scene_ai_prob >= 0.22:
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
