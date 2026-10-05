"""Shared types and helpers for the detection pipelines."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.models import Verdict


class DetectorUnavailableError(RuntimeError):
    """Raised when a pipeline's dependencies (torch, ffmpeg, ...) are missing."""


@dataclass
class AnalysisResult:
    """Normalised output of any detector, ready to persist on a Job."""

    fake_probability: float
    model_name: str
    model_version: str
    weights_status: str  # "trained" | "untrained-backbone"
    evidence: dict[str, Any] = field(default_factory=dict)
    # Set when the evidence cannot support the verdict the probability alone
    # would give: a screenshot the detectors did not flag is not thereby
    # "authentic", it is unverifiable.
    verdict_override: Verdict | None = None

    @property
    def verdict(self) -> Verdict:
        if self.verdict_override is not None:
            return self.verdict_override
        return classify(self.fake_probability)

    @property
    def confidence(self) -> float:
        """Distance from the undecided midpoint, expressed as 0..1.

        A probability of 0.5 carries no information (confidence 0.0); 0.0 or 1.0
        is maximally confident. This is what the UI shows, so a borderline score
        never renders as a confident verdict — and an INCONCLUSIVE override never
        shows more confidence than a probability inside the uncertain band could.
        """
        confidence = abs(self.fake_probability - 0.5) * 2
        if self.verdict_override is Verdict.INCONCLUSIVE:
            confidence = min(confidence, settings.uncertain_band * 2)
        return round(confidence, 4)


def json_safe(value: Any) -> Any:
    """Copy of ``value`` that strict JSON accepts: NaN/inf become ``None``, numpy scalars become Python.

    Evidence is persisted as JSON and parsed by browsers, which reject the
    ``NaN`` literal Python's encoder emits by default.
    """
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item") and callable(value.item) and getattr(value, "ndim", None) == 0:
        value = value.item()  # numpy scalar
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def classify(fake_probability: float) -> Verdict:
    """Map a probability to a three-way verdict with an explicit uncertain band.

    Reporting 'inconclusive' near the threshold is deliberate: deepfake
    detectors are not certain, and a two-way label would overstate the result.
    """
    low = settings.fake_threshold - settings.uncertain_band
    high = settings.fake_threshold + settings.uncertain_band
    if fake_probability >= high:
        return Verdict.MANIPULATED
    if fake_probability <= low:
        return Verdict.AUTHENTIC
    return Verdict.INCONCLUSIVE


def torch_available() -> bool:
    """True when PyTorch can be imported in this process."""
    try:
        import torch  # noqa: F401
    except Exception:
        return False
    return True


def resolve_device(preferred: str | None = None) -> str:
    """Pick a torch device, falling back to CPU if CUDA is not available."""
    preferred = preferred or settings.device
    if not preferred.startswith("cuda"):
        return preferred

    import torch
    if not torch.cuda.is_available():
        import logging
        logging.getLogger(__name__).warning(
            "CUDA was requested but torch.cuda.is_available() is False. Falling back to CPU."
        )
        return "cpu"
    return preferred
