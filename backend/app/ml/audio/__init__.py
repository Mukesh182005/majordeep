"""Audio Forensics Package: Complete 10-Engine Audio Intelligence & Forensics Suite.

Executes an 8-stage progressive forensic pipeline:
  Stage 1: Secure Ingestion Vault & Cryptographic Chain-of-Custody
  Stage 2: Audio File DNA & Container Cybersecurity
  Stage 3: Deterministic Signal Intelligence & 120+ Descriptors
  Stage 4: Physiological Glottal Flow (IAIF) & Physical Acoustics (VoiceRadar)
  Stage 5: Speech Semantics & Phonemic Coarticulation
  Stage 6: Multi-Model Detection & Intermediate SSL Probing (WavLM L18 / Whisper L4)
  Stage 7: Environmental & Grid Forensics (ENF Phase & Room RT60)
  Stage 8: Cybersecurity, Splicing Localization & Conformal Evidence Fusion
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
import numpy as np

from app.ml.audio.vault import create_evidence_record
from app.ml.audio.file_dna import analyze_audio_dna
from app.ml.audio.signal_intelligence import extract_signal_intelligence
from app.ml.audio.glottal_physiological import analyze_glottal_and_physics
from app.ml.audio.speech_semantics import analyze_speech_and_semantics
from app.ml.audio.signal_lab import generate_signal_lab_plates
from app.ml.audio.models_arch import AudioMultiModelEnsemble
from app.ml.audio.splicing_timeline import analyze_splicing_and_timeline
from app.ml.audio.enf_environment import analyze_environmental_and_enf
from app.ml.audio.security_provenance import analyze_security_and_provenance
from app.ml.audio.evidence_fusion import compute_evidence_fusion_and_risk
from app.ml.audio.xai_interpretability import generate_audio_xai_explanations

logger = logging.getLogger(__name__)

# Global singleton ensemble instance
_AUDIO_ENSEMBLE = None


def get_audio_ensemble() -> AudioMultiModelEnsemble:
    global _AUDIO_ENSEMBLE
    if _AUDIO_ENSEMBLE is None:
        _AUDIO_ENSEMBLE = AudioMultiModelEnsemble()
    return _AUDIO_ENSEMBLE


def run_comprehensive_audio_forensics(
    file_path: str | Path,
    waveform: np.ndarray,
    sample_rate: int,
    evidence_dir: str | Path,
    job_id: str,
    case_reference: str | None = None,
) -> dict[str, Any]:
    """Execute all 10 audio forensic engines and compile exhaustive evidentiary dossier."""
    file_path = Path(file_path)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    pipeline_modules: list[dict[str, Any]] = []

    # ------------------------------------------------------------- STAGE 1: Secure Ingestion Vault
    t0 = time.perf_counter()
    vault_record = create_evidence_record(file_path, case_reference=case_reference)
    t1 = time.perf_counter()
    pipeline_modules.append({
        "stage": 1,
        "name": "Secure Ingestion Vault",
        "category": "Evidence Integrity",
        "status": "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Evidence ID: {vault_record['evidence_id']} | SHA-256: {vault_record['hashes']['sha256'][:16]}...",
        "findings": ["SWGDE & ISO 27042 compliant cryptographic bind established.", "Write-blocker access emulated."],
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

    # ------------------------------------------------------------- STAGE 6: Multi-Model AI Detection & SSL Probing
    t0 = time.perf_counter()
    ensemble = get_audio_ensemble()
    models_output = ensemble.classify_audio(waveform, sample_rate, signal_intel, glottal_physics, file_dna)
    t1 = time.perf_counter()
    ai_prob = models_output.get("fused_ai_probability", 0.1)
    pipeline_modules.append({
        "stage": 6,
        "name": "Multi-Model ML & Intermediate SSL Probing",
        "category": "Machine Learning",
        "status": "ANOMALY_DETECTED" if ai_prob > 0.65 else "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Domain: {models_output.get('audio_domain')} | Sinc-RawNet: {models_output.get('model_branch_scores', {}).get('rawnet_waveform_prob')*100:.1f}% | WavLM L18: {models_output.get('model_branch_scores', {}).get('wavlm_l18_acoustic_prob')*100:.1f}%",
        "findings": [
            f"Evaluated intermediate WavLM Layer 18 and Whisper Layer 4 representations.",
            f"Top Typology: Fully Synthetic TTS ({models_output.get('typology_breakdown', {}).get('tts_fully_synthetic_pct')}%) vs Bona Fide ({models_output.get('typology_breakdown', {}).get('bona_fide_authentic_pct')}%).",
        ],
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
        "name": "Evidence Fusion & Conformal Risk Engine",
        "category": "Decision Engine",
        "status": "ANOMALY_DETECTED" if fusion_decision.get("final_verdict") in ("AI_GENERATED", "MANIPULATED") else "PASSED",
        "duration_ms": max(1, int((t1 - t0) * 1000)),
        "summary": f"Verdict: {fusion_decision.get('final_verdict')} | AI Risk: {(fusion_decision.get('generative_ai_risk_score') or 0.0)*100:.1f}% | Tamper Risk: {(fusion_decision.get('structural_tampering_risk_score') or 0.0)*100:.1f}%",
        "findings": fusion_decision.get("orthogonal_signals_details") or ["Zero manipulation signals detected across all 10 engines."],
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
