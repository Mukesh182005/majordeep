"""Forensic Package: Cybersecurity-focused image analysis suite.

Executes an 8-stage sequential modular pipeline:
  Stage 1: Secure Ingestion & File Validation
  Stage 2: File Structure & Cryptographic Ledger
  Stage 3: Metadata & Digital Timeline Forensics
  Stage 4: Image Signal Forensics (FFT / DCT / ELA / CFA / PRNU)
  Stage 5: Manipulation & Watermark Engine
  Stage 6: AI & Deepfake Classification
  Stage 7: Steganography & Provenance Verification
  Stage 8: Evidence Correlation & Calibrated Risk Fusion
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from PIL import Image

from app.ml.forensics.file_security import analyze_file_security
from app.ml.forensics.hashing import compute_all_hashes
from app.ml.forensics.metadata_timeline import analyze_metadata_and_timeline
from app.ml.forensics.tampering import analyze_tampering, compute_ela
from app.ml.forensics.steganography import analyze_steganography
from app.ml.forensics.camera_cfa import analyze_camera_and_cfa
from app.ml.forensics.watermark import analyze_watermark
from app.ml.forensics.provenance_threat import analyze_provenance_and_threats
from app.ml.forensics.adversarial_ood import analyze_adversarial_and_ood
from app.ml.forensics.risk_fusion import compute_risk_and_fusion
from app.ml.forensics.custody import generate_chain_of_custody, get_model_audit_info
from app.ml.forensics.heatmaps import generate_tampering_heatmap, generate_combined_forensic_map
from app.ml.forensics.ai_synthetic_detector import compute_ai_forensic_score

logger = logging.getLogger(__name__)


def run_comprehensive_forensics(
    file_path: str | Path,
    image: Image.Image,
    evidence_dir: str | Path,
    job_id: str,
    ai_scores: dict[str, Any],
    ai_heatmap_path: Path | None = None,
    face_boxes: list[tuple[int, int, int, int]] | None = None,
) -> dict[str, Any]:
    """
    Execute all forensic modules sequentially in 8 explicit stages, logging timing and status.
    """
    file_path = Path(file_path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    pipeline_modules: list[dict[str, Any]] = []

    # ------------------------------------------------------------- STAGE 1: Secure Ingestion
    t0 = time.perf_counter()
    file_security = analyze_file_security(file_path)
    t1 = time.perf_counter()
    
    st1_status = "PASSED" if file_security["structure_valid"] and not file_security["extension_mismatch"] else "ANOMALY_DETECTED"
    pipeline_modules.append({
        "stage": 1,
        "name": "Secure Ingestion & Validation",
        "category": "File Ingestion",
        "status": st1_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Format: {file_security['format']} | MIME: {file_security['mime_type']} | Size: {file_security['file_size_bytes']} bytes",
        "findings": file_security["anomalies"] or ["Header magic bytes and file extension match."],
    })

    # ------------------------------------------------------------- STAGE 2: File Structure & Hashing
    t0 = time.perf_counter()
    hashes = compute_all_hashes(file_path, image)
    t1 = time.perf_counter()

    st2_findings = []
    if file_security["trailing_data_detected"]:
        st2_findings.append(f"{file_security['trailing_bytes_count']} trailing bytes appended after EOF.")
    if file_security["embedded_objects"]:
        st2_findings.append(f"{len(file_security['embedded_objects'])} embedded archive/executable signature(s) detected.")
    
    st2_status = "ANOMALY_DETECTED" if (file_security["trailing_data_detected"] or file_security["embedded_objects"]) else "PASSED"
    pipeline_modules.append({
        "stage": 2,
        "name": "File Container & Cryptographic Ledger",
        "category": "File Forensics",
        "status": st2_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"SHA-256: {hashes['sha256'][:16]}... | pHash: {hashes['phash']} | Trailing data: {'Detected' if file_security['trailing_data_detected'] else 'None'}",
        "findings": st2_findings or ["Container structure normal; cryptographic and perceptual hashes generated."],
    })

    # ------------------------------------------------------------- STAGE 3: Metadata & Timeline
    t0 = time.perf_counter()
    metadata_forensics = analyze_metadata_and_timeline(file_path, image)
    t1 = time.perf_counter()

    st3_status = "ANOMALY_DETECTED" if metadata_forensics["editing_software_detected"] or metadata_forensics["ai_metadata_detected"] else "PASSED"
    pipeline_modules.append({
        "stage": 3,
        "name": "Metadata & Digital Timeline Forensics",
        "category": "Provenance & Metadata",
        "status": st3_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Camera: {metadata_forensics['camera_make']} {metadata_forensics['camera_model']} | Software: {metadata_forensics['software']} | Timeline: {metadata_forensics['timeline_consistency']}",
        "findings": metadata_forensics["anomalies"] or ["Metadata timestamps and device profile consistent."],
    })

    # ------------------------------------------------------------- STAGE 4: Image Signal Forensics
    t0 = time.perf_counter()
    camera_stats = analyze_camera_and_cfa(image, evidence_dir, job_id)
    ela = compute_ela(image, evidence_dir, job_id)
    t1 = time.perf_counter()

    st4_findings = []
    if ela["compression_anomaly_detected"]:
        st4_findings.append(f"Compression divergence detected (peak ELA delta: {ela['peak_error']}).")
    if not camera_stats["cfa_artifacts_detected"]:
        # Absent in every real JPEG photo measured: resizing and recompression erase it.
        st4_findings.append("No camera CFA demosaicing trace found (normal after resizing or JPEG recompression; not evidence of AI generation on its own).")

    if camera_stats.get("fourier_spectral_slope"):
        st4_findings.append(f"Fourier spectral slope: alpha={camera_stats['fourier_spectral_slope']} (Wavelet HH peak ratio: {camera_stats.get('wavelet_grid_peak_ratio')}).")

    st4_status = "SUSPICIOUS" if ela["compression_anomaly_detected"] else "PASSED"
    cfa_label = "Physical Hardware Grid (Real Camera)" if camera_stats["cfa_artifacts_detected"] else "Not detected"
    pipeline_modules.append({
        "stage": 4,
        "name": "Frequency & Signal Forensics (FFT / DCT / ELA)",
        "category": "Image Forensics",
        "status": st4_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Camera Sensor: {camera_stats['estimated_camera_family']} | ELA Score: {ela['ela_score']} | CFA Bayer: {cfa_label}",
        "findings": st4_findings or ["Natural sensor noise and physical Bayer CFA demosaicing characteristics."],
    })

    # ------------------------------------------------------------- STAGE 5: Manipulation & Watermark Engine
    t0 = time.perf_counter()
    tampering = analyze_tampering(image, face_boxes=face_boxes)
    tampering_heatmap = generate_tampering_heatmap(image, evidence_dir, job_id, tampering)
    watermark = analyze_watermark(image, evidence_dir, job_id)
    t1 = time.perf_counter()

    st5_findings = []
    fswap_info = tampering.get("face_swap", {})
    if fswap_info.get("face_swap_detected"):
        for anom in fswap_info.get("anomalies", []):
            st5_findings.append(f"Face-region inconsistency (heuristic; common in real portraits, not proof of a face swap): {anom}.")
    if tampering.get("synthetic_matte_detected"):
        st5_findings.append(f"Synthetic background matte: {round(tampering.get('clamped_black_ratio', 0) * 100, 1)}% of frame is zero-noise digital void (matte/cutout).")
    if tampering["copy_move_detected"]:
        st5_findings.append(f"Copy-move cloning detected with {tampering['cloned_feature_pairs']} matched keypoints.")
    if tampering["splicing_detected"] and not fswap_info.get("face_swap_detected") and not tampering.get("synthetic_matte_detected"):
        st5_findings.append("Splicing boundary gradient discontinuity detected.")
    if watermark["watermark_detected"]:
        st5_findings.append(f"Watermark detected: {watermark['subtype']} in {watermark['location']}.")

    has_tamper = (tampering["copy_move_detected"] or tampering["splicing_detected"] or watermark["watermark_detected"] or fswap_info.get("face_swap_detected"))
    st5_status = "SUSPICIOUS" if (has_tamper or tampering.get("synthetic_matte_detected")) else "PASSED"
    splicing_summary = "Synthetic Matte" if tampering.get("synthetic_matte_detected") else ("Detected" if tampering["splicing_detected"] else "None")
    pipeline_modules.append({
        "stage": 5,
        "name": "Tampering & Watermark Engine",
        "category": "Manipulation Detection",
        "status": st5_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Copy-Move: {'Detected' if tampering['copy_move_detected'] else 'None'} | Splicing: {splicing_summary} | Watermark: {watermark['subtype'] if watermark['watermark_detected'] else 'None'}",
        "findings": st5_findings or ["No keypoint cloning, boundary splicing, or watermarks detected."],
    })

    # ------------------------------------------------------------- STAGE 6: AI & Deepfake Engine + Module 28
    t0 = time.perf_counter()
    robustness_ood = analyze_adversarial_and_ood(image, ai_scores)
    
    # Module 28: AI Synthetic Image Forensics (statistical/mathematical AI detection)
    # Detects: DALL-E 3, Gemini, ChatGPT, Claude, Flux, Midjourney, SD3 using
    # noise uniformity, Fourier spectrum, gradient distribution, chromatic aberration
    file_fmt = None
    try:
        file_fmt = file_path.suffix.lstrip(".").upper()
    except Exception:
        pass
    ai_forensic_result = compute_ai_forensic_score(image, file_format=file_fmt)
    forensic_ai_prob = float(ai_forensic_result.get("ai_forensic_prob", 0.40))

    # Module 28 is reported but not fused into the AI score. Measured on 560
    # labelled images (200 real photos, 360 from current generators) its
    # score had AUC 0.26-0.31: it rates real photos as *more* synthetic than
    # AI images, so blending it in can only move verdicts the wrong way.
    ai_scores = dict(ai_scores)
    ai_scores["forensic_ai_prob"] = round(forensic_ai_prob, 4)

    t1 = time.perf_counter()

    ai_flag = float(ai_scores.get("ensemble_fake_prob", 0.0)) >= 0.50 or float(ai_scores.get("scene_ai_prob", 0.0)) >= 0.50
    forensic_verdict = ai_forensic_result.get("forensic_verdict", "BORDERLINE")
    st6_status = "AI_FLAGGED" if ai_flag else ("SUSPICIOUS" if float(ai_scores.get("scene_ai_prob", 0.0)) >= 0.35 else "PASSED")
    pipeline_modules.append({
        "stage": 6,
        "name": "AI & Deepfake Detection Engine (Neural + M28 Forensic)",
        "category": "AI Forensics",
        "status": st6_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Ensemble Score: {round(ai_scores.get('ensemble_fake_prob', 0.0) * 100, 1)}% | Scene AI detectors: {round(ai_scores.get('scene_ai_prob', 0.0) * 100, 1)}% | M28 heuristic (informational): {round(forensic_ai_prob * 100, 1)}%",
        "findings": [f"Dominant Indicator: {'Synthetic AI Generation' if ai_scores.get('scene_ai_prob', 0) >= ai_scores.get('face_fake_prob', 0) else 'Deepfake Facial Manipulation'}"] if ai_flag else [f"No AI-generation detector crossed its threshold. M28 heuristic: {forensic_verdict} ({round(forensic_ai_prob*100,1)}%; unvalidated, not used in the verdict)."],
    })

    # ------------------------------------------------------------- STAGE 7: Steganography & Provenance
    t0 = time.perf_counter()
    stego = analyze_steganography(image, evidence_dir, job_id)
    provenance_threat = analyze_provenance_and_threats(file_path, hashes)
    t1 = time.perf_counter()

    st7_findings = []
    if provenance_threat.get("ai_generation_disclosed"):
        st7_findings.append(f"C2PA Content Credentials: Disclosed AI generation ({provenance_threat.get('disclosed_generator')}).")
    if stego["lsb_anomaly"]:
        st7_findings.append(f"Stego suspicion: {stego['payload_likelihood']} likelihood on {', '.join(stego['affected_channels']) or 'channels'}.")

    st7_status = "AI_FLAGGED" if provenance_threat.get("ai_generation_disclosed") else ("SUSPICIOUS" if (stego["payload_likelihood"] in ("HIGH", "MEDIUM") or provenance_threat["threat_intel"]["ioc_match"]) else "PASSED")
    c2pa_label = provenance_threat.get("disclosed_generator") or ("Found" if provenance_threat["c2pa_detected"] else "Absent")
    pipeline_modules.append({
        "stage": 7,
        "name": "Steganography & Provenance Authentication",
        "category": "Cyber Forensics",
        "status": st7_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Stego Payload: {stego['payload_likelihood']} ({stego['suspicion_percentage']}%) | C2PA: {c2pa_label} | Threat IOC: {provenance_threat['threat_intel']['threat_level']}",
        "findings": st7_findings or ["LSB bitplane entropy within normal photographic bounds; clean threat IOC profile."],
    })

    # ------------------------------------------------------------- STAGE 8: Evidence Fusion & Risk Scoring
    t0 = time.perf_counter()
    risk_fusion = compute_risk_and_fusion(
        ai_scores=ai_scores,
        tampering=tampering,
        ela=ela,
        stego=stego,
        file_security=file_security,
        metadata=metadata_forensics,
        provenance=provenance_threat,
        camera_stats=camera_stats,
        watermark=watermark,
    )
    ela_path = evidence_dir / ela["heatmap_file"] if ela.get("heatmap_file") else None
    noise_path = evidence_dir / camera_stats["heatmap_file"] if camera_stats.get("heatmap_file") else None
    combined_heatmap = generate_combined_forensic_map(
        image, evidence_dir, job_id, ai_heatmap_path, ela_path, noise_path
    )
    custody = generate_chain_of_custody(file_path, hashes["sha256"], job_id)
    audit = get_model_audit_info()
    t1 = time.perf_counter()

    pipeline_modules.append({
        "stage": 8,
        "name": "Evidence Fusion & Calibrated Risk Engine",
        "category": "Synthesis & Audit",
        "status": "CONSENSUS_REACHED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Risk Score: {risk_fusion['overall_risk_score']}/100 ({risk_fusion['risk_tier']}) | Threat: {risk_fusion.get('dominant_threat')} | Fusion: {risk_fusion['evidence_fusion']['fusion_verdict']}",
        "findings": risk_fusion["evidence_fusion"]["corroborating_signals"] or ["All orthogonal forensic dimensions agree on authenticity."],
    })

    return {
        "updated_ai_scores": ai_scores,
        "pipeline_modules": pipeline_modules,
        "file_security": file_security,
        "hashes": hashes,
        "metadata_forensics": metadata_forensics,
        "tampering": tampering,
        "ela": ela,
        "steganography": stego,
        "camera_stats": camera_stats,
        "watermark": watermark,
        "provenance_threat": provenance_threat,
        "robustness_ood": robustness_ood,
        "risk_engine": risk_fusion,
        "chain_of_custody": custody,
        "model_audit": audit,
        "heatmaps": {
            "ai_heatmap": ai_heatmap_path.name if ai_heatmap_path and ai_heatmap_path.exists() else None,
            "ela_heatmap": ela.get("heatmap_file"),
            "noise_heatmap": camera_stats.get("heatmap_file"),
            "tampering_heatmap": tampering_heatmap,
            "stego_heatmap": stego.get("heatmap_file"),
            "watermark_heatmap": watermark.get("heatmap_file"),
            "combined_heatmap": combined_heatmap,
        },
    }
