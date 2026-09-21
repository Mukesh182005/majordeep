"""Automated unit and integration test suite for the AudioSentinel 10-Engine Platform."""

import math
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from app.ml.audio.vault import compute_audio_vault_hashes, create_evidence_record
from app.ml.audio.file_dna import analyze_audio_dna
from app.ml.audio.signal_intelligence import extract_signal_intelligence
from app.ml.audio.glottal_physiological import analyze_glottal_and_physics
from app.ml.audio.speech_semantics import analyze_speech_and_semantics
from app.ml.audio.models_arch import AudioMultiModelEnsemble
from app.ml.audio.splicing_timeline import analyze_splicing_and_timeline
from app.ml.audio.enf_environment import analyze_environmental_and_enf
from app.ml.audio.security_provenance import analyze_security_and_provenance
from app.ml.audio.evidence_fusion import compute_evidence_fusion_and_risk
from app.ml.audio_pipeline import analyze_audio


@pytest.fixture
def sample_wav(tmp_path):
    """Create a temporary authentic-like synthetic voice test tone fixture."""
    sr = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Fundamental + harmonics
    audio = (
        0.50 * np.sin(2 * np.pi * 180 * t) +
        0.25 * np.sin(2 * np.pi * 360 * t) +
        0.12 * np.sin(2 * np.pi * 540 * t)
    ).astype(np.float32)
    
    file_path = tmp_path / "test_voice.wav"
    sf.write(file_path, audio, sr)
    return file_path, audio, sr


def test_vault_cryptographic_hashes(sample_wav):
    file_path, _, _ = sample_wav
    hashes = compute_audio_vault_hashes(file_path)
    assert len(hashes["sha256"]) == 64
    assert len(hashes["sha512"]) == 128
    assert len(hashes["md5"]) == 32
    assert len(hashes["sha1"]) == 40

    record = create_evidence_record(file_path)
    assert record["evidence_id"].startswith("EVID-")
    assert record["chain_of_custody_status"] == "PRESERVED_IMMUTABLE"
    assert record["write_blocker_emulated"] is True


def test_file_dna_and_trailing_data(sample_wav):
    file_path, audio, sr = sample_wav
    dna = analyze_audio_dna(file_path, raw_audio_data=audio, sample_rate=sr)
    assert dna["container_format"] == "RIFF/WAV"
    assert dna["trailing_data_detected"] is False
    assert len(dna["inferred_transcoding_history"]) >= 2

    # Inject trailing bytes and verify detection
    corrupted_path = file_path.parent / "corrupted_trailing.wav"
    original_bytes = file_path.read_bytes()
    corrupted_bytes = original_bytes + b"MALICIOUS_STEGO_PAYLOAD_12345678"
    corrupted_path.write_bytes(corrupted_bytes)

    dna_corrupted = analyze_audio_dna(corrupted_path, raw_audio_data=audio, sample_rate=sr)
    assert dna_corrupted["trailing_data_detected"] is True
    assert dna_corrupted["trailing_bytes_count"] == len(b"MALICIOUS_STEGO_PAYLOAD_12345678")


def test_signal_intelligence_120_descriptors(sample_wav):
    _, audio, sr = sample_wav
    intel = extract_signal_intelligence(audio, sr)
    assert intel["descriptor_count"] >= 120
    assert "time_domain" in intel
    assert "frequency_domain" in intel
    assert "cepstral_analysis" in intel
    assert "voice_quality" in intel
    assert len(intel["cepstral_analysis"]["lfcc_coefficients_1_20"]) == 20
    assert len(intel["cepstral_analysis"]["cqcc_coefficients_1_16"]) == 16
    assert 0 <= intel["quality_score"] <= 100


def test_glottal_iaif_and_voiceradar(sample_wav):
    _, audio, sr = sample_wav
    phys = analyze_glottal_and_physics(audio, sr)
    assert "glottal_flow" in phys
    assert "physical_propagation" in phys
    assert 0.0 <= phys["composite_physiological_anomaly_score"] <= 1.0
    glottal = phys["glottal_flow"]
    assert 0.0 <= glottal["open_quotient"] <= 1.0
    assert 0.0 <= glottal["closing_quotient"] <= 1.0


def test_enf_environment_and_phase_continuity(sample_wav):
    _, audio, sr = sample_wav
    enf = analyze_environmental_and_enf(audio, sr)
    assert "enf_forensics" in enf
    assert "room_acoustics" in enf
    assert "microphone_hardware" in enf
    assert enf["enf_forensics"]["nominal_grid_frequency_hz"] in (50.0, 60.0)


def test_security_provenance_and_steganography(sample_wav):
    file_path, audio, sr = sample_wav
    sec = analyze_security_and_provenance(file_path, audio, sr)
    assert "provenance_c2pa" in sec
    assert "watermark_analysis" in sec
    assert "steganography_forensics" in sec
    assert sec["watermark_analysis"]["anti_shortcut_status"] == "DEFENDED_WATERMARK_AGNOSTIC"


def test_splicing_timeline_and_f1_dynamics(sample_wav):
    _, audio, sr = sample_wav
    timeline = analyze_splicing_and_timeline(audio, sr, window_seconds=1.0, hop_seconds=0.5)
    assert timeline["total_segments_analyzed"] >= 3
    assert "first_order_f1_spikes_count" in timeline


def test_speech_semantics_and_wpm(sample_wav):
    _, audio, sr = sample_wav
    semantics = analyze_speech_and_semantics(audio, sr)
    assert semantics["speaking_rate_wpm"] >= 0
    assert 0 <= semantics["speech_ratio_percent"] <= 100


def test_multi_model_ensemble(sample_wav):
    file_path, audio, sr = sample_wav
    dna = analyze_audio_dna(file_path, raw_audio_data=audio, sample_rate=sr)
    intel = extract_signal_intelligence(audio, sr)
    phys = analyze_glottal_and_physics(audio, sr)

    ensemble = AudioMultiModelEnsemble()
    out = ensemble.classify_audio(audio, sr, intel, phys, dna)
    assert 0.0 <= out["fused_ai_probability"] <= 1.0
    assert "typology_breakdown" in out
    assert "audio_domain" in out


def test_evidence_fusion_and_conformal_risk(sample_wav):
    file_path, audio, sr = sample_wav
    vault = create_evidence_record(file_path)
    dna = analyze_audio_dna(file_path, raw_audio_data=audio, sample_rate=sr)
    intel = extract_signal_intelligence(audio, sr)
    phys = analyze_glottal_and_physics(audio, sr)
    ensemble = AudioMultiModelEnsemble()
    models = ensemble.classify_audio(audio, sr, intel, phys, dna)
    splice = analyze_splicing_and_timeline(audio, sr)
    enf = analyze_environmental_and_enf(audio, sr)
    sec = analyze_security_and_provenance(file_path, audio, sr)
    speech = analyze_speech_and_semantics(audio, sr)

    fusion = compute_evidence_fusion_and_risk(
        vault, dna, intel, phys, models, splice, enf, sec, speech
    )
    assert fusion["final_verdict"] in ("AUTHENTIC", "AI_GENERATED", "MANIPULATED", "INCONCLUSIVE")
    assert 0.0 <= fusion["generative_ai_risk_score"] <= 1.0
    assert 0.0 <= fusion["structural_tampering_risk_score"] <= 1.0
    assert len(fusion["conformal_prediction_set"]) >= 1
    assert "evidence_graph" in fusion
    assert len(fusion["evidence_graph"]["nodes"]) >= 5


def test_analyze_audio_pipeline_end_to_end(sample_wav, tmp_path):
    file_path, _, _ = sample_wav
    ev_dir = tmp_path / "evidence"
    res = analyze_audio(file_path, ev_dir, "job_test_full")
    assert 0.0 <= res.fake_probability <= 1.0
    assert "AudioSentinel" in res.model_name
    assert res.evidence["media"] == "audio"
    assert len(res.evidence["pipeline_modules"]) == 8
    assert res.evidence["risk_tier"] in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK", "CRITICAL_RISK")
    assert (ev_dir / res.evidence["spectrogram_file"]).exists()
    assert (ev_dir / res.evidence["lfcc_scalogram_file"]).exists()
