"""Scene and shot detection engine (Module 05, 06, 23).

Segments video into chronological scene units using structural color histogram deltas
and edge discontinuity metrics. Allows per-segment deepfake and manipulation scoring.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def detect_scenes_and_shots(
    frames: list[tuple[float, Image.Image]],
    min_scene_duration_s: float = 1.0,
    threshold: float = 0.42,
) -> list[dict[str, Any]]:
    """Segment consecutive sampled frames into distinct scenes based on visual feature deltas.

    Args:
        frames: List of (timestamp_s, PIL Image) tuples.
        min_scene_duration_s: Minimum duration between detected scene cuts.
        threshold: Normalized Chi-Square / Bhattacharyya distance threshold for a shot transition.

    Returns:
        List of scene dictionaries with start/end timestamps and frame indices.
    """
    if not frames:
        return []

    if len(frames) == 1:
        return [{
            "scene_id": 1,
            "start_time_s": round(frames[0][0], 3),
            "end_time_s": round(frames[0][0] + 1.0, 3),
            "duration_s": 1.0,
            "start_frame_idx": 0,
            "end_frame_idx": 0,
            "transition_type": "SINGLE_FRAME",
            "keyframe_timestamp_s": round(frames[0][0], 3),
        }]

    # Convert frames to HSV histograms for illumination-robust shot boundary detection
    hsv_histograms: list[np.ndarray] = []
    for _, pil_img in frames:
        rgb = np.array(pil_img)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        # Compute 2D Hue-Saturation histogram
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        hsv_histograms.append(hist)

    scenes: list[dict[str, Any]] = []
    current_scene_start_idx = 0
    current_scene_start_time = frames[0][0]

    for i in range(len(frames) - 1):
        hist_a = hsv_histograms[i]
        hist_b = hsv_histograms[i + 1]

        # Bhattacharyya distance (0 = identical, 1 = completely different)
        bhatt_dist = float(cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_BHATTACHARYYA))
        time_elapsed = frames[i + 1][0] - current_scene_start_time

        # If visual difference exceeds threshold and enough time passed, declare a scene boundary
        if bhatt_dist >= threshold and time_elapsed >= min_scene_duration_s:
            end_time = frames[i][0]
            # Keyframe is roughly middle frame of scene
            mid_idx = (current_scene_start_idx + i) // 2
            scenes.append({
                "scene_id": len(scenes) + 1,
                "start_time_s": round(current_scene_start_time, 2),
                "end_time_s": round(end_time, 2),
                "duration_s": round(max(0.1, end_time - current_scene_start_time), 2),
                "start_frame_idx": current_scene_start_idx,
                "end_frame_idx": i,
                "transition_type": "HARD_CUT" if bhatt_dist > 0.65 else "SOFT_DISSOLVE",
                "boundary_delta": round(bhatt_dist, 3),
                "keyframe_timestamp_s": round(frames[mid_idx][0], 2),
            })
            current_scene_start_idx = i + 1
            current_scene_start_time = frames[i + 1][0]

    # Final trailing scene
    last_idx = len(frames) - 1
    end_time = frames[last_idx][0]
    mid_idx = (current_scene_start_idx + last_idx) // 2
    scenes.append({
        "scene_id": len(scenes) + 1,
        "start_time_s": round(current_scene_start_time, 2),
        "end_time_s": round(end_time, 2),
        "duration_s": round(max(0.1, end_time - current_scene_start_time), 2),
        "start_frame_idx": current_scene_start_idx,
        "end_frame_idx": last_idx,
        "transition_type": "FINAL_SEGMENT",
        "boundary_delta": 0.0,
        "keyframe_timestamp_s": round(frames[mid_idx][0], 2),
    })

    return scenes
