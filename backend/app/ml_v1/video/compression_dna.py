"""Compression fingerprint analysis for video deepfake detection.

Deepfakes are re-encoded videos: the original frames are replaced with
synthesised ones and re-compressed. This typically leaves detectable traces:

* Lower-than-expected average bitrate for the resolution/FPS
* Abnormally regular I-frame spacing (GCD patterns from re-encoding)
* Truncated high-frequency DCT coefficients (over-quantization)

We use FFprobe when available; otherwise we fall back to file-level heuristics.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_compression_fingerprint(video_path: str | Path) -> float:
    """Compute a re-encoding anomaly score from video compression structure.

    Returns a float in [0.0, 1.0] where higher = more likely re-encoded.
    """
    path = Path(video_path)
    if not path.exists():
        return 0.0

    if shutil.which("ffprobe"):
        try:
            return _ffprobe_analysis(path)
        except Exception as exc:
            logger.debug("FFprobe compression analysis failed (%s); using heuristic.", exc)

    return _heuristic_analysis(path)


# ── FFprobe-based analysis ────────────────────────────────────────────────────

def _ffprobe_analysis(path: Path) -> float:
    """Query FFprobe for packet-level bitrate and I-frame spacing stats."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_packets",
        "-select_streams", "v:0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe exited {result.returncode}")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    packets = data.get("packets", [])

    score = 0.0

    # ── Bitrate vs resolution sanity check ──────────────────────────────────
    if streams:
        stream = streams[0]
        width  = stream.get("width",  0)
        height = stream.get("height", 0)
        pixels = width * height
        # Camera-original 720p at 30fps ≈ 3-5 Mbps; deepfake exports are often
        # re-compressed at 1-2 Mbps to keep file sizes down.
        bitrate_str = stream.get("bit_rate") or stream.get("avg_frame_rate", "")
        try:
            bitrate_bps = float(bitrate_str)
            # Expected: ~4 bits/pixel/s at 30fps is typical camera.
            fps_str = stream.get("avg_frame_rate", "30/1")
            num, den = (fps_str.split("/") + ["1"])[:2]
            fps = float(num) / max(float(den), 1)
            expected_bps = pixels * fps * 4
            ratio = bitrate_bps / max(expected_bps, 1)
            if ratio < 0.15:      # heavily compressed relative to resolution
                score += 0.35
            elif ratio < 0.30:
                score += 0.15
        except (ValueError, ZeroDivisionError):
            pass

    # ── I-frame spacing regularity ───────────────────────────────────────────
    if packets:
        i_frame_positions = [
            i for i, p in enumerate(packets)
            if p.get("flags", "") == "K_"  # keyframe flag
        ]
        if len(i_frame_positions) > 2:
            gaps = [
                i_frame_positions[j + 1] - i_frame_positions[j]
                for j in range(len(i_frame_positions) - 1)
            ]
            mean_gap = sum(gaps) / len(gaps)
            # Perfect regularity (std/mean → 0) is a sign of re-encoding tool.
            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            cv = (variance ** 0.5) / max(mean_gap, 1)   # coefficient of variation
            if cv < 0.05:       # almost perfectly regular → suspicious
                score += 0.35
            elif cv < 0.15:
                score += 0.15

    return round(float(min(score, 1.0)), 4)


# ── Heuristic fallback (no FFprobe) ──────────────────────────────────────────

def _heuristic_analysis(path: Path) -> float:
    """File-level heuristic when FFprobe is not installed."""
    file_size = path.stat().st_size

    # Very small files relative to expected video content are suspicious.
    if file_size < 100 * 1024:      # < 100 KB — impossibly small for real video
        return 0.45
    if file_size < 500 * 1024:      # < 500 KB
        return 0.25

    return 0.10   # baseline: no strong signal without bitstream data
