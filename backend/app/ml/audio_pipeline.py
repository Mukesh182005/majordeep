"""Audio analysis: runs the audio suite (app/ml/audio) and packages its evidence.

The probability comes from the suite's risk rule (app/ml/audio/evidence_fusion.py).
Its model stage is the ASVspoof 2019 LA LCNN when ``audio_model_source`` is
"lcnn_asvspoof"; in "legacy" mode no trained model runs at all and the result
is marked experimental.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import numpy as np

from app.config import settings
from app.ml.base import AnalysisResult
from app.ml.preprocessing import load_audio, normalize_waveform
from app.ml.registry import TRAINED, UNTRAINED
from app.ml.audio import run_comprehensive_audio_forensics

logger = logging.getLogger(__name__)

EXPERIMENTAL_REASON = (
    "No trained audio model is in use (AUDIO_MODEL_SOURCE=legacy): the score comes from hand-set "
    "rules over signal descriptors that have not been validated on labelled speech."
)
LCNN_SCOPE_NOTE = (
    "Model stage: LCNN trained and evaluated on ASVspoof 2019 LA (studio-quality English read speech). "
    "It has not been evaluated on real-world recordings, phone calls or other languages."
)


def analyze_audio(path: str | Path, evidence_dir: str | Path, job_id: str) -> AnalysisResult:
    """Run the audio suite on one file and return its probability and evidence."""
    path = Path(path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ 1. Load Audio
    waveform, sample_rate = load_audio(path, settings.audio_sample_rate)
    normalized = normalize_waveform(waveform)
    duration_s = len(normalized) / sample_rate

    # ------------------------------------------------------------------ 2. Run the audio suite
    forensic_results = run_comprehensive_audio_forensics(
        model_waveform=waveform,
        file_path=path,
        waveform=normalized,
        sample_rate=sample_rate,
        evidence_dir=evidence_dir,
        job_id=job_id,
    )

    fusion = forensic_results["fusion_decision"]
    final_fake_prob = fusion["calibrated_fake_probability"]
    splicing = forensic_results["splicing_timeline"]
    visuals = forensic_results["visual_evidence"]
    file_dna = forensic_results["file_dna"]
    signal_intel = forensic_results["signal_intel"]
    glottal = forensic_results["glottal_physics"]
    enf = forensic_results["enf_environment"]
    provenance = forensic_results["security_provenance"]

    # ------------------------------------------------------------------ 3. Investigative Notes
    lcnn = forensic_results["models_output"].get("lcnn_asvspoof")
    experimental = lcnn is None
    notes: list[str] = [EXPERIMENTAL_REASON if experimental else LCNN_SCOPE_NOTE]

    if file_dna.get("trailing_data_detected"):
        notes.append(
            f"Container warning: {file_dna.get('trailing_bytes_count')} trailing bytes appended past audio EOF."
        )

    if enf.get("environmental_splicing_confirmed"):
        notes.append(
            f"Mains-hum (ENF) phase discontinuity of {enf.get('enf_forensics', {}).get('max_phase_slip_degrees')}° "
            "(heuristic, unvalidated): possible splice."
        )

    if glottal.get("composite_physiological_anomaly_score", 0.0) > 0.65:
        notes.append(
            "Glottal-flow anomaly score above 0.65 (heuristic, unvalidated)."
        )

    if splicing.get("splicing_detected"):
        notes.append(
            f"Splice timeline: {len(splicing.get('suspicious_intervals', []))} suspicious interval(s) "
            "(heuristic, unvalidated)."
        )

    if provenance.get("watermark_analysis", {}).get("overwriting_attack_suspected"):
        notes.append(
            "Watermark check reported a possible overwriting attack (heuristic, unvalidated)."
        )

    if duration_s < settings.audio_window_seconds:
        notes.append(
            f"Clip duration ({duration_s:.1f}s) is shorter than recommended baseline window ({settings.audio_window_seconds:.0f}s)."
        )

    # ------------------------------------------------------------------ 4. Evidence Payload
    overall_risk = int(final_fake_prob * 100)
    risk_tier = (
        "CRITICAL_RISK" if overall_risk >= 75
        else "HIGH_RISK" if overall_risk >= 55
        else "MODERATE_RISK" if overall_risk >= 35
        else "LOW_RISK"
    )

    evidence_payload: dict[str, Any] = {
        "media": "audio",
        "duration_seconds": round(duration_s, 3),
        "sample_rate": sample_rate,
        "notes": notes,
        "experimental": experimental,
        "experimental_reason": EXPERIMENTAL_REASON if experimental else None,

        # Visual evidence files
        "spectrogram_file": visuals.get("spectrogram_file"),
        "lfcc_scalogram_file": visuals.get("lfcc_scalogram_file"),
        "cqt_scalogram_file": visuals.get("cqt_scalogram_file"),
        "waveform_file": visuals.get("waveform_file"),
        "multi_resolution_plate_file": visuals.get("multi_resolution_plate_file"),
        "heatmap_file": visuals.get("gradcam_heatmap_file"),

        # Temporal timeline segments
        "segments_analysed": splicing.get("total_segments_analyzed", 0),
        "segment_scores": splicing.get("segments", []),
        "suspicious_intervals": splicing.get("suspicious_intervals", []),

        # Per-stage audit trail
        "pipeline_modules": forensic_results.get("pipeline_modules", []),

        # Full stage outputs
        "forensics": forensic_results,
        "file_dna": file_dna,
        "signal_intel": signal_intel,
        "glottal_physics": glottal,
        "speech_semantics": forensic_results["speech_semantics"],
        "models_output": forensic_results["models_output"],
        "splicing_timeline": splicing,
        "enf_environment": enf,
        "security_provenance": provenance,
        "fusion_decision": fusion,

        # Synthesis and tampering risk, and the rule that turned them into a verdict
        "risk_score": overall_risk,
        "risk_tier": risk_tier,
        "generative_ai_risk": fusion.get("generative_ai_risk_score"),
        "structural_tampering_risk": fusion.get("structural_tampering_risk_score"),
        "decision_set": fusion.get("decision_set"),
        "decision_rule": fusion.get("decision_rule"),
        "is_inconclusive": fusion.get("is_inconclusive"),
    }

    if lcnn:
        return AnalysisResult(
            fake_probability=round(final_fake_prob, 4),
            model_name="LCNN (LFCC), ASVspoof 2019 LA, with hand-set signal rules",
            model_version=lcnn["model_version"],
            weights_status=TRAINED,
            evidence=evidence_payload,
        )
    return AnalysisResult(
        fake_probability=round(final_fake_prob, 4),
        model_name="Hand-set audio rules (heuristic, unvalidated)",
        model_version="rules-no-trained-model",
        weights_status=UNTRAINED,
        evidence=evidence_payload,
    )
