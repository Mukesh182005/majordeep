"""Dispatch to the correct detector for a media type."""

from __future__ import annotations

from pathlib import Path

from app.ml.base import AnalysisResult
from app.models import MediaType


def _inject_mopci(result: AnalysisResult, media_type_str: str) -> AnalysisResult:
    """Enrich result.evidence with MOPCI intelligence payload."""
    try:
        from app.ml.mopci.mopci_engine import generate_mopci_data
        is_fake = (result.fake_probability or 0.0) >= 0.5
        file_dna = result.evidence.get("file_dna", {}) if result.evidence else {}
        mopci = generate_mopci_data(
            media_type=media_type_str,
            is_fake=is_fake,
            fake_prob=result.fake_probability or 0.0,
            file_dna=file_dna,
        )
        if result.evidence is None:
            result.evidence = {}  # type: ignore
        result.evidence["mopci"] = mopci
    except Exception:
        pass  # Never let MOPCI enrichment crash the pipeline
    return result


def analyze(
    media_type: MediaType, path: str | Path, evidence_dir: str | Path, job_id: str
) -> AnalysisResult:
    """Run the pipeline matching ``media_type``."""
    if media_type is MediaType.IMAGE:
        from app.ml.image_pipeline import analyze_image
        result = analyze_image(path, evidence_dir, job_id)
        return _inject_mopci(result, "image")

    if media_type is MediaType.AUDIO:
        from app.ml.audio_pipeline import analyze_audio
        result = analyze_audio(path, evidence_dir, job_id)
        return _inject_mopci(result, "audio")

    if media_type is MediaType.VIDEO:
        from app.ml.video_pipeline import analyze_video
        result = analyze_video(path, evidence_dir, job_id)
        return _inject_mopci(result, "video")

    raise ValueError(f"Unsupported media type: {media_type}")

