"""Extra image scorers for comparison: each returns P(AI-generated) for a file.

* ``umm_maybe``: the old detector C, ``umm-maybe/AI-image-detector``, read the
  same way as the scene detectors (1 - P(real class)).
* ``univfd``: UnivFD (Ojha et al., CVPR 2023), official code and weights.
* ``cnndetection``: CNNDetection (Wang et al., CVPR 2020), official code and weights.

Baselines see the original file with their own preprocessing; they are not
given the system's border cropping. The official code and weights live outside
this repository (``$DEEPSENTINEL_DATA/baselines``) and are never committed.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path


def baselines_root() -> Path:
    data = os.environ.get("DEEPSENTINEL_DATA")
    if not data:
        raise RuntimeError("Set DEEPSENTINEL_DATA; baseline code and weights live in $DEEPSENTINEL_DATA/baselines")
    return Path(data) / "baselines"


def _hf_scorer(model_id: str) -> Callable[[Path], float]:
    from app.ml.base import resolve_device
    from app.ml.image_pipeline import _REAL_CLASS_NAMES
    from PIL import Image
    from transformers import pipeline

    pipe = pipeline("image-classification", model=model_id, device=resolve_device())
    labels = {str(v) for v in (getattr(pipe.model.config, "id2label", None) or {}).values()}
    real = {label for label in labels if label.lower() in _REAL_CLASS_NAMES}
    if not real:
        raise RuntimeError(f"{model_id} has no recognisable 'real' class in {labels}")

    def score(path: Path) -> float:
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        predictions = pipe(image, top_k=None)
        p_real = sum(float(p["score"]) for p in predictions if str(p["label"]) in real)
        return min(max(1.0 - p_real, 0.0), 1.0)

    return score


def load_scorer(name: str) -> Callable[[Path], float]:
    if name == "umm_maybe":
        return _hf_scorer("umm-maybe/AI-image-detector")
    if name == "univfd":
        from ml.evaluation.baselines.univfd import load_univfd

        return load_univfd(baselines_root())
    if name == "cnndetection":
        from ml.evaluation.baselines.cnndetection import load_cnndetection

        return load_cnndetection(baselines_root())
    raise ValueError(f"Unknown scorer '{name}'")
