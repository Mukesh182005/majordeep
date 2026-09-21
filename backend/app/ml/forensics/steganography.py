"""Steganography and hidden payload detection (Module 9)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image


def _calc_bitplane_entropy(bitplane: np.ndarray) -> float:
    """Calculate Shannon entropy of a binary bitplane."""
    p1 = float(np.mean(bitplane))
    p0 = 1.0 - p1
    if p0 <= 0.0 or p1 <= 0.0:
        return 0.0
    return -(p0 * math.log2(p0) + p1 * math.log2(p1))


def analyze_steganography(image: Image.Image, evidence_dir: Path, job_id: str) -> dict[str, Any]:
    """
    Detect hidden payloads, LSB anomalies, and statistical steganalysis signatures.
    """
    img_np = np.array(image.convert("RGB"))
    h, w, c = img_np.shape

    channel_entropies: dict[str, float] = {}
    channel_anomalies: list[str] = []
    names = ["R", "G", "B"]

    # Extract LSB (bit 0) for each channel
    lsb_planes = []
    for ch_idx, name in enumerate(names):
        plane = img_np[:, :, ch_idx] & 1
        lsb_planes.append(plane)
        ent = _calc_bitplane_entropy(plane)
        channel_entropies[name] = round(ent, 4)
        # Maximal entropy close to 1.0 indicates possible high-entropy payload
        if ent > 0.9992:
            channel_anomalies.append(name)

    # Chi-square sample-pair statistical analysis on Pairs of Values (PoVs)
    # LSB embedding equalizes frequencies of 2k and 2k+1 pairs
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    chi_sq = 0.0
    dof = 0
    equalized_pairs = 0
    total_pairs = 0
    for i in range(0, 256, 2):
        c1, c2 = hist[i], hist[i + 1]
        observed = c1 + c2
        if observed > 20:
            total_pairs += 1
            if abs(c1 - c2) <= 2:
                equalized_pairs += 1
            expected = observed / 2.0
            chi_sq += ((c1 - expected) ** 2) / expected
            dof += 1

    pov_ratio = (equalized_pairs / max(total_pairs, 1))
    # True steganography forces high entropy AND strong PoV equalization
    stego_statistical_match = bool(pov_ratio > 0.65 and len(channel_anomalies) >= 2)
    lsb_anomaly = bool(stego_statistical_match or (len(channel_anomalies) == 3 and pov_ratio > 0.45))

    suspicion_score = 0.0
    if lsb_anomaly:
        suspicion_score = round(min(0.50 + pov_ratio * 0.45, 0.95), 4)
    elif len(channel_anomalies) >= 2:
        suspicion_score = 0.25
    else:
        suspicion_score = 0.05

    if suspicion_score >= 0.70:
        likelihood = "HIGH"
    elif suspicion_score >= 0.35:
        likelihood = "MEDIUM"
    else:
        likelihood = "LOW"

    # Generate visual LSB map artifact
    stego_filename = f"{job_id}_stego.png"
    stego_path = evidence_dir / stego_filename
    lsb_vis = (lsb_planes[0] * 255).astype(np.uint8)
    stego_colored = cv2.applyColorMap(lsb_vis, cv2.COLORMAP_VIRIDIS)
    cv2.imwrite(str(stego_path), stego_colored)

    return {
        "lsb_anomaly": lsb_anomaly,
        "payload_likelihood": likelihood,
        "affected_channels": channel_anomalies,
        "channel_entropies": channel_entropies,
        "suspicion_percentage": round(suspicion_score * 100, 1),
        "heatmap_file": stego_filename,
    }
