from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _compute_noise_uniformity(img_np: np.ndarray) -> float:
    gray = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0.8)
    residual = gray - denoised
    h, w = residual.shape
    block_size = 64
    block_stds = []
    for y in range(0, h - block_size, block_size):
        for x in range(0, w - block_size, block_size):
            block = residual[y:y + block_size, x:x + block_size]
            block_stds.append(float(np.std(block)))
    if not block_stds:
        return 0.5
    mean_std = np.mean(block_stds)
    cv_of_stds = np.std(block_stds) / (mean_std + 1e-6)
    if mean_std < 0.40:
        return min(0.95, 0.65 + (0.40 - mean_std) * 0.75)
    elif cv_of_stds < 0.10:
        return min(0.90, 0.55 + (0.10 - cv_of_stds) * 3.0)
    elif cv_of_stds < 0.18 and mean_std < 1.2:
        return 0.50
    else:
        return max(0.05, 0.35 - (cv_of_stds - 0.18) * 0.5)


def _compute_fourier_ai_score(img_np: np.ndarray) -> float:
    gray = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float64)
    h, w = gray.shape
    gray = gray[:h - h % 2, :w - w % 2]
    eh, ew = gray.shape
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = np.abs(fshift) + 1e-6
    cy, cx = eh // 2, ew // 2
    max_r = min(cy, cx)
    y_g, x_g = np.ogrid[:eh, :ew]
    r_grid = np.hypot(x_g - cx, y_g - cy).astype(np.int32)
    tbin = np.bincount(r_grid.ravel(), mag.ravel())
    nr = np.bincount(r_grid.ravel())
    radial = tbin / (nr + 1e-6)
    r_start, r_end = 8, min(int(max_r * 0.80), len(radial) - 1)
    if r_end - r_start < 10:
        return 0.50
    r_vals = np.arange(r_start, r_end)
    p_vals = radial[r_start:r_end]
    valid = p_vals > 0
    if np.sum(valid) < 8:
        return 0.50
    log_r = np.log(r_vals[valid])
    log_p = np.log(p_vals[valid])
    slope, _ = np.polyfit(log_r, log_p, 1)
    alpha = -slope
    if alpha < 1.10:
        return min(0.92, 0.75 + (1.10 - alpha) * 0.30)
    elif alpha < 1.40:
        return min(0.80, 0.50 + (1.40 - alpha) * 0.85)
    elif alpha < 1.60:
        return 0.40
    elif alpha <= 2.80:
        return max(0.05, 0.25 - (alpha - 1.60) * 0.10)
    else:
        return min(0.60, 0.30 + (alpha - 2.80) * 0.10)


def _compute_gradient_uniformity(img_np: np.ndarray) -> float:
    gray = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    sobel_x = cv2.Sobel(gray.astype(np.float64), cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray.astype(np.float64), cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
    flat = grad_mag.flatten()
    mean_g = float(np.mean(flat))
    std_g = float(np.std(flat))
    cv_g = std_g / (mean_g + 1e-6)
    p95 = float(np.percentile(flat, 95))
    p50 = float(np.percentile(flat, 50))
    tail_ratio = p95 / (p50 + 1e-6)
    score = 0.0
    if cv_g < 0.80:
        score += 0.35
    elif cv_g < 1.00:
        score += 0.15
    if tail_ratio < 2.80:
        score += 0.30
    elif tail_ratio < 3.50:
        score += 0.10
    return min(0.85, score)


def _compute_chromatic_coherence(img_np: np.ndarray) -> float:
    r = img_np[:, :, 0].astype(np.float32)
    g = img_np[:, :, 1].astype(np.float32)
    b = img_np[:, :, 2].astype(np.float32)
    gray = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 200)
    edge_mask = edges > 0
    if np.sum(edge_mask) < 100:
        return 0.40
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    near_edge_mask = (dilated > 0) & ~edge_mask
    if np.sum(near_edge_mask) < 50:
        return 0.40
    r_near = r[near_edge_mask]
    g_near = g[near_edge_mask]
    b_near = b[near_edge_mask]
    rg_diff = np.abs(r_near - g_near)
    bg_diff = np.abs(b_near - g_near)
    ca_signal = float(np.std(rg_diff) + np.std(bg_diff))
    if ca_signal < 2.5:
        return 0.75
    elif ca_signal < 3.5:
        return 0.55
    elif ca_signal < 5.0:
        return 0.35
    else:
        return 0.10


def _compute_compression_history(img_np: np.ndarray, img_pil: Image.Image) -> float:
    import io
    buf = io.BytesIO()
    img_pil.save(buf, format='JPEG', quality=95, subsampling=0)
    buf.seek(0)
    try:
        recompressed = np.array(Image.open(buf).convert('RGB'), dtype=np.float32)
        original = img_np.astype(np.float32)
        if recompressed.shape != original.shape:
            recompressed = cv2.resize(recompressed, (original.shape[1], original.shape[0]))
        diff = np.abs(original - recompressed)
        mean_diff = float(np.mean(diff))
        if mean_diff < 0.5:
            return 0.70
        elif mean_diff < 1.5:
            return 0.55
        elif mean_diff < 3.0:
            return 0.35
        else:
            return 0.15
    except Exception:
        return 0.40


def compute_ai_forensic_score(
    image: Image.Image,
    file_format: str | None = None,
) -> dict[str, Any]:
    """Run the AI Synthetic Image Forensics suite (Module 28).
    
    Detects AI-synthesized images from DALL-E 3, Gemini, ChatGPT, Claude,
    Flux, Stable Diffusion 3, Midjourney v6, and similar generators using
    pure mathematical/statistical analysis without neural networks.
    Works at all resolutions including 4K/8K.
    """
    try:
        w, h = image.size
        max_analysis_dim = 2048
        if max(w, h) > max_analysis_dim:
            scale = max_analysis_dim / max(w, h)
            rw, rh = int(w * scale), int(h * scale)
            img_analyze = image.resize((rw, rh), Image.LANCZOS)
        else:
            img_analyze = image

        img_np = np.array(img_analyze.convert("RGB"), dtype=np.float32)
        img_pil_rgb = img_analyze.convert("RGB")
        is_png = (file_format or "").upper() == "PNG"

        noise_prob = _compute_noise_uniformity(img_np)
        fourier_prob = _compute_fourier_ai_score(img_np)
        gradient_prob = _compute_gradient_uniformity(img_np)
        ca_prob = _compute_chromatic_coherence(img_np)

        if not is_png:
            compression_prob = _compute_compression_history(img_np, img_pil_rgb)
        else:
            compression_prob = 0.60 if (noise_prob > 0.55 and ca_prob > 0.45) else 0.45

        weights = {"noise": 0.30, "fourier": 0.28, "gradient": 0.17, "chromatic": 0.15, "compression": 0.10}
        raw_score = (
            noise_prob * weights["noise"]
            + fourier_prob * weights["fourier"]
            + gradient_prob * weights["gradient"]
            + ca_prob * weights["chromatic"]
            + compression_prob * weights["compression"]
        )

        strong_ai_count = sum([1 for p in [noise_prob, fourier_prob, gradient_prob, ca_prob] if p >= 0.55])
        if strong_ai_count >= 3:
            raw_score = max(raw_score, 0.65)
        elif strong_ai_count >= 2:
            raw_score = max(raw_score, 0.50)

        pixel_count = w * h
        if pixel_count >= 8_000_000 and raw_score >= 0.40:
            raw_score = min(raw_score + 0.08, 0.92)
        elif pixel_count >= 4_000_000 and raw_score >= 0.42:
            raw_score = min(raw_score + 0.05, 0.88)

        ai_forensic_prob = float(round(min(max(raw_score, 0.0), 1.0), 4))

        logger.debug(
            "AI Forensic M28: prob=%.3f | noise=%.3f fourier=%.3f gradient=%.3f ca=%.3f comp=%.3f",
            ai_forensic_prob, noise_prob, fourier_prob, gradient_prob, ca_prob, compression_prob,
        )

        return {
            "ai_forensic_prob": ai_forensic_prob,
            "forensic_verdict": "AI_SYNTHESIS_LIKELY" if ai_forensic_prob >= 0.55 else (
                "BORDERLINE" if ai_forensic_prob >= 0.40 else "AUTHENTIC_LIKELY"
            ),
            "sub_scores": {
                "noise_uniformity": round(noise_prob, 4),
                "fourier_spectrum": round(fourier_prob, 4),
                "gradient_distribution": round(gradient_prob, 4),
                "chromatic_aberration_absence": round(ca_prob, 4),
                "compression_history": round(compression_prob, 4),
            },
            "strong_ai_signal_count": strong_ai_count,
            "resolution_pixels": pixel_count,
            "analysis_resolution": f"{img_analyze.width}x{img_analyze.height}",
        }
    except Exception as exc:
        logger.warning("AI forensic detection failed: %s", exc)
        return {
            "ai_forensic_prob": 0.40,
            "forensic_verdict": "ANALYSIS_FAILED",
            "sub_scores": {},
            "strong_ai_signal_count": 0,
            "resolution_pixels": image.width * image.height,
            "analysis_resolution": f"{image.width}x{image.height}",
        }
