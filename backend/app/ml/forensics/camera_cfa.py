"""Camera fingerprinting, CFA demosaicing, and statistical image forensics (Modules 13, 14, 15)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
import cv2
from PIL import Image


def analyze_camera_and_cfa(image: Image.Image, evidence_dir: Path, job_id: str) -> dict[str, Any]:
    """
    Extract PRNU-like sensor noise residual, demosaicing periodicity, and high-order statistical moments.
    """
    img_np = np.array(image.convert("RGB"), dtype=np.float32)
    h, w, c = img_np.shape

    # 1. PRNU Sensor Noise Residual Extraction (Module 13)
    # Residual = Original - Denoised (using median filter as clean approximation)
    denoised = cv2.medianBlur(img_np.astype(np.uint8), 3).astype(np.float32)
    residual = img_np - denoised
    residual_gray = cv2.cvtColor(residual, cv2.COLOR_RGB2GRAY)

    noise_variance = float(np.var(residual_gray))
    noise_std = float(np.std(residual_gray))

    # 2. CFA / Demosaicing Periodicity Analysis (Module 14)
    # Real camera demosaicing produces periodic 2x2 Bayer interpolation correlations
    green = img_np[:, :, 1]
    # Demosaicing residual in green channel
    g_denoised = cv2.GaussianBlur(green, (3, 3), 0.5)
    g_res = green - g_denoised
    
    # 2D Fourier transform to detect periodic CFA peaks
    f = np.fft.fft2(g_res)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-6)

    # Detect high-frequency periodic demosaicing peak ratio
    center_y, center_x = h // 2, w // 2
    hf_region = magnitude_spectrum[center_y - 20:center_y + 20, center_x - 20:center_x + 20]
    cfa_peak_ratio = float(np.max(magnitude_spectrum) / (np.mean(hf_region) + 1e-4))

    # Real camera Bayer sensors typically show cfa_peak_ratio > 2.5 with natural noise std 1.2 - 6.0
    cfa_detected = cfa_peak_ratio > 2.5 and noise_std > 0.8
    
    if cfa_detected and noise_std > 1.8:
        estimated_camera = "Physical Digital Camera (DSLR / Smartphone)"
        fingerprint_detected = True
        camera_consistency = 0.88
    elif (cfa_peak_ratio < 1.8 and noise_std < 1.6) or noise_std < 0.6:
        estimated_camera = "Synthetic / AI-Rendered (Missing Sensor Artifacts)"
        fingerprint_detected = False
        camera_consistency = 0.22
    else:
        estimated_camera = "Smartphone / Compressed Web Media"
        fingerprint_detected = True
        camera_consistency = 0.65

    # 3. Statistical Image Forensics (Module 15)
    r_chan, g_chan, b_chan = img_np[:, :, 0], img_np[:, :, 1], img_np[:, :, 2]

    def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
        """Pearson correlation safe against zero-variance (uniform) channels."""
        if np.std(a) < 1e-6 or np.std(b) < 1e-6:
            return 0.0
        return float(np.corrcoef(a.flatten(), b.flatten())[0, 1])

    # Inter-channel Pearson correlations
    corr_rg = _safe_corr(r_chan, g_chan)
    corr_gb = _safe_corr(g_chan, b_chan)
    corr_rb = _safe_corr(r_chan, b_chan)

    # Moments: skewness and kurtosis
    gray_flat = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).flatten().astype(np.float64)
    _gray_std = float(np.std(gray_flat))
    if _gray_std < 1e-3:
        # Degenerate / near-uniform distribution — moments are meaningless
        skewness = 0.0
        kurtosis = 0.0
    else:
        _diff = gray_flat - np.mean(gray_flat)
        _m2 = np.mean(_diff ** 2)
        _m3 = np.mean(_diff ** 3)
        _m4 = np.mean(_diff ** 4)
        skewness = float(_m3 / (_m2 ** 1.5 + 1e-9))
        kurtosis = float((_m4 / (_m2 ** 2 + 1e-9)) - 3.0)

    # High-frequency edge gradient distribution
    sobel_x = cv2.Sobel(gray_flat.reshape(h, w), cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_flat.reshape(h, w), cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    gradient_mean = float(np.mean(gradient_mag))

    # 4. Fourier Azimuthal Radial Decay & 2D Wavelet DWT Decomposition (Module 15B)
    gray_even = gray_flat.reshape(h, w)[:h - h % 2, :w - w % 2]
    eh, ew = gray_even.shape
    f_full = np.fft.fft2(gray_even)
    f_shift = np.fft.fftshift(f_full)
    mag_full = np.abs(f_shift) + 1e-6
    cy, cx = eh // 2, ew // 2
    max_r = min(cy, cx)
    y_g, x_g = np.ogrid[:eh, :ew]
    r_grid = np.hypot(x_g - cx, y_g - cy).astype(np.int32)
    tbin = np.bincount(r_grid.ravel(), mag_full.ravel())
    nr = np.bincount(r_grid.ravel())
    radial_prof = tbin / (nr + 1e-6)

    r_start = 10
    r_end = max(r_start + 5, int(max_r * 0.85))
    r_vals = np.arange(r_start, r_end)
    p_vals = radial_prof[r_start:r_end]
    valid = p_vals > 0
    if np.sum(valid) > 5:
        log_r = np.log(r_vals[valid])
        log_p = np.log(p_vals[valid])
        slope_res, _ = np.polyfit(log_r, log_p, 1)
        fourier_slope_alpha = float(round(-slope_res, 3))
    else:
        fourier_slope_alpha = 2.0

    # 2D Haar Wavelet Diagonal (HH) subband
    hh_subband = (gray_even[0::2, 0::2] - gray_even[0::2, 1::2] - gray_even[1::2, 0::2] + gray_even[1::2, 1::2]) * 0.5
    hh_fft = np.abs(np.fft.fftshift(np.fft.fft2(hh_subband)))
    wavelet_grid_peak = float(round(float(np.max(hh_fft) / (np.mean(hh_fft) + 1e-4)), 2))

    # 5. Save Noise Residual Heatmap Artifact
    noise_filename = f"{job_id}_noise.png"
    noise_path = evidence_dir / noise_filename
    _src = np.abs(residual_gray)
    _dst = np.empty_like(_src, dtype=np.uint8)
    norm_noise = cv2.normalize(_src, _dst, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    noise_colored = cv2.applyColorMap(norm_noise, cv2.COLORMAP_TURBO)
    cv2.imwrite(str(noise_path), noise_colored)

    return {
        "camera_fingerprint_detected": fingerprint_detected,
        "synthetic_sensor_detected": not fingerprint_detected and estimated_camera.startswith("Synthetic"),
        "estimated_camera_family": estimated_camera,
        "camera_consistency_score": round(camera_consistency, 2),
        "cfa_artifacts_detected": cfa_detected,
        "cfa_periodicity_ratio": round(cfa_peak_ratio, 2),
        "sensor_noise_std": round(noise_std, 3),
        "sensor_noise_variance": round(noise_variance, 3),
        "fourier_spectral_slope": fourier_slope_alpha,
        "wavelet_grid_peak_ratio": wavelet_grid_peak,
        "statistical_moments": {
            "skewness": round(skewness, 3),
            "kurtosis": round(kurtosis, 3),
            "gradient_mean": round(gradient_mean, 2),
            "channel_correlation_rg": round(corr_rg, 3),
            "channel_correlation_gb": round(corr_gb, 3),
            "channel_correlation_rb": round(corr_rb, 3),
        },
        "heatmap_file": noise_filename,
    }
