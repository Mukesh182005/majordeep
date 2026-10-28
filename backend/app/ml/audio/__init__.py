"""Audio analysis suite: eight stages run in order.

  Stage 1: File hashes
  Stage 2: Container parsing (format, codec, trailing bytes)
  Stage 3: Signal descriptors (time, frequency, cepstral, loudness)
  Stage 4: Glottal-flow and propagation heuristics
  Stage 5: Speech rate and coarticulation heuristics
  Stage 6: Model stage: the ASVspoof 2019 LA LCNN (``audio_model_source="lcnn_asvspoof"``)
           or, in ``legacy`` mode, hand-set rules only (heuristic, unvalidated)
  Stage 7: Mains-hum (ENF) and room-acoustics heuristics
  Stage 8: Splice timeline, provenance checks, and the risk/verdict rule

Only the LCNN is a trained model. Every other stage is a heuristic whose
discrimination has not been shown (paper_results/audio_heuristics_dev/).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
import numpy as np

from app.config import settings
from app.ml.audio.vault import create_evidence_record
from app.ml.audio.file_dna import analyze_audio_dna
from app.ml.audio.signal_intelligence import extract_signal_intelligence
from app.ml.audio.glottal_physiological import analyze_glottal_and_physics
from app.ml.audio.speech_semantics import analyze_speech_and_semantics
from app.ml.audio.signal_lab import generate_signal_lab_plates
from app.ml.audio.models_arch import score_audio_heuristics
from app.ml.audio.splicing_timeline import analyze_splicing_and_timeline
from app.ml.audio.enf_environment import analyze_environmental_and_enf
from app.ml.audio.security_provenance import analyze_security_and_provenance
from app.ml.audio.evidence_fusion import compute_evidence_fusion_and_risk
from app.ml.audio.xai_interpretability import generate_audio_xai_explanations

logger = logging.getLogger(__name__)


TRAINED_MODEL_SOURCES = ("lcnn_asvspoof", "pellav2")


def _pellav2_stage(
    waveform: np.ndarray,
    sample_rate: int,
    models_output: dict[str, Any],
    verdict_config: dict[str, Any] | None,
    findings: list[str],
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    """Score with pellav2; it takes over the model stage only when AUDIO_PELLAV2_IN_VERDICT is set.

    If pellav2 is meant to decide but cannot (no weights, no frozen thresholds),
    the stage is left as it was and a finding says so.
    """
    from app.ml.audio.pellav2 import MODEL_LABEL, load_pellav2_verdict_config, score_clip

    try:
        pellav2 = score_clip(waveform, sample_rate, settings.audio_pellav2_max_windows)
    except Exception as exc:
        logger.error("pellav2 scoring failed: %s", exc)
        pellav2 = None
    if pellav2 is None:
        return models_output, verdict_config, findings + [f"{MODEL_LABEL} unavailable for this clip; not used."]

    models_output = {**models_output, "pellav2": pellav2}
    summary = f"{MODEL_LABEL}: fake probability {pellav2['prob'] * 100:.1f}% (mean of {pellav2['n_windows']} 4 s window(s))"
    if not settings.audio_pellav2_in_verdict:
        return models_output, verdict_config, findings + [summary + "; unvalidated here, not in the verdict."]
    try:
        pellav2_config = load_pellav2_verdict_config(pellav2["metadata"].get("weights_sha256"))
    except Exception as exc:
        logger.error("pellav2 cannot decide the verdict: %s", exc)
        return models_output, verdict_config, findings + [summary + f"; not in the verdict ({exc})."]

    lcnn = models_output.get("lcnn_asvspoof")
    models_output.update(
        fused_ai_probability=pellav2["prob"],
        model_stage_source="pellav2",
        model_stage_label=f"{MODEL_LABEL}, pretrained by its authors",
    )
    findings = [summary + "; decides the verdict.", *(
        [f"ASVspoof 2019 LA LCNN {lcnn['probability'] * 100:.1f}% shown as context (no weight)."] if lcnn else []
    ), *[f for f in findings if f.startswith("Hand-set rule")]]
    return models_output, pellav2_config, findings


def _verdict_model(models_output: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    source = models_output.get("model_stage_source")
    if source not in TRAINED_MODEL_SOURCES:
        return None, None
    return source, models_output.get(source)


def lcnn_window_segments(models_output: dict[str, Any], verdict_config: dict[str, Any] | None) -> list[dict[str, Any]]:
    """The verdict model's per-window probabilities as timeline segments (empty in legacy mode).

    Same keys as the splice-timeline segments, so the plates, the report and
    the UI draw them unchanged. Status uses the frozen verdict thresholds; the
    verdict itself uses the mean over windows, not any single window.
    """
    source, model = _verdict_model(models_output)
    if not model or verdict_config is None:
        return []
    low, high = float(verdict_config["authentic_below"]), float(verdict_config["flagged_at_or_above"])
    segments = []
    for window in model.get("windows", []):
        p = float(window["probability"])
        status = "FLAGGED" if p >= high else ("AUTHENTIC" if p < low else "INCONCLUSIVE")
        segments.append({
            "segment_index": window["index"],
            "start_s": window["start_s"],
            "end_s": window["end_s"],
            "fake_probability": round(p, 4),
            "status": status,
            "source": source,
            "reasons": [],
        })
    return segments


def run_comprehensive_audio_forensics(
    file_path: str | Path,
    waveform: np.ndarray,
    sample_rate: int,
    evidence_dir: str | Path,
    job_id: str,
    case_reference: str | None = None,
    model_waveform: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run the eight audio stages and collect their outputs.

    ``model_waveform`` is the waveform before peak normalisation, used by the
    ASVspoof LCNN when ``settings.audio_model_source == "lcnn_asvspoof"``.
    """
    file_path = Path(file_path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    pipeline_modules: list[dict[str, Any]] = []

    # ------------------------------------------------------------- STAGE 1: File hashes
    t0 = time.perf_counter()
    vault_record = create_evidence_record(file_path, case_reference=case_reference)
    t1 = time.perf_counter()
    pipeline_modules.append({
        "stage": 1,
        "name": "File Hashes",
        "category": "File Integrity",
        "status": "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Evidence ID: {vault_record['evidence_id']} | SHA-256: {vault_record['hashes']['sha256'][:16]}...",
        "findings": ["SHA-256, SHA-512, MD5 and SHA-1 of the uploaded file recorded."],
    })

    # ------------------------------------------------------------- STAGE 2: Audio File DNA & Container
    t0 = time.perf_counter()
    file_dna = analyze_audio_dna(file_path, raw_audio_data=waveform, sample_rate=sample_rate)
    t1 = time.perf_counter()
    dna_status = "ANOMALY_DETECTED" if file_dna.get("trailing_data_detected") or not file_dna.get("container_structure_valid") else "PASSED"
    pipeline_modules.append({
        "stage": 2,
        "name": "Audio File DNA & Container Forensics",
        "category": "Container Cybersecurity",
        "status": dna_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"{file_dna.get('container_format')} | Codec: {file_dna.get('codec')} | Rate: {file_dna.get('sample_rate_hz') or sample_rate} Hz",
        "findings": file_dna.get("security_flags") or ["Container structural integrity intact.", f"Inferred {len(file_dna.get('inferred_transcoding_history', []))} processing stage(s)."],
    })

    # ------------------------------------------------------------- STAGE 3: Deterministic Signal Intelligence
    t0 = time.perf_counter()
    signal_intel = extract_signal_intelligence(waveform, sample_rate)
    t1 = time.perf_counter()
    pipeline_modules.append({
        "stage": 3,
        "name": "Signal Intelligence & Acoustic Telemetry",
        "category": "Signal Processing",
        "status": "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Quality Score: {signal_intel.get('quality_score')}/100 | SNR: {signal_intel.get('dynamics_and_loudness', {}).get('estimated_snr_db')} dB | LUFS: {signal_intel.get('dynamics_and_loudness', {}).get('integrated_loudness_lufs')}",
        "findings": [
            f"Extracted {signal_intel.get('descriptor_count', 120)}+ time, frequency, and multi-scale cepstral descriptors.",
            f"LFCC linear filterbank calculated across 0-{sample_rate//2} Hz Nyquist range.",
            f"Clipping severity: {signal_intel.get('clipping_analysis', {}).get('severity')}.",
        ],
    })

    # ------------------------------------------------------------- STAGE 4: Physiological Glottal Flow & Physics
    t0 = time.perf_counter()
    glottal_physics = analyze_glottal_and_physics(waveform, sample_rate)
    t1 = time.perf_counter()
    phys_anomaly = glottal_physics.get("composite_physiological_anomaly_score", 0.0)
    phys_status = "ANOMALY_DETECTED" if phys_anomaly > 0.60 else "PASSED"
    pipeline_modules.append({
        "stage": 4,
        "name": "Physiological Glottal Flow & VoiceRadar Physics",
        "category": "Physical Forensics",
        "status": phys_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Glottal Qo: {glottal_physics.get('glottal_flow', {}).get('open_quotient')} | Closing: {glottal_physics.get('glottal_flow', {}).get('closing_quotient')} | Doppler Anomaly: {glottal_physics.get('physical_propagation', {}).get('doppler_anomaly_score')}",
        "findings": [
            glottal_physics.get("physiological_verdict", "Biological tract adherence evaluated."),
            f"Vocal turbulence index: {glottal_physics.get('glottal_flow', {}).get('biological_turbulence_index')}.",
        ],
    })

    # ------------------------------------------------------------- STAGE 5: Speech Semantics & Phonetics
    t0 = time.perf_counter()
    speech_semantics = analyze_speech_and_semantics(waveform, sample_rate)
    t1 = time.perf_counter()
    pipeline_modules.append({
        "stage": 5,
        "name": "Content & Phonemic Coarticulation",
        "category": "Linguistic Forensics",
        "status": "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"{speech_semantics.get('speaking_rate_wpm')} WPM | Words: ~{speech_semantics.get('estimated_words_count')} | Speech: {speech_semantics.get('speech_ratio_percent')}%",
        "findings": [
            speech_semantics.get("content_summary", "Speech distribution measured."),
            f"Syllable rhythm variation: {speech_semantics.get('syllable_rhythm_std_ms')} ms (Rigid prosody: {'YES' if speech_semantics.get('rigid_synthetic_prosody_detected') else 'NO'}).",
        ],
    })

    # ------------------------------------------------------------- STAGE 6: Model stage
    t0 = time.perf_counter()
    models_output: dict[str, Any] = score_audio_heuristics(signal_intel, glottal_physics, file_dna)
    model_findings = [
        "No trained model in this mode: hand-set rules over glottal, voice-quality and cepstral "
        "descriptors (heuristic, unvalidated)."
    ]
    verdict_config = None
    if settings.audio_model_source == "lcnn_asvspoof":
        from app.ml.audio.lcnn_asvspoof import load_verdict_config, score_lcnn_asvspoof

        verdict_config = load_verdict_config()

        lcnn = score_lcnn_asvspoof(
            model_waveform if model_waveform is not None else waveform,
            sample_rate,
            peak_normalised=model_waveform is None,
        )
        models_output = {
            **models_output,
            "legacy_fused_ai_probability": models_output.get("fused_ai_probability"),
            "fused_ai_probability": lcnn["probability"],
            "model_stage_source": "lcnn_asvspoof",
            "model_stage_label": "trained model (ASVspoof 2019 LA)",
            "lcnn_asvspoof": lcnn,
        }
        model_findings = [
            f"ASVspoof 2019 LA LCNN ({lcnn['model_version']}), {lcnn['n_windows']} window(s), "
            f"calibrated spoof probability {lcnn['probability'] * 100:.1f}%.",
            f"Hand-set rule score {models_output['legacy_fused_ai_probability'] * 100:.1f}% shown as context only "
            "(heuristic, unvalidated).",
        ]
    if settings.audio_pellav2_enabled:
        models_output, verdict_config, model_findings = _pellav2_stage(
            model_waveform if model_waveform is not None else waveform, sample_rate,
            models_output, verdict_config, model_findings,
        )
    t1 = time.perf_counter()
    ai_prob = models_output.get("fused_ai_probability", 0.1)
    pipeline_modules.append({
        "stage": 6,
        "name": "Model Stage",
        "category": "Machine Learning" if models_output.get("model_stage_source") in TRAINED_MODEL_SOURCES else "Heuristic (unvalidated)",
        "status": "ANOMALY_DETECTED" if ai_prob > 0.65 else "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Spoof probability: {ai_prob * 100:.1f}% ({models_output.get('model_stage_label')}) | "
        + (
            f"pellav2 (w2v-BERT 2.0): {models_output['pellav2']['prob'] * 100:.1f}% over "
            f"{models_output['pellav2']['n_windows']} window(s) (unvalidated, not in verdict) | "
            if models_output.get("pellav2") and models_output.get("model_stage_source") != "pellav2" else ""
        )
        + f"Domain (heuristic): {models_output.get('audio_domain')}",
        "findings": model_findings,
    })

    # ------------------------------------------------------------- STAGE 7: Environmental & Grid Forensics (ENF)
    t0 = time.perf_counter()
    enf_environment = analyze_environmental_and_enf(waveform, sample_rate)
    t1 = time.perf_counter()
    enf_status = "ANOMALY_DETECTED" if enf_environment.get("environmental_splicing_confirmed") else "PASSED"
    pipeline_modules.append({
        "stage": 7,
        "name": "Environmental & ENF Grid Forensics",
        "category": "Sensor Forensics",
        "status": enf_status,
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Grid: {enf_environment.get('enf_forensics', {}).get('nominal_grid_frequency_hz')} Hz | Phase Slips: {enf_environment.get('enf_forensics', {}).get('phase_discontinuity_count')} | Room RT60: {enf_environment.get('room_acoustics', {}).get('mean_reverberation_time_rt60_s')}s",
        "findings": [
            enf_environment.get("enf_forensics", {}).get("status", "ENF continuity analyzed."),
            f"Microphone consistency: {enf_environment.get('microphone_hardware', {}).get('transducer_signature')}.",
        ],
    })

    # ------------------------------------------------------------- STAGE 8: Splicing, Cybersecurity & Evidence Fusion
    t0 = time.perf_counter()
    splicing_timeline = analyze_splicing_and_timeline(waveform, sample_rate)
    security_provenance = analyze_security_and_provenance(file_path, waveform, sample_rate, acoustic_ai_score=ai_prob)
    fusion_decision = compute_evidence_fusion_and_risk(
        vault_record, file_dna, signal_intel, glottal_physics,
        models_output, splicing_timeline, enf_environment, security_provenance,
        speech_semantics, verdict_config=verdict_config,
    )
    t1 = time.perf_counter()
    pipeline_modules.append({
        "stage": 8,
        "name": "Risk and Verdict",
        "category": "Decision Rule",
        "status": "ANOMALY_DETECTED" if fusion_decision.get("final_verdict") in ("AI_GENERATED", "MANIPULATED") else "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Verdict: {fusion_decision.get('final_verdict')} | AI Risk: {(fusion_decision.get('generative_ai_risk_score') or 0.0)*100:.1f}% | Tamper Risk: {(fusion_decision.get('structural_tampering_risk_score') or 0.0)*100:.1f}%",
        "findings": fusion_decision.get("flagged_signals") or ["No signal reached its flag threshold."],
    })

    # ------------------------------------------------------------- Visual Scalograms & XAI Plates
    model_windows = lcnn_window_segments(models_output, verdict_config)
    visual_files = generate_signal_lab_plates(
        waveform, sample_rate, evidence_dir, job_id,
        segment_scores=model_windows if model_windows else splicing_timeline.get("segments"),
    )
    xai_files = generate_audio_xai_explanations(
        waveform, sample_rate, evidence_dir, job_id, ai_prob=fusion_decision.get("calibrated_fake_probability", 0.5)
    )

    return {
        "model_windows": model_windows,
        "pipeline_modules": pipeline_modules,
        "vault_record": vault_record,
        "file_dna": file_dna,
        "signal_intel": signal_intel,
        "glottal_physics": glottal_physics,
        "speech_semantics": speech_semantics,
        "models_output": models_output,
        "splicing_timeline": splicing_timeline,
        "enf_environment": enf_environment,
        "security_provenance": security_provenance,
        "fusion_decision": fusion_decision,
        "visual_evidence": {**visual_files, **xai_files},
    }
