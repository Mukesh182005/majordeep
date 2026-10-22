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
    if settings.audio_model_source == "lcnn_asvspoof":
        from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof

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
    t1 = time.perf_counter()
    ai_prob = models_output.get("fused_ai_probability", 0.1)
    pipeline_modules.append({
        "stage": 6,
        "name": "Model Stage",
        "category": "Machine Learning" if models_output.get("model_stage_source") == "lcnn_asvspoof" else "Heuristic (unvalidated)",
        "status": "ANOMALY_DETECTED" if ai_prob > 0.65 else "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Spoof probability: {ai_prob * 100:.1f}% ({models_output.get('model_stage_label')}) | "
        f"Domain (heuristic): {models_output.get('audio_domain')}",
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
        speech_semantics
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
    visual_files = generate_signal_lab_plates(
        waveform, sample_rate, evidence_dir, job_id, segment_scores=splicing_timeline.get("segments")
    )
    xai_files = generate_audio_xai_explanations(
        waveform, sample_rate, evidence_dir, job_id, ai_prob=fusion_decision.get("calibrated_fake_probability", 0.5)
    )

    return {
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
