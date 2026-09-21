"""Cross-modal audiovisual synchrony and lip-sync forensics (Module 11, 12, 13, 47, 48).

Correlates facial mouth vertical aperture dynamics with acoustic speech energy envelopes
to detect synthetic lip generation, dubbed speech, and audio track replacement.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def analyze_crossmodal_lipsync(
    video_path: str | Path,
    frames_pil: list[tuple[float, Image.Image]],
    face_boxes: list[tuple[int, int, int, int] | None],
) -> dict[str, Any]:
    """Measure synchrony between visual lip aperture dynamics and speech audio energy."""
    # 1. Compute Lip Vertical Aperture Curve from sampled frames
    timestamps: list[float] = []
    mouth_aperture: list[float] = []

    for i, (t_s, pil_img) in enumerate(frames_pil):
        box = face_boxes[i]
        if box is None:
            continue

        x1, y1, x2, y2 = box
        img_np = np.array(pil_img)
        h, w = img_np.shape[:2]
        bx1, by1 = max(0, x1), max(0, y1)
        bx2, by2 = min(w, x2), min(h, y2)
        if bx2 <= bx1 or by2 <= by1:
            continue

        face_crop = img_np[by1:by2, bx1:bx2]
        face_gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
        fh, fw = face_gray.shape

        # Extract mouth region: lower 65% to 92% of face
        my1, my2 = int(fh * 0.65), int(fh * 0.92)
        mx1, mx2 = int(fw * 0.30), int(fw * 0.70)

        if my2 > my1 and mx2 > mx1:
            mouth_roi = face_gray[my1:my2, mx1:mx2]
            # Vertical gradient projection: upper lip and lower lip edges
            v_proj = np.mean(cv2.Sobel(mouth_roi, cv2.CV_64F, 0, 1, ksize=3) ** 2, axis=1)
            if len(v_proj) > 4:
                # Distance between two highest edge peaks in mouth ROI
                peaks = np.argsort(v_proj)[-2:]
                aperture = float(abs(peaks[0] - peaks[1])) / float(len(v_proj))
            else:
                aperture = 0.0

            timestamps.append(t_s)
            mouth_aperture.append(float(aperture))

    # 2. Extract Audio Track from Video Container
    audio_present = False
    audio_energy: list[float] = []
    correlation = 0.0

    try:
        # Check if torchaudio can demux audio stream
        import importlib
        torchaudio = importlib.import_module("torchaudio")

        waveform, sr = torchaudio.load(str(video_path))
        if waveform.numel() > 0:
            audio_present = True
            audio_np = waveform.mean(dim=0).cpu().numpy()
            duration_s = len(audio_np) / float(sr)

            # Compute RMS energy per timestamp window corresponding to frames
            for t in timestamps:
                center_sample = int(t * sr)
                half_window = int(0.15 * sr)  # 300ms window
                s_start = max(0, center_sample - half_window)
                s_end = min(len(audio_np), center_sample + half_window)
                if s_end > s_start:
                    rms = float(np.sqrt(np.mean(audio_np[s_start:s_end] ** 2)))
                else:
                    rms = 0.0
                audio_energy.append(rms)

            if len(mouth_aperture) >= 4 and len(audio_energy) == len(mouth_aperture):
                ap_norm = np.array(mouth_aperture) - np.mean(mouth_aperture)
                en_norm = np.array(audio_energy) - np.mean(audio_energy)
                std_prod = (np.std(ap_norm) * np.std(en_norm))
                if std_prod > 1e-6:
                    correlation = float(np.mean(ap_norm * en_norm) / std_prod)
                    correlation = float(np.clip(correlation, -1.0, 1.0))
    except Exception as exc:
        logger.debug("Audio stream extraction for lip-sync analysis skipped: %s", exc)

    # Cross-modal evaluation
    # Natural speech exhibits positive correlation (mouth opens as acoustic energy rises).
    # Desync or synthetic lip dubbing exhibits negative or near-zero correlation (< 0.10).
    lip_sync_anomaly = False
    anomaly_score = 0.0

    if audio_present and len(mouth_aperture) >= 4:
        if correlation < 0.05:
            lip_sync_anomaly = True
            anomaly_score = round(float(np.clip(0.50 - correlation * 0.5, 0.0, 1.0)), 3)
        else:
            anomaly_score = round(float(np.clip(0.20 - correlation * 0.2, 0.0, 0.4)), 3)

    return {
        "audio_stream_detected": audio_present,
        "lip_sync_analyzed": audio_present and len(mouth_aperture) >= 4,
        "audiovisual_correlation": round(correlation, 3),
        "lip_sync_anomaly_detected": lip_sync_anomaly,
        "lip_sync_anomaly_score": anomaly_score,
        "mouth_aperture_timeline": [round(a, 3) for a in mouth_aperture[:20]],
        "speech_energy_timeline": [round(e, 4) for e in audio_energy[:20]],
        "verdict_reason": (
            "Auditory speech envelope desynchronized with visual lip kinematics"
            if lip_sync_anomaly
            else "Natural speech-to-lip articulation alignment" if audio_present
            else "Audio track absent from video container"
        ),
    }
