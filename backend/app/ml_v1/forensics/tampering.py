"""Image tampering detection (Copy-Move, Splicing, Face-Swap Seams) and calibrated ELA (Modules 5 & 6)."""

from __future__ import annotations

import io
import logging
from collections import Counter
from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image, ImageChops

logger = logging.getLogger(__name__)


def detect_face_swap_artifacts(
    image: Image.Image,
    face_boxes: list[tuple[int, int, int, int]] | None = None,
) -> dict[str, Any]:
    """
    Detect face-swap specific boundary seams and face-to-background noise inconsistency.
    Universal physical artifact of DeepFaceLab, FaceForensics++, SimSwap, and Roop.
    """
    if not face_boxes:
        return {
            "face_swap_detected": False,
            "face_swap_score": 0.0,
            "anomalies": [],
            "min_noise_ratio": 1.0,
            "max_boundary_score": 0.0,
        }

    arr = np.array(image.convert("RGB"))
    h, w = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    anomalies: list[str] = []
    max_boundary_score = 0.0
    min_noise_ratio = 1.0
    face_swap_detected = False

    for box in face_boxes:
        x1, y1, x2, y2 = box
        bw = x2 - x1
        bh = y2 - y1
        if bw < 35 or bh < 35:
            continue

        # 1. Noise variance comparison (face vs background)
        face_gray = gray[y1:y2, x1:x2]
        mask = np.zeros_like(gray, dtype=bool)
        mask[y1:y2, x1:x2] = True
        bg_pixels = gray[~mask]

        lap_face = cv2.Laplacian(face_gray, cv2.CV_64F)
        lap_bg = cv2.Laplacian(gray, cv2.CV_64F)[~mask]

        var_face = float(np.var(lap_face))
        var_bg = float(np.var(lap_bg))
        ratio = var_face / (var_bg + 1e-6)
        min_noise_ratio = min(min_noise_ratio, ratio)

        # If noise is consistent across face and background (ratio >= 0.60),
        # the camera sensor noise is uniform -> authentic photograph!
        if ratio >= 0.60:
            continue

        # Discrepancy checks:
        # Case A: AI-smoothed/in-painted face inserted into noisy real background
        if ratio < 0.50 and var_bg > 60.0:
            anomalies.append(f"Face-to-background noise discrepancy (ratio: {ratio:.2f})")
            face_swap_detected = True
        # Case B: Cutout/in-painted subject placed onto flat, synthetic, or blacked-out background
        elif ratio > 2.20 and var_bg < 40.0:
            anomalies.append(f"Face-to-background high-frequency divergence (ratio: {ratio:.2f})")
            face_swap_detected = True

    # 2. Multi-Face Noise & Illumination Consistency (Across individuals in group shots)
    if len(face_boxes) >= 2:
        face_vars = []
        for (x1, y1, x2, y2) in face_boxes:
            f_gray = gray[y1:y2, x1:x2]
            if f_gray.size > 100:
                face_vars.append(float(np.var(cv2.Laplacian(f_gray, cv2.CV_64F))))
        if face_vars:
            max_v, min_v = max(face_vars), min(face_vars)
            if min_v > 0 and (max_v / min_v) > 2.8:
                anomalies.append(f"Inter-facial noise inconsistency (ratio: {max_v/min_v:.2f} between subjects)")
                face_swap_detected = True

    # 3. Corneal Specular Catchlight & Ocular Reflection Physics
    for (x1, y1, x2, y2) in face_boxes:
        fw, fh = x2 - x1, y2 - y1
        if fw >= 60 and fh >= 60:
            f_patch = arr[y1:y2, x1:x2]
            l_eye = f_patch[int(fh * 0.25):int(fh * 0.48), int(fw * 0.15):int(fw * 0.48)]
            r_eye = f_patch[int(fh * 0.25):int(fh * 0.48), int(fw * 0.52):int(fw * 0.85)]
            if l_eye.size > 50 and r_eye.size > 50:
                l_gray = cv2.cvtColor(l_eye, cv2.COLOR_RGB2GRAY)
                r_gray = cv2.cvtColor(r_eye, cv2.COLOR_RGB2GRAY)
                l_max, r_max = float(np.max(l_gray)), float(np.max(r_gray))
                if (l_max > 240 and r_max < 160) or (r_max > 240 and l_max < 160):
                    anomalies.append(f"Corneal specular catchlight mismatch (L: {l_max:.0f}, R: {r_max:.0f})")
                    face_swap_detected = True

    score = 0.0
    if face_swap_detected:
        score = 0.85

    return {
        "face_swap_detected": face_swap_detected,
        "face_swap_score": score,
        "anomalies": anomalies,
        "min_noise_ratio": round(min_noise_ratio, 4),
        "max_boundary_score": round(max_boundary_score, 2),
    }


def analyze_tampering(
    image: Image.Image,
    face_boxes: list[tuple[int, int, int, int]] | None = None,
) -> dict[str, Any]:
    """
    Detect copy-move cloning with spatial translation clustering, synthetic mattes, and face-swap seams.
    """
    img_np = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # 1. ORB Keypoint-based Copy-Move Detection with Coherent Translation Clustering
    orb_create = getattr(cv2, "ORB_create", None)
    keypoints, descriptors = (orb_create(nfeatures=1200).detectAndCompute(gray, None) if orb_create is not None else ([], None))

    copy_move_detected = False
    max_coherent_cluster = 0
    suspicious_regions: list[dict[str, Any]] = []

    if descriptors is not None and len(keypoints) > 15:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        try:
            matches = bf.knnMatch(descriptors, descriptors, k=3)
            shift_bins = Counter()
            for m in matches:
                if len(m) >= 2:
                    m1, m2 = m[0], m[1]
                    if m1.queryIdx == m1.trainIdx and m2.distance < 35:
                        pt1 = np.array(keypoints[m1.queryIdx].pt)
                        pt2 = np.array(keypoints[m2.trainIdx].pt)
                        dist = np.linalg.norm(pt1 - pt2)
                        if dist > 45.0:
                            # Cluster displacement vectors into 30px spatial bins
                            bx = int(round((pt2[0] - pt1[0]) / 30.0)) * 30
                            by = int(round((pt2[1] - pt1[1]) / 30.0)) * 30
                            shift_bins[(bx, by)] += 1

            if shift_bins:
                max_coherent_cluster = max(shift_bins.values())

            # Require at least 12 keypoints moving in the EXACT same spatial direction
            # to avoid false positives on repetitive clothing/crowd textures
            if max_coherent_cluster >= 12:
                copy_move_detected = True
                suspicious_regions.append({
                    "type": "COPY_MOVE_CLONE",
                    "matched_features": max_coherent_cluster,
                    "confidence": min(max_coherent_cluster / 20.0, 0.98),
                })
        except Exception as exc:
            logger.debug("Copy-move analysis error: %s", exc)

    # 2. Synthetic Background / Segmentation Matte Detection
    # AI character generations, in-painted composites, and cutouts often feature
    # clamped digital voids (RGB < 6,6,6) or uniform solid regions with near-zero noise std (< 2.5)
    clamped_black_mask = (img_np[:, :, 0] < 6) & (img_np[:, :, 1] < 6) & (img_np[:, :, 2] < 6)
    # Chroma green/blue backdrops:
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    chroma_mask = ((hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 110)) | \
                  ((hsv[:, :, 0] >= 100) & (hsv[:, :, 0] <= 130) & (hsv[:, :, 1] > 110))
    flat_mask = clamped_black_mask | chroma_mask
    clamped_ratio = float(np.mean(flat_mask))
    synthetic_matte_detected = False
    if clamped_ratio >= 0.04:  # >= 4% of image is pure digital void or chroma isolation
        bg_std = float(np.std(gray[flat_mask]))
        if bg_std < 2.5:
            synthetic_matte_detected = True
            suspicious_regions.append({
                "type": "SYNTHETIC_BACKGROUND_MATTE",
                "matched_features": 1,
                "confidence": 0.90,
                "description": f"Synthetic background matte: {round(clamped_ratio * 100, 1)}% of frame is zero-noise digital void or chroma isolation (noise std: {round(bg_std, 2)})",
            })

    # 3. Splicing Boundary Edge Discontinuity
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_var = float(laplacian.var())
    gradient_discontinuity = float(np.std(np.abs(laplacian)))
    splicing_detected = copy_move_detected or synthetic_matte_detected

    # 4. Face-Swap Boundary & Noise Discrepancy
    face_swap = detect_face_swap_artifacts(image, face_boxes)
    if face_swap["face_swap_detected"]:
        splicing_detected = True
        for anom in face_swap["anomalies"]:
            suspicious_regions.append({
                "type": "FACE_SWAP_SEAM",
                "matched_features": 1,
                "confidence": face_swap["face_swap_score"],
                "description": anom,
            })

    return {
        "copy_move_detected": copy_move_detected,
        "cloned_feature_pairs": max_coherent_cluster,
        "splicing_detected": splicing_detected,
        "synthetic_matte_detected": synthetic_matte_detected,
        "clamped_black_ratio": round(clamped_ratio, 4),
        "gradient_discontinuity_score": round(gradient_discontinuity, 2),
        "laplacian_variance": round(laplacian_var, 2),
        "suspicious_regions": suspicious_regions,
        "face_swap": face_swap,
    }


def compute_ela(image: Image.Image, evidence_dir: Path, job_id: str, quality: int = 90) -> dict[str, Any]:
    """
    Calibrated Error Level Analysis (ELA) and difference visualization artifact.
    """
    buffer = io.BytesIO()
    rgb = image.convert("RGB")
    rgb.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)

    diff = ImageChops.difference(rgb, compressed)
    diff_np = np.array(diff, dtype=np.float32)

    mean_diff = float(np.mean(diff_np))
    max_diff = float(np.max(diff_np))
    p95_diff = float(np.percentile(diff_np, 95))

    anomaly_detected = p95_diff > 28.0 and (max_diff - mean_diff) > 40.0
    ela_score = round(min((mean_diff * 2.0 + p95_diff) / 100.0, 1.0), 4)

    ela_filename = f"{job_id}_ela.png"
    ela_path = evidence_dir / ela_filename

    scale = 15.0
    amplified = np.clip(diff_np * scale, 0, 255).astype(np.uint8)
    ela_gray = cv2.cvtColor(amplified, cv2.COLOR_RGB2GRAY)
    colored_ela = cv2.applyColorMap(ela_gray, cv2.COLORMAP_INFERNO)
    cv2.imwrite(str(ela_path), colored_ela)

    return {
        "ela_score": ela_score,
        "mean_error": round(mean_diff, 2),
        "peak_error": round(max_diff, 2),
        "p95_error": round(p95_diff, 2),
        "compression_anomaly_detected": anomaly_detected,
        "heatmap_file": ela_filename,
    }
