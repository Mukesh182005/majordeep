"""Optical flow analysis for video deepfakes.

Deepfakes are generated frame-by-frame and pasted back into the video.
This leads to temporal motion inconsistencies at blending boundaries
(jawline, forehead). Dense optical flow reveals these divergent vectors.

NOTE: face boxes are in (x1, y1, x2, y2) format as returned by
``app.ml.faces.extract_faces``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def compute_optical_flow_anomaly(
    frames: list[np.ndarray],
    face_boxes: list[tuple[int, int, int, int] | None],
    evidence_dir: Path | None = None,
    job_id: str | None = None,
) -> tuple[float, dict[str, Any]]:
    """Compute a motion-boundary anomaly score using Farneback dense optical flow.

    Args:
        frames: Consecutive frames as numpy arrays in **RGB** order (H, W, 3)
            or (H, W) grayscale. Must be the same length as ``face_boxes``.
        face_boxes: ``(x1, y1, x2, y2)`` bounding boxes aligned to ``frames``.
        evidence_dir: Directory to persist optical flow visualization heatmap.
        job_id: Unique job identifier for artifact naming.

    Returns:
        tuple[float, dict]: Motion anomaly score [0.0, 1.0] and detailed motion metrics.
    """
    if len(frames) < 2 or len(frames) != len(face_boxes):
        return 0.0, {"per_frame_flow": [], "flow_file": None}

    def to_gray(arr: np.ndarray) -> np.ndarray:
        if arr.ndim == 2:
            return arr.astype(np.uint8)
        return cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY)

    H, W = frames[0].shape[:2]
    anomaly_scores: list[float] = []
    face_bg_divergences: list[float] = []
    worst_flow_vis: np.ndarray | None = None
    max_flow_mag = 0.0

    for i in range(len(frames) - 1):
        try:
            gray1 = to_gray(frames[i])
            gray2 = to_gray(frames[i + 1])
        except Exception as exc:
            logger.warning("Optical flow: frame conversion failed at idx %d: %s", i, exc)
            continue

        try:
            farneback_fn = getattr(cv2, "calcOpticalFlowFarneback")
            flow = farneback_fn(
                gray1, gray2, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
            )
        except Exception as exc:
            logger.warning("Optical flow: Farneback failed at idx %d: %s", i, exc)
            continue

        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        global_var = float(np.var(magnitude))

        box = face_boxes[i]
        if box is None:
            # Full-frame scene motion: normalize variance relative to mean flow
            mean_mag = float(np.mean(magnitude))
            flow_cov = float(np.sqrt(global_var) / (mean_mag + 1e-4))
            score = float(np.clip((flow_cov - 1.2) / 1.5, 0.0, 1.0))
            anomaly_scores.append(score)
            face_bg_divergences.append(0.0)
        else:
            x1, y1, x2, y2 = box
            x1 = max(0, min(x1, W - 1))
            y1 = max(0, min(y1, H - 1))
            x2 = max(x1 + 1, min(x2, W))
            y2 = max(y1 + 1, min(y2, H))

            face_flow = flow[y1:y2, x1:x2]
            if face_flow.size == 0:
                continue

            face_mag, _ = cv2.cartToPolar(face_flow[..., 0], face_flow[..., 1])
            face_var = float(np.var(face_mag))

            # Divergence between face motion and background motion
            bg_mask = np.ones((H, W), dtype=bool)
            bg_mask[y1:y2, x1:x2] = False
            bg_mag = magnitude[bg_mask]
            divergence = float(abs(np.mean(face_mag) - np.mean(bg_mag))) if bg_mag.size > 0 else 0.0
            face_bg_divergences.append(round(divergence, 2))

            # Optical flow anomaly scoring:
            # Natural talking/head turns at 1 FPS sample rate produce face_var ~ 30-100 and divergence ~ 1-4 px.
            # Deepfake face-swaps exhibit boundary warping seams with divergence > 8 px and chaotic flow variance > 250 px^2.
            var_anomaly = float(np.clip((face_var - 90.0) / 220.0, 0.0, 1.0))
            div_anomaly = float(np.clip((divergence - 5.0) / 10.0, 0.0, 1.0))
            score = round(float(0.50 * var_anomaly + 0.50 * div_anomaly), 4)
            anomaly_scores.append(score)

        # Check if this frame had the highest motion variance to save as visual artifact
        curr_peak = float(np.max(magnitude))
        if curr_peak > max_flow_mag and evidence_dir is not None and job_id is not None:
            max_flow_mag = curr_peak
            # Generate HSV flow visualization
            hsv = np.zeros((H, W, 3), dtype=np.uint8)
            hsv[..., 0] = angle * 180 / np.pi / 2
            hsv[..., 1] = 255
            _norm_dst = np.empty_like(magnitude, dtype=np.uint8)
            cv2.normalize(magnitude, _norm_dst, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            hsv[..., 2] = _norm_dst
            worst_flow_vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    final_score = round(float(np.clip(np.mean(anomaly_scores), 0.0, 1.0)), 4) if anomaly_scores else 0.0

    flow_filename: str | None = None
    if worst_flow_vis is not None and evidence_dir is not None and job_id is not None:
        try:
            flow_filename = f"{job_id}_optical_flow.png"
            out_file = evidence_dir / flow_filename
            cv2.imwrite(str(out_file), worst_flow_vis)
        except Exception as exc:
            logger.warning("Failed to save optical flow plate: %s", exc)

    return final_score, {
        "mean_motion_anomaly": final_score,
        "max_motion_anomaly": round(float(np.max(anomaly_scores)), 4) if anomaly_scores else 0.0,
        "face_background_divergence": round(float(np.mean(face_bg_divergences)), 2) if face_bg_divergences else 0.0,
        "per_frame_flow": anomaly_scores,
        "flow_heatmap_file": flow_filename,
    }
