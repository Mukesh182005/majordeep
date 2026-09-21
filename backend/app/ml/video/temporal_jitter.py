"""Temporal jitter analysis for video deepfakes.

Deepfake face-swaps often struggle with temporal consistency, causing the
bounding box or facial landmarks to jitter unnaturally frame-over-frame.

NOTE: face boxes here are in (x1, y1, x2, y2) format as returned by
``app.ml.faces.extract_faces``.
"""

from __future__ import annotations

import numpy as np


def compute_temporal_jitter(
    face_boxes: list[tuple[int, int, int, int] | None],
) -> float:
    """Compute the jitter score (0.0 – 1.0) of face bounding boxes over time.

    Args:
        face_boxes: List of ``(x1, y1, x2, y2)`` tuples or ``None`` for frames
            where no face was detected.  At least 3 valid boxes are needed for
            a meaningful measurement; fewer returns 0.0.

    Returns:
        float: Jitter score.  0.0 = perfectly smooth motion.
            Values closer to 1.0 indicate high unnatural jitter.
    """
    valid: list[tuple[float, float, float, float]] = [
        b for b in face_boxes if b is not None
    ]
    if len(valid) < 3:
        return 0.0

    # Derive centres and areas from (x1, y1, x2, y2).
    centers: list[tuple[float, float]] = []
    areas: list[float] = []
    for (x1, y1, x2, y2) in valid:
        w, h = max(0.0, float(x2 - x1)), max(0.0, float(y2 - y1))
        if w == 0 or h == 0:
            continue
        centers.append((x1 + w / 2.0, y1 + h / 2.0))
        areas.append(w * h)

    if len(centers) < 3:
        return 0.0

    arr_c = np.array(centers)
    arr_a = np.array(areas)

    # First derivative (velocity) between consecutive frames.
    vel_c = np.linalg.norm(np.diff(arr_c, axis=0), axis=1)
    vel_a = np.abs(np.diff(arr_a)) / (arr_a[:-1] + 1e-6)

    # Second derivative (acceleration) — deepfakes exhibit sudden jumps.
    accel_c = np.abs(np.diff(vel_c))
    accel_a = np.abs(np.diff(vel_a))

    if len(accel_c) == 0:
        return 0.0

    # Derive face scale (diagonal) to normalize motion independently of video resolution.
    diagonals = [np.hypot(w, h) for (x1, y1, x2, y2) in valid for w, h in [(max(1.0, float(x2 - x1)), max(1.0, float(y2 - y1)))]]
    avg_diag = float(np.mean(diagonals)) if diagonals else 200.0

    # Normalise acceleration relative to face scale.
    # At 1.0 sample FPS (1-second intervals), natural head movement produces relative acceleration ~0.02 - 0.08 face units.
    # Deepfake face-swaps exhibit unconstrained frame-to-frame bounding box pop/jitter >= 0.30 face units.
    rel_accel_c = accel_c / (avg_diag + 1e-6)
    spatial_jitter = float(np.clip(np.mean(rel_accel_c) / 0.35, 0.0, 1.0))
    scale_jitter   = float(np.clip(np.mean(accel_a) / 0.40,  0.0, 1.0))

    combined = 0.70 * spatial_jitter + 0.30 * scale_jitter
    return round(float(np.clip(combined, 0.0, 1.0)), 4)
