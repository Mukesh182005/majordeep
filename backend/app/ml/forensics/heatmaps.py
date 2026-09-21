"""Multi-forensic heatmap generation and composite fusion (Module 23)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


def generate_tampering_heatmap(
    image: Image.Image,
    evidence_dir: Path,
    job_id: str,
    tampering: dict[str, Any],
) -> str | None:
    """Generate a visual heatmap highlighting copy-move and gradient discontinuity regions."""
    try:
        img_np = np.array(image.convert("RGB"))
        h, w, _ = img_np.shape
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # Edge gradient density map
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        blurred = cv2.GaussianBlur(grad, (15, 15), 0)
        norm_grad = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        colored = cv2.applyColorMap(norm_grad, cv2.COLORMAP_JET)
        # Blend with original
        overlay = cv2.addWeighted(img_np, 0.55, colored, 0.45, 0)
        
        filename = f"{job_id}_tampering.png"
        out_path = evidence_dir / filename
        cv2.imwrite(str(out_path), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        return filename
    except Exception as exc:
        logger.warning("Tampering heatmap generation failed: %s", exc)
        return None


def generate_combined_forensic_map(
    image: Image.Image,
    evidence_dir: Path,
    job_id: str,
    ai_heatmap_path: Path | None,
    ela_heatmap_path: Path | None,
    noise_heatmap_path: Path | None,
) -> str | None:
    """
    Fuse multiple forensic signals into a unified multi-layer anomaly map.
    """
    try:
        img_np = np.array(image.convert("RGB"))
        h, w, _ = img_np.shape
        composite = np.zeros((h, w, 3), dtype=np.float32)
        count = 0

        # Layer 1: ELA
        if ela_heatmap_path and ela_heatmap_path.exists():
            ela_img = cv2.imread(str(ela_heatmap_path))
            if ela_img is not None:
                ela_resized = cv2.resize(ela_img, (w, h)).astype(np.float32)
                composite += ela_resized * 0.35
                count += 1

        # Layer 2: Noise residual
        if noise_heatmap_path and noise_heatmap_path.exists():
            noise_img = cv2.imread(str(noise_heatmap_path))
            if noise_img is not None:
                noise_resized = cv2.resize(noise_img, (w, h)).astype(np.float32)
                composite += noise_resized * 0.35
                count += 1

        # Layer 3: AI Grad-CAM
        if ai_heatmap_path and ai_heatmap_path.exists():
            ai_img = cv2.imread(str(ai_heatmap_path))
            if ai_img is not None:
                ai_resized = cv2.resize(ai_img, (w, h)).astype(np.float32)
                composite += ai_resized * 0.40
                count += 1

        if count == 0:
            return None

        composite_norm = np.clip(composite, 0, 255).astype(np.uint8)
        # Alpha blend with original image
        final_blend = cv2.addWeighted(cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR), 0.50, composite_norm, 0.50, 0)

        combined_filename = f"{job_id}_combined.png"
        out_path = evidence_dir / combined_filename
        cv2.imwrite(str(out_path), final_blend)
        return combined_filename
    except Exception as exc:
        logger.warning("Combined forensic heatmap generation failed: %s", exc)
        return None
