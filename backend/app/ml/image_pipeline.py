"""Image deepfake and comprehensive forensic analysis pipeline.

Combines:
  1. Full-scene AI-generation detectors (HuggingFace ensemble, see ``SCENE_DETECTORS``)
  2. Face-crop GAN detector (EfficientNet-B4 trained on StyleGAN faces)
  3. Digital image forensics suite (ELA, stego, CFA, tampering, hashes, metadata, C2PA)
  4. Evidence fusion and risk engine

Screenshots are detected and their viewer borders cropped before any pixel
analysis; a screenshot the detectors do not flag is reported INCONCLUSIVE, not
AUTHENTIC, because recapture destroys the evidence an authentic verdict needs.
"""

from __future__ import annotations

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image

from app.config import settings
from app.ml.base import AnalysisResult, classify, resolve_device
from app.ml.faces import extract_faces
from app.ml.forensics import run_comprehensive_forensics
from app.ml.forensics.recapture import crop_recapture_borders
from app.ml.gradcam import compute_gradcam, overlay_heatmap
from app.ml.preprocessing import preprocess_image
from app.ml.registry import UNTRAINED, get_image_model
from app.models import Verdict

logger = logging.getLogger(__name__)

MAX_FACES = 5


@dataclass(frozen=True)
class SceneDetectorSpec:
    model_id: str
    weight: float  # weight in the log-odds fusion
    role: str


# Chosen by measurement, not by model card. On 560 held-out images (200 real
# COCO/Flickr photos; 360 from SD 2.1, SDXL, SD3, DALL-E 3, Midjourney v6,
# Flux.1-dev, Gemini "Nano Banana" and Nano Banana Pro), scored as original
# files, as size/codec-normalised JPEGs, and as simulated screenshots:
#   haywoodsloan alone            AUC 0.973, 3.5% of real photos >= 0.5
#   0.75/0.25 fusion w/ Organika  AUC 0.984 (0.980 on held-out halves), 3.5%
#   Organika alone                AUC 0.836, 23% of real photos >= 0.5
#   umm-maybe/AI-image-detector   AUC 0.469 — below chance; removed
#   max-of-experts (old rule)     flagged 26-36% of real photos
SCENE_DETECTORS: tuple[SceneDetectorSpec, ...] = (
    SceneDetectorSpec(
        "haywoodsloan/ai-image-detector-deploy", 0.75, "Modern diffusion & GAN detector (SwinV2)"
    ),
    SceneDetectorSpec("Organika/sdxl-detector", 0.25, "Stable Diffusion / SDXL specialist (Swin)"),
)
_REAL_CLASS_NAMES = frozenset({"real", "human", "hum", "authentic"})


@dataclass(frozen=True)
class LoadedSceneDetector:
    spec: SceneDetectorSpec
    pipe: Any  # transformers ImageClassificationPipeline
    real_labels: frozenset[str]


_SCENE_DETECTORS: list[LoadedSceneDetector] | None = None
_SCENE_LOCK = threading.Lock()


def get_scene_detector() -> list[LoadedSceneDetector]:
    """Load the scene-detector ensemble once per process.

    P(AI) is read as 1 - P(real class), with the real class found in each
    model's own label map, so a model whose labels are named differently
    ("hum", "human", "real") cannot be silently mis-scored.
    """
    global _SCENE_DETECTORS
    if _SCENE_DETECTORS is not None:
        return _SCENE_DETECTORS
    with _SCENE_LOCK:
        if _SCENE_DETECTORS is None:
            from transformers import pipeline

            device = resolve_device()
            loaded: list[LoadedSceneDetector] = []
            for spec in SCENE_DETECTORS:
                try:
                    logger.info("Initializing scene detector %s on %s...", spec.model_id, device)
                    pipe = pipeline("image-classification", model=spec.model_id, device=device)
                except Exception as exc:
                    logger.error("Failed to load scene detector %s: %s", spec.model_id, exc)
                    continue
                id2label = getattr(pipe.model.config, "id2label", None) or {}
                labels = {str(label) for label in id2label.values()}
                real = frozenset(label for label in labels if label.lower() in _REAL_CLASS_NAMES)
                if not real:
                    logger.error("Scene detector %s has no 'real' class in %s; skipped.", spec.model_id, labels)
                    continue
                loaded.append(LoadedSceneDetector(spec=spec, pipe=pipe, real_labels=real))
            if not loaded:
                logger.error("No scene detector could be loaded: AI-generation analysis is unavailable.")
            _SCENE_DETECTORS = loaded
    return _SCENE_DETECTORS


def _logit(p: float, eps: float = 1e-6) -> float:
    p = min(max(p, eps), 1.0 - eps)
    return math.log(p / (1.0 - p))


def score_scene(image: Image.Image) -> dict[str, Any]:
    """Probability that ``image`` is AI-generated, fused across the scene detectors.

    Fusion is a weighted mean in log-odds space. Unlike max-of-experts, a
    single over-eager model cannot flag a real photo on its own. Returns
    ``scene_ai_prob=None`` when no detector produced a score.
    """
    model_scores: dict[str, float] = {}
    weighted = weight_total = 0.0
    for detector in get_scene_detector():
        try:
            predictions = detector.pipe(image, top_k=None)
        except Exception as exc:
            logger.warning("Scene detector %s failed: %s", detector.spec.model_id, exc)
            continue
        p_real = sum(float(p["score"]) for p in predictions if str(p["label"]) in detector.real_labels)
        p_ai = min(max(1.0 - p_real, 0.0), 1.0)
        model_scores[detector.spec.model_id] = round(p_ai, 4)
        weighted += detector.spec.weight * _logit(p_ai)
        weight_total += detector.spec.weight
    fused = 1.0 / (1.0 + math.exp(-weighted / weight_total)) if weight_total else None
    return {"scene_ai_prob": fused, "model_scores": model_scores}


def _face_fake_probability(loaded, tensor) -> float | None:
    """Face-model probability, or ``None`` if the output is not a number.

    Runs in float32: under float16 autocast EfficientNet-B4 overflows on some
    inputs and returns NaN, which then poisons the stored evidence.
    """
    with torch.inference_mode():
        logit = loaded.module(tensor).float()
    probability = float(torch.sigmoid(logit).item())
    return probability if math.isfinite(probability) else None


def _to_source_box(box, offset: tuple[int, int]) -> list[int] | None:
    """Map a box from the analysed (border-cropped) image back to the uploaded image."""
    if box is None:
        return None
    ox, oy = offset
    x1, y1, x2, y2 = box
    return [int(x1) + ox, int(y1) + oy, int(x2) + ox, int(y2) + oy]


def analyze_image(path: str | Path, evidence_dir: str | Path, job_id: str) -> AnalysisResult:
    """Score an image across all forensic dimensions and save visual evidence."""
    path = Path(path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    loaded = get_image_model()

    with Image.open(path) as opened:
        source_image = opened.convert("RGB")

    notes: list[str] = []

    # ------------------------------------------------ 0. Screenshot / recapture framing
    # Viewer bars skew every pixel statistic and the classifiers' 224 px input,
    # so all pixel analysis runs on the framed content only.
    image, recapture = crop_recapture_borders(source_image)
    offset = tuple(recapture["content_box"][:2]) if recapture["content_box"] else (0, 0)
    if recapture["letterbox_detected"]:
        notes.append(
            f"Uniform viewer/letterbox borders removed before analysis "
            f"({round(recapture['border_area_ratio'] * 100, 1)}% of the frame)."
        )

    # ------------------------------------------------ 1. Face crops (StyleGAN face model)
    crops = extract_faces(image)[:MAX_FACES]
    face_detected = crops[0].box is not None
    if not face_detected:
        notes.append("No human face detected; full scene analysis prioritized.")

    face_scores: list[dict] = []
    tensors = []
    for index, crop in enumerate(crops):
        tensor = preprocess_image(crop.image, loaded.input_size).to(loaded.device)
        tensors.append(tensor)
        if not face_detected:
            continue  # the face model is trained on face crops; its score on a whole scene means nothing
        probability = _face_fake_probability(loaded, tensor)
        face_scores.append(
            {
                "index": index,
                "box": _to_source_box(crop.box, offset),
                "detection_confidence": round(crop.confidence, 4) if crop.confidence else None,
                "fake_probability": round(probability, 4) if probability is not None else None,
            }
        )

    scored_faces = [s for s in face_scores if s["fake_probability"] is not None]
    worst_face_idx = max(
        range(len(face_scores)), key=lambda i: face_scores[i]["fake_probability"] or 0.0, default=0
    )
    face_fake_prob = max((s["fake_probability"] for s in scored_faces), default=0.0)
    face_boxes: list[tuple[int, int, int, int]] = [c.box for c in crops if face_detected and c.box is not None]

    # ------------------------------------------------ 2. Full-scene AI-generation detectors
    scene = score_scene(image)
    scene_available = scene["scene_ai_prob"] is not None
    scene_ai_prob = scene["scene_ai_prob"] if scene_available else 0.0
    if not scene_available:
        notes.append(
            "AI-generation detectors unavailable (models failed to load); "
            "an AUTHENTIC verdict cannot be issued for this image."
        )

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

    # ------------------------------------------------ 4. Comprehensive Forensic Suite
    # Reported always; counted only when a validated face model is configured.
    face_model_counts = settings.face_model_in_verdict and face_detected and loaded.weights_status == "trained"
    prelim_ai_prob = max(face_fake_prob, scene_ai_prob) if face_model_counts else scene_ai_prob
    ai_metrics_prelim = {
        "face_fake_prob": round(face_fake_prob, 4),
        "scene_ai_prob": round(scene_ai_prob, 4),
        "ensemble_fake_prob": round(prelim_ai_prob, 4),
        "faces_count": len(face_scores),
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
    if recapture["letterbox_detected"]:
        ingestion = next((m for m in forensics.get("pipeline_modules", []) if m.get("stage") == 1), None)
        if ingestion is not None:
            border = (
                f"{recapture['framed_sides']} uniform border side(s) "
                f"({round(recapture['border_area_ratio'] * 100, 1)}% of frame) cropped before analysis"
            )
            finding = (
                f"Screen-capture framing detected: {border}."
                if recapture["framed"]
                else f"Flat edge strip trimmed: {border}."
            )
            ingestion["findings"] = [finding, *ingestion.get("findings", [])]

    # ------------------------------------------------ 5. Forensic indicators
    # The face-seam heuristic is reported, not scored: on 30 real photos with
    # faces it fired on 9 (30%) — face-vs-background sharpness differences
    # are what ordinary portraits (bokeh, skin vs foliage) look like. Only a
    # trained face-swap model can carry a face-swap verdict.
    fswap_info = forensics.get("tampering", {}).get("face_swap", {})
    if fswap_info.get("face_swap_detected"):
        for anom in fswap_info.get("anomalies", []):
            notes.append(f"Face-region inconsistency (unvalidated heuristic, not used in the verdict): {anom}.")

    # Camera-trace absence is near-universal in web images (no CFA trace in
    # any of 196 real JPEG photos measured), so it only ever corroborates a
    # detector that has already fired — it is never evidence on its own.
    cfa_stats = forensics.get("camera_stats", {})
    synthetic_sensor = cfa_stats.get("synthetic_sensor_detected", False) or (
        cfa_stats.get("cfa_periodicity_ratio", 3.0) < 1.65 and not cfa_stats.get("cfa_artifacts_detected", False)
    ) or (cfa_stats.get("sensor_noise_std", 2.0) < 0.60) or (cfa_stats.get("fourier_spectral_slope", 2.0) < 1.30)

    metadata_forensics = forensics["metadata_forensics"]
    provenance = forensics.get("provenance_threat", {})
    tampering_res = forensics.get("tampering", {})
    synthetic_matte = tampering_res.get("synthetic_matte_detected", False)

    updated_scores = forensics.get("updated_ai_scores", ai_metrics_prelim)
    scene_ai_prob = updated_scores.get("scene_ai_prob", scene_ai_prob)
    if face_model_counts:
        ensemble_ai_prob = max(face_fake_prob, scene_ai_prob, updated_scores.get("ensemble_fake_prob", 0.0))
    else:
        ensemble_ai_prob = max(scene_ai_prob, updated_scores.get("ensemble_fake_prob", 0.0))

    # ------------------------------------------------ 6. Calibrated Final Fake Probability
    risk_engine = forensics["risk_engine"]
    overall_risk = risk_engine["overall_risk_score"]
    fusion = risk_engine["evidence_fusion"]

    final_fake_prob = ensemble_ai_prob

    # Declared provenance is the strongest evidence there is: a generator that
    # signs its output as AI (C2PA "trainedAlgorithmicMedia") or writes its
    # parameters into the file.
    if provenance.get("ai_generation_disclosed"):
        final_fake_prob = max(final_fake_prob, 0.97)
        notes.append(f"Content Credentials (C2PA) declare AI generation: {provenance.get('disclosed_generator')}.")
    if metadata_forensics.get("ai_metadata_detected"):
        final_fake_prob = max(final_fake_prob, 0.93)
        notes.append(f"Generator metadata found in file: {metadata_forensics.get('ai_generator_name')}.")

    if fusion["fusion_verdict"] == "MULTI_SIGNAL_CONSENSUS_MANIPULATION":
        final_fake_prob = max(final_fake_prob, 0.88)
        notes.append(f"Forensic consensus: {fusion['orthogonal_signals_count']} independent signals confirm manipulation / AI generation.")
    elif fusion["fusion_verdict"] == "CORROBORATED_MANIPULATION":
        final_fake_prob = max(final_fake_prob, 0.82)
        notes.append(f"Corroborated manipulation: {'; '.join(fusion.get('corroborating_signals', []))}.")

    # A near-black/chroma matte fired on 2.0% of real photos and 1.8% of AI
    # images: it describes a detection, it does not add evidence for one.
    if synthetic_matte and final_fake_prob >= 0.50:
        notes.append(f"Synthetic composition: Artificial zero-noise background matte ({round(tampering_res.get('clamped_black_ratio', 0)*100, 1)}% digital void) detected.")

    # ORB copy-move clustering also matches repeated real structure (windows,
    # tiles, icons), so on its own it asks for review rather than asserting
    # tampering.
    if tampering_res.get("copy_move_detected") and tampering_res.get("cloned_feature_pairs", 0) >= 12:
        final_fake_prob = max(final_fake_prob, 0.55)
        notes.append(f"Possible cloning / copy-move: {tampering_res.get('cloned_feature_pairs')} keypoints share one displacement; repeated real structure can also cause this, so review the region.")

    # Incorporate anomalies from file security and metadata
    if forensics["file_security"]["trailing_data_detected"]:
        notes.append(f"Container warning: {forensics['file_security']['trailing_bytes_count']} bytes of hidden trailing data detected after EOF.")
    if metadata_forensics["editing_software_detected"]:
        notes.append(f"Software audit: Edited with {metadata_forensics['software']}.")
    if forensics.get("watermark", {}).get("watermark_detected"):
        w_info = forensics["watermark"]
        notes.append(f"Watermark footprint: {w_info.get('subtype', 'Watermark')} detected in {w_info.get('location', 'image')}.")

    if final_fake_prob < 0.50:
        if classify(final_fake_prob) is Verdict.AUTHENTIC:
            dominant_threat = "Authentic Camera Photograph"
            threat_code = "AUTHENTIC_PHOTOGRAPH"
        else:
            dominant_threat = "Inconclusive (weak AI-generation indicators)"
            threat_code = "INCONCLUSIVE_INDICATORS"
    elif synthetic_matte and scene_ai_prob >= 0.50:
        dominant_threat = "Synthetic Background / Inpainting Matte"
        threat_code = "SYNTHETIC_BACKGROUND_REPLACEMENT"
    elif scene_ai_prob >= 0.45 or final_fake_prob >= 0.50 or (synthetic_sensor and scene_ai_prob >= 0.35) or provenance.get("ai_generation_disclosed"):
        is_edited = metadata_forensics.get("editing_software_detected")
        is_ai_meta = metadata_forensics.get("ai_metadata_detected")
        is_provenance_ai = provenance.get("ai_generation_disclosed")

        # Editor metadata relabels only scores the detectors are not confident
        # about; re-saving an AI image in an editor must not hide a confident
        # detection (this cap used to reach 0.85).
        if is_edited and not is_ai_meta and not is_provenance_ai and scene_ai_prob < 0.65 and final_fake_prob < 0.65:
            sw_name = metadata_forensics.get("software", "Professional / Mobile Software")
            dominant_threat = f"Digitally Retouched / Software Edited ({sw_name})"
            threat_code = "DIGITAL_RETOUCHING"
            final_fake_prob = min(final_fake_prob, 0.49)
        else:
            disclosed = provenance.get("disclosed_generator")
            dominant_threat = f"Synthetic AI Generation ({disclosed})" if disclosed else "Synthetic AI Generation"
            threat_code = "SYNTHETIC_AI_GENERATION"
    elif metadata_forensics.get("editing_software_detected"):
        sw_name = metadata_forensics.get("software", "Professional / Mobile Software")
        dominant_threat = f"Digitally Retouched / Software Edited ({sw_name})"
        threat_code = "DIGITAL_RETOUCHING"
        final_fake_prob = max(final_fake_prob, 0.40)
    elif face_model_counts and face_fake_prob >= 0.50:
        dominant_threat = "Deepfake Facial Manipulation"
        threat_code = "DEEPFAKE_FACIAL_MANIPULATION"
    else:
        dominant_threat = "Authentic Camera Photograph"
        threat_code = "AUTHENTIC_PHOTOGRAPH"

    # ------------------------------------------------ 7. Can the evidence support AUTHENTIC?
    # A low score is absence of detected manipulation, not proof of
    # authenticity. Two cases cannot support an authentic call: the AI
    # detectors did not run, or the upload is a screenshot with no camera
    # metadata — recapture strips provenance and blurs the traces detectors
    # need, so the original file must be examined instead.
    camera_make = str(metadata_forensics.get("camera_make", "")).strip().lower()
    camera_metadata = bool(metadata_forensics.get("exif_present")) and camera_make not in ("", "none") and not any(
        camera_make.startswith(k) for k in ("unknown", "unspecified")
    )
    verdict_override = None
    verdict_basis = "detector_score"
    would_be_authentic = classify(final_fake_prob) is Verdict.AUTHENTIC
    if would_be_authentic and not scene_available:
        verdict_override = Verdict.INCONCLUSIVE
        verdict_basis = "scene_detectors_unavailable"
        dominant_threat = "Insufficient Evidence (AI-generation detectors unavailable)"
        threat_code = "INSUFFICIENT_EVIDENCE"
    elif would_be_authentic and recapture["framed"] and not camera_metadata:
        verdict_override = Verdict.INCONCLUSIVE
        verdict_basis = "screen_recapture"
        dominant_threat = "Screenshot / Screen Recapture — Insufficient Evidence"
        threat_code = "SCREEN_RECAPTURE_UNVERIFIABLE"
        notes.append(
            "This upload is a screenshot: recapture removes camera/C2PA provenance and the "
            "fine pixel traces AI detectors rely on. No AI generation was detected, but that "
            "cannot establish authenticity — analyse the original file instead."
        )

    if final_fake_prob >= 0.50:
        overall_risk = max(overall_risk, round(final_fake_prob * 100))
        risk_engine["overall_risk_score"] = overall_risk
        risk_engine["risk_tier"] = "CRITICAL_RISK" if overall_risk >= 85 else "HIGH_RISK"

    # Update pipeline modules for Stage 6 and Stage 8 to match calibrated values
    model_summary = " | ".join(
        f"{model_id.split('/')[-1]}: {round(p * 100, 1)}%" for model_id, p in scene["model_scores"].items()
    ) or "unavailable"
    for mod in forensics.get("pipeline_modules", []):
        if mod.get("stage") == 6:
            face_part = (
                f" | Face GAN model (StyleGAN-trained{'' if face_model_counts else ', informational only'}): {round(face_fake_prob * 100, 1)}%"
                if face_detected
                else ""
            )
            mod["summary"] = f"Ensemble Score: {round(final_fake_prob * 100, 1)}% | Scene detectors: {model_summary}{face_part}"
            if final_fake_prob >= 0.50 or scene_ai_prob >= 0.75:
                mod["status"] = "AI_FLAGGED"
                mod["findings"] = [f"Dominant Indicator: {dominant_threat}"]
            elif verdict_override is not None:
                mod["status"] = "SUSPICIOUS"
                mod["findings"] = [dominant_threat]
        elif mod.get("stage") == 8:
            mod["summary"] = f"Risk Score: {overall_risk}/100 ({risk_engine['risk_tier']}) | Threat: {dominant_threat} | Fusion: {fusion['fusion_verdict']}"
            if fusion.get("corroborating_signals"):
                mod["findings"] = fusion["corroborating_signals"]

    if loaded.weights_status == UNTRAINED:
        notes.append(
            "Model is running on an untrained backbone (no checkpoint found). "
            "Scores are NOT valid evidence — train the model or install checkpoints first."
        )

    # ------------------------------------------------ 8. Return Result Payload
    evidence_payload = {
        "media": "image",
        "image_size": list(source_image.size),
        "analysis_region": recapture["content_box"],
        "recapture": recapture,
        "faces_detected": len(face_scores),
        "face_scores": face_scores,
        "analysed_region": face_scores[worst_face_idx]["box"] if face_scores else None,
        "backbone": loaded.metadata.get("backbone", settings.image_model_backbone),
        "input_size": loaded.input_size,
        "scene_model_scores": scene["model_scores"],
        "verdict_basis": verdict_basis,
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
        # Complete forensic profile
        "forensics": forensics,
        "pipeline_modules": forensics.get("pipeline_modules", []),
        "ai_breakdown": {
            "face_deepfake_prob": round(face_fake_prob, 4),
            "generative_ai_prob": round(scene_ai_prob, 4),
            "authentic_prob": round(max(0.0, 1.0 - scene_ai_prob), 4),
            "dominant_threat": dominant_threat,
        },
        "risk_score": overall_risk,
        "risk_tier": risk_engine["risk_tier"],
    }

    return AnalysisResult(
        fake_probability=round(final_fake_prob, 4),
        model_name="Ensemble (SwinV2 + Swin scene detectors, EfficientNet-B4 face model, forensic modules)",
        model_version="2.5-forensics",
        weights_status=loaded.weights_status,
        evidence=evidence_payload,
        verdict_override=verdict_override,
    )
