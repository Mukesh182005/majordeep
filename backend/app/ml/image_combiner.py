"""Learned combination of the image scene detectors (replaces the hand-set log-odds weights).

A logistic regression on each detector's log-odds, fitted on held-out images in upload-like
versions (original, WhatsApp-style, screenshot, small) by ``ml/training/fit_image_combiner.py``
(evaluation/IMAGE-COMBINER-01). The file stores the raw coefficients and the two cut-offs chosen on
the tuning split (``z_authentic``, ``z_manipulated``, in log-odds); ``combine`` maps them onto whatever
verdict band is configured (``settings.fake_threshold`` +/- ``settings.uncertain_band``), so
``classify`` applies exactly the measured cut-offs.

``combine`` returns ``None`` when the file is missing or a detector it needs did not score; the
caller then falls back to the hand-set weights.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.config import settings

EPS = 1e-4


def combiner_path() -> Path:
    return Path(settings.checkpoint_dir) / "image_combiner.json"


@lru_cache(maxsize=1)
def _load(path: str, mtime: float) -> dict | None:  # mtime: reload when the file changes
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_combiner() -> dict | None:
    if not settings.image_combiner_enabled:
        return None
    p = combiner_path()
    return _load(str(p), p.stat().st_mtime) if p.exists() else None


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def _score_for(name: str, model_scores: dict[str, float]) -> float | None:
    """The score of detector ``name``; a local checkpoint matches by the end of its path."""
    for key, p in model_scores.items():
        if key == name or key.replace("\\", "/").endswith("/" + name):
            return p
    return None


def combine(model_scores: dict[str, float]) -> float | None:
    """P(AI) on the verdict scale, or ``None`` if the combiner cannot be applied."""
    c = get_combiner()
    if c is None:
        return None
    z = c["intercept"]
    for name, w in zip(c["models"], c["coef"]):
        s = _score_for(name, model_scores)
        if s is None:
            return None
        z += w * _logit(s)
    low = settings.fake_threshold - settings.uncertain_band
    high = settings.fake_threshold + settings.uncertain_band
    lo, hi = math.log(low / (1 - low)), math.log(high / (1 - high))
    z = lo + (z - c["z_authentic"]) * (hi - lo) / (c["z_manipulated"] - c["z_authentic"])
    return 1.0 / (1.0 + math.exp(-z))
