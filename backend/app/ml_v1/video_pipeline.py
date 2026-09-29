"""Video deepfake detection — entry point.

Delegates to the modular pipeline in ``app.ml.video``.
The full 8-stage orchestration (frame sampling, face detection, spatial scoring,
temporal jitter, optical flow, compression DNA, Grad-CAM, fusion) lives there.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.ml.base import AnalysisResult
from app.ml.video import analyze_video as _analyze_video

logger = logging.getLogger(__name__)


def analyze_video(path: str | Path, evidence_dir: str | Path, job_id: str) -> AnalysisResult:
    """Score a video by delegating to the modular temporal pipeline."""
    logger.info("Routing video job %s to modular pipeline", job_id)
    return _analyze_video(path, evidence_dir, job_id)
