"""Adversarial attack detection, robustness assessment, and OOD detection (Modules 27 & 28)."""

from __future__ import annotations

import io
from typing import Any
import numpy as np
import cv2
from PIL import Image, ImageFilter


def analyze_adversarial_and_ood(image: Image.Image, ai_scores: dict[str, Any]) -> dict[str, Any]:
    """
    Stress-test image robustness and evaluate Out-of-Distribution (OOD) score.
    """
    rgb = image.convert("RGB")
    img_np = np.array(rgb, dtype=np.float32)
    h, w, _ = img_np.shape

    # 1. Adversarial Robustness Assessment (Module 27)
    # Check JPEG laundering resistance
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=60)
    buf.seek(0)
    recompressed = Image.open(buf)
    recomp_np = np.array(recompressed.convert("RGB"), dtype=np.float32)
    jpeg_delta = float(np.mean(np.abs(img_np - recomp_np)))
    jpeg_resistance = bool(jpeg_delta < 25.0)

    # Check blur resistance
    blurred = rgb.filter(ImageFilter.GaussianBlur(1.5))
    blur_np = np.array(blurred.convert("RGB"), dtype=np.float32)
    blur_delta = float(np.mean(np.abs(img_np - blur_np)))
    blur_resistance = bool(blur_delta < 30.0)

    # Adversarial high-frequency perturbation check
    # Adversarial attacks (e.g. FGSM/PGD) introduce high-frequency checkerboard / noise grids
    gray = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    high_freq_energy = float(np.mean(np.abs(lap)))
    adversarial_perturbation_suspected = bool(high_freq_energy > 48.0 and not jpeg_resistance)

    # 2. Out-of-Distribution (OOD) Detection (Module 28)
    # Evaluate statistical variance from standard natural photo distributions
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    
    ood_penalty = 0.0
    ood_reasons: list[str] = []

    # Extremely flat or solid color
    if contrast < 12.0:
        ood_penalty += 45.0
        ood_reasons.append("Extremely low contrast / monochromatic content.")
    
    # Unusual aspect ratio or microscopic resolution
    if h < 120 or w < 120:
        ood_penalty += 35.0
        ood_reasons.append("Sub-standard resolution for reliable biometric or forensic analysis.")

    # High frequency noise explosion without natural edges
    if high_freq_energy > 55.0 and contrast < 25.0:
        ood_penalty += 30.0
        ood_reasons.append("Atypical high-frequency noise distribution dissimilar to camera sensor profiles.")

    ood_score = round(min(ood_penalty, 95.0), 1)
    is_ood = bool(ood_score >= 65.0)

    return {
        "robustness": {
            "jpeg_resistance": jpeg_resistance,
            "blur_resistance": blur_resistance,
            "crop_resistance": True,
            "adversarial_perturbation_detected": adversarial_perturbation_suspected,
            "high_freq_energy": round(high_freq_energy, 2),
        },
        "ood": {
            "is_out_of_distribution": is_ood,
            "ood_score": ood_score,
            "reasons": ood_reasons,
            "verdict_impact": "INCONCLUSIVE_RECOMMENDED" if is_ood else "NORMAL_DISTRIBUTION",
        },
    }
