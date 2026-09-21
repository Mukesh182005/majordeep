"""Watermark detection module: identifies visible logos/badges, AI generator stamps, and digital frequency watermarks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


def _detect_dalle_watermark(img_rgb: np.ndarray) -> dict[str, Any] | None:
    """
    Detect DALL-E's signature 5-color block watermark in the bottom-right corner.
    Strictly verifies all 5 sequential color squares: Yellow, Cyan, Green, Red, Blue.
    """
    h, w, _ = img_rgb.shape
    ymin, xmin = int(h * 0.88), int(w * 0.78)
    corner = img_rgb[ymin:h, xmin:w]
    ch, cw, _ = corner.shape
    if ch < 10 or cw < 35:
        return None

    hsv = cv2.cvtColor(corner, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # DALL-E blocks are pure saturated, bright colors
    vibrant_mask = (sat > 130) & (val > 130)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 3))
    vibrant_connected = cv2.morphologyEx(vibrant_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(vibrant_connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh) if bh > 0 else 0
        if 4.0 <= aspect <= 7.0 and 25 <= bw <= 120 and 5 <= bh <= 22:
            patch_hsv = hsv[y:y + bh, x:x + bw]
            seg_w = bw // 5
            if seg_w < 4:
                continue
            hues = []
            for i in range(5):
                seg = patch_hsv[:, i * seg_w:(i + 1) * seg_w]
                if float(np.mean(seg[:, :, 1])) < 110 or float(np.mean(seg[:, :, 2])) < 110:
                    break
                hues.append(float(np.median(seg[:, :, 0])))
            
            # Yellow (~20-40), Cyan (~80-108), Green (~43-78), Red (<18 or >162), Blue (~108-138)
            if len(hues) == 5:
                is_yellow = 18 <= hues[0] <= 42
                is_cyan = 80 <= hues[1] <= 110
                is_green = 43 <= hues[2] <= 78
                is_red = (hues[3] <= 18 or hues[3] >= 162)
                is_blue = 108 <= hues[4] <= 138
                if is_yellow and is_cyan and is_green and is_red and is_blue:
                    abs_box = [xmin + x, ymin + y, xmin + x + bw, ymin + y + bh]
                    return {
                        "type": "AI_GENERATOR_STAMP",
                        "subtype": "DALL-E Chromatic Badge",
                        "confidence": 0.98,
                        "box": abs_box,
                        "location": "bottom-right corner",
                    }
    return None


def _detect_corner_badges(img_rgb: np.ndarray) -> dict[str, Any] | None:
    """
    Detect genuine high-contrast logo badges or platform stamps in corners.
    Requires distinct artificial glyph/text contours, high sharpness, and high edge concentration.
    """
    h, w, _ = img_rgb.shape
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    corners = {
        "bottom-right corner": (int(h * 0.90), h, int(w * 0.85), w),
        "bottom-left corner": (int(h * 0.90), h, 0, int(w * 0.15)),
        "top-right corner": (0, int(h * 0.10), int(w * 0.85), w),
        "top-left corner": (0, int(h * 0.10), 0, int(w * 0.15)),
    }

    full_edges = cv2.Canny(gray, 80, 200)
    baseline_density = float(np.mean(full_edges > 0))

    best_badge = None
    max_score = 0.0

    for loc_name, (y1, y2, x1, x2) in corners.items():
        crop_gray = gray[y1:y2, x1:x2]
        ch, cw = crop_gray.shape
        if ch < 20 or cw < 20:
            continue

        crop_edges = full_edges[y1:y2, x1:x2]
        corner_density = float(np.mean(crop_edges > 0))

        # Real logo badges have strong, dense edge strokes (text or icons)
        if corner_density < 0.25:
            continue

        # Contrast ratio against the whole image must be significantly higher
        contrast_ratio = (corner_density + 1e-4) / (baseline_density + 1e-4)
        if contrast_ratio < 4.0:
            continue

        thresh = cv2.adaptiveThreshold(crop_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            bx, by, bw, bh = cv2.boundingRect(c)
            area = bw * bh
            corner_area = ch * cw
            rel_area = area / float(corner_area)
            aspect = bw / float(bh) if bh > 0 else 0

            # Badges typically have specific compact rectangular/square aspect ratios
            if 0.08 <= rel_area <= 0.50 and 0.8 <= aspect <= 4.0 and bw > 25 and bh > 15:
                # Check for high internal gradient variance (sharp artificial lines vs soft natural textures)
                patch = crop_gray[by:by + bh, bx:bx + bw]
                grad_x = cv2.Sobel(patch, cv2.CV_32F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(patch, cv2.CV_32F, 0, 1, ksize=3)
                grad_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
                mean_grad = float(np.mean(grad_mag))
                
                # Real logos have high gradient contrast (> 45.0)
                if mean_grad > 45.0:
                    score = min(0.85 + (contrast_ratio - 4.0) * 0.03, 0.96)
                    if score > max_score and score >= 0.88:
                        max_score = score
                        best_badge = {
                            "type": "VISIBLE_LOGO_BADGE",
                            "subtype": "Corner Stamp / Logo",
                            "confidence": round(score, 3),
                            "box": [x1 + bx, y1 + by, x1 + bx + bw, y1 + by + bh],
                            "location": loc_name,
                        }

    return best_badge


def _detect_semi_transparent_watermark(img_rgb: np.ndarray) -> dict[str, Any] | None:
    """
    Detect semi-transparent text or diagonal grid watermarks (e.g. stock photo overlays).
    Requires multiple distinct, non-collinear parallel lines across the frame to prevent
    false positives on natural diagonal lines.
    """
    h, w, _ = img_rgb.shape
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    cy1, cy2 = int(h * 0.15), int(h * 0.85)
    cx1, cx2 = int(w * 0.15), int(w * 0.85)
    center = gray[cy1:cy2, cx1:cx2]

    edges = cv2.Canny(center, 60, 180)
    min_len = int(min(h, w) * 0.25)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=90, minLineLength=min_len, maxLineGap=15)

    if lines is None:
        return None

    rhos_pos = []
    rhos_neg = []
    for line in lines:
        x1, y1, x2, y2 = line.ravel()
        dx, dy = x2 - x1, y2 - y1
        angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
        if 32 <= angle <= 58:
            # Positive diagonal slope
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                c = (y1 + y2) / 2.0 - (x1 + x2) / 2.0
                rhos_pos.append(c)
            else:
                c = (y1 + y2) / 2.0 + (x1 + x2) / 2.0
                rhos_neg.append(c)

    def cluster_intercepts(intercepts, tol=60):
        if not intercepts:
            return []
        sorted_i = sorted(intercepts)
        clusters = [[sorted_i[0]]]
        for val in sorted_i[1:]:
            if abs(val - np.mean(clusters[-1])) < tol:
                clusters[-1].append(val)
            else:
                clusters.append([val])
        return clusters

    c_pos = cluster_intercepts(rhos_pos, tol=60)
    c_neg = cluster_intercepts(rhos_neg, tol=60)

    extent = h + w
    best_clusters = c_pos if len(c_pos) >= len(c_neg) else c_neg
    max_distinct_lines = len(best_clusters)

    span_ratio = 0.0
    if max_distinct_lines >= 2:
        means = [float(np.mean(c)) for c in best_clusters]
        span_ratio = (max(means) - min(means)) / extent

    # Real stock watermark grids have at least 7 repeating parallel lines covering >= 45% of image
    if max_distinct_lines >= 7 and span_ratio >= 0.45:
        return {
            "type": "SEMI_TRANSPARENT_OVERLAY",
            "subtype": "Diagonal Watermark Grid / Text",
            "confidence": round(min(0.85 + max_distinct_lines * 0.02, 0.95), 3),
            "box": [cx1, cy1, cx2, cy2],
            "location": "center diagonal",
        }
    return None


def _detect_frequency_watermark(img_rgb: np.ndarray) -> dict[str, Any] | None:
    """
    Detect statistical / invisible frequency watermarks (e.g. SynthID / mid-frequency DCT rings).
    """
    h, w, _ = img_rgb.shape
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    mag = np.log(np.abs(fshift) + 1e-5)

    ch, cw = h // 2, w // 2
    r_min = int(min(ch, cw) * 0.25)
    r_max = int(min(ch, cw) * 0.65)

    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - cw) ** 2 + (y - ch) ** 2)
    mid_mask = (dist >= r_min) & (dist <= r_max)

    mid_vals = mag[mid_mask]
    if len(mid_vals) > 0:
        std_mid = float(np.std(mid_vals))
        kurt_mid = float(np.mean(((mid_vals - np.mean(mid_vals)) / (std_mid + 1e-5)) ** 4) - 3.0)
        # Strict threshold to avoid false alarms on normal textured photos
        if kurt_mid > 7.0 and std_mid > 3.2:
            return {
                "type": "FREQUENCY_WATERMARK",
                "subtype": "Digital Mid-Frequency Ring Resonance (SynthID-like)",
                "confidence": round(min(0.85 + (kurt_mid - 7.0) * 0.02, 0.95), 3),
                "box": None,
                "location": "frequency domain",
            }
    return None


def analyze_watermark(
    image: Image.Image,
    evidence_dir: Path,
    job_id: str,
) -> dict[str, Any]:
    """
    Comprehensive watermark analysis: checks AI stamps, corner badges, transparent text, and frequency watermarks.
    """
    img_rgb = np.array(image.convert("RGB"))
    h, w, _ = img_rgb.shape

    findings: list[str] = []
    detected = False
    watermark_type = "NONE"
    subtype = "None"
    confidence = 0.0
    location = "none"
    bounding_box = None

    # 1. Check AI Generator watermark (DALL-E 5-color badge)
    dalle_res = _detect_dalle_watermark(img_rgb)
    if dalle_res:
        detected = True
        watermark_type = dalle_res["type"]
        subtype = dalle_res["subtype"]
        confidence = dalle_res["confidence"]
        location = dalle_res["location"]
        bounding_box = dalle_res["box"]
        findings.append(f"AI generator watermark detected: {subtype} in {location}.")

    # 2. Check Corner Logos / Stamps
    if not detected:
        corner_res = _detect_corner_badges(img_rgb)
        if corner_res:
            detected = True
            watermark_type = corner_res["type"]
            subtype = corner_res["subtype"]
            confidence = corner_res["confidence"]
            location = corner_res["location"]
            bounding_box = corner_res["box"]
            findings.append(f"Visible watermark/logo badge detected in {location} ({subtype}).")

    # 3. Check Semi-Transparent / Diagonal Watermark Overlay
    if not detected:
        trans_res = _detect_semi_transparent_watermark(img_rgb)
        if trans_res:
            detected = True
            watermark_type = trans_res["type"]
            subtype = trans_res["subtype"]
            confidence = trans_res["confidence"]
            location = trans_res["location"]
            bounding_box = trans_res["box"]
            findings.append(f"Semi-transparent watermark pattern detected: {subtype}.")

    # 4. Check Frequency-Domain / Invisible Digital Watermark
    if not detected:
        freq_res = _detect_frequency_watermark(img_rgb)
        if freq_res:
            detected = True
            watermark_type = freq_res["type"]
            subtype = freq_res["subtype"]
            confidence = freq_res["confidence"]
            location = freq_res["location"]
            findings.append(f"Invisible digital watermark artifact detected: {subtype}.")

    # 5. Generate Visual Watermark Overlay Artifact
    heatmap_filename = f"{job_id}_watermark.png"
    out_path = evidence_dir / heatmap_filename
    vis = img_rgb.copy()

    if bounding_box:
        x1, y1, x2, y2 = bounding_box
        overlay = vis.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
        vis = cv2.addWeighted(vis, 0.65, overlay, 0.35, 0)
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(
            vis,
            f"WATERMARK ({subtype})",
            (max(0, x1 - 5), max(15, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
    elif detected and location == "frequency domain":
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        fshift = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32)))
        mag = 20 * np.log(np.abs(fshift) + 1)
        norm_mag = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)  # type: ignore
        color_freq = cv2.applyColorMap(norm_mag, cv2.COLORMAP_MAGMA)
        vis = cv2.addWeighted(vis, 0.40, color_freq, 0.60, 0)

    cv2.imwrite(str(out_path), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))

    return {
        "watermark_detected": detected,
        "watermark_type": watermark_type,
        "subtype": subtype,
        "confidence": confidence,
        "location": location,
        "bounding_box": bounding_box,
        "findings": findings,
        "heatmap_file": heatmap_filename if detected else None,
    }
