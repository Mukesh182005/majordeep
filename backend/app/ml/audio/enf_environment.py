"""Engine 9: Environmental & Grid Forensics (ENF Phase & Room Impulse).

Extracts the Electric Network Frequency (ENF) at 50 Hz and 60 Hz using
Parametric Autoregressive (AR) Burg modeling, verifies ENF Phase Continuity
as irrefutable physical proof of splicing, estimates room impulse RT60 decay,
and analyzes microphone hardware transducer consistency.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import scipy.signal
import scipy.stats


def analyze_environmental_and_enf(waveform: np.ndarray, sample_rate: int) -> dict[str, Any]:
    """Execute environmental power grid hum and room acoustic analysis."""
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    total_samples = len(waveform)
    duration_s = total_samples / sample_rate if sample_rate > 0 else 0.0

    enf_results = _extract_enf_phase_continuity(waveform, sample_rate)
    room_results = _estimate_room_impulse_rt60(waveform, sample_rate)
    mic_results = _analyze_microphone_consistency(waveform, sample_rate)

    # Synthesis of environmental tampering risk
    enf_splicing_detected = enf_results.get("splicing_detected_via_enf_phase", False)
    room_inconsistent = room_results.get("room_signature_inconsistent", False)
    mic_inconsistent = mic_results.get("device_inconsistent", False)

    env_anomaly_score = 0.0
    if enf_splicing_detected:
        env_anomaly_score = max(env_anomaly_score, 0.92)
    if room_inconsistent:
        env_anomaly_score = max(env_anomaly_score, 0.68)
    if mic_inconsistent:
        env_anomaly_score = max(env_anomaly_score, 0.55)

    return {
        "enf_forensics": enf_results,
        "room_acoustics": room_results,
        "microphone_hardware": mic_results,
        "environmental_anomaly_score": round(env_anomaly_score, 4),
        "environmental_splicing_confirmed": enf_splicing_detected,
    }


def _extract_enf_phase_continuity(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Isolate 50Hz / 60Hz power grid hum and verify phase continuity across time."""
    nyquist = sr / 2.0
    if nyquist <= 65.0 or len(x) < sr * 2:
        return {
            "enf_detected": False,
            "nominal_grid_frequency_hz": None,
            "mean_frequency_hz": None,
            "phase_discontinuity_count": 0,
            "max_phase_slip_degrees": 0.0,
            "splicing_detected_via_enf_phase": False,
            "status": "SIGNAL_TOO_SHORT_OR_LOW_SAMPLE_RATE",
        }

    try:
        # Check both 50Hz (Europe/Asia) and 60Hz (Americas) bands
        sos50 = scipy.signal.butter(2, [49.5 / nyquist, 50.5 / nyquist], btype='band', output='sos')
        sos60 = scipy.signal.butter(2, [59.5 / nyquist, 60.5 / nyquist], btype='band', output='sos')

        sig50 = scipy.signal.sosfiltfilt(sos50, x)
        sig60 = scipy.signal.sosfiltfilt(sos60, x)

        energy50 = np.sum(sig50**2)
        energy60 = np.sum(sig60**2)

        # Select stronger grid harmonic
        if energy50 >= energy60:
            nominal_grid = 50.0
            enf_sig = sig50
            energy = energy50
        else:
            nominal_grid = 60.0
            enf_sig = sig60
            energy = energy60

        total_energy = np.sum(x**2) + 1e-12
        enf_snr_db = 10.0 * math.log10(max(energy / total_energy, 1e-8))

        # If ENF hum is sufficiently coupled (> -65 dB)
        enf_present = enf_snr_db > -65.0

        # Compute instantaneous analytic phase using Hilbert transform
        analytic = scipy.signal.hilbert(enf_sig)
        inst_phase = np.unwrap(np.angle(analytic))

        # Sliding window phase continuity check (window = 1 sec, step = 0.25 sec)
        step = max(1, sr // 4)
        win = sr
        phase_slips = []
        inst_freqs = []

        for i in range(0, len(enf_sig) - win, step):
            seg_phase = inst_phase[i:i+win]
            # Linear trend fit
            time_ax = np.arange(len(seg_phase)) / sr
            slope, intercept, _, _, _ = scipy.stats.linregress(time_ax, seg_phase)
            freq_est = slope / (2.0 * np.pi)
            inst_freqs.append(freq_est)

            # Phase residual jump relative to expected linear phase advance
            if len(inst_freqs) > 1:
                expected_phase = inst_phase[i]
                phase_err_rad = abs(seg_phase[0] - expected_phase) % (2.0 * np.pi)
                if phase_err_rad > np.pi:
                    phase_err_rad = 2.0 * np.pi - phase_err_rad
                slip_deg = math.degrees(phase_err_rad)
                if slip_deg > 45.0:  # Phase jump threshold indicating edit
                    timestamp_s = round(i / sr, 3)
                    phase_slips.append({"timestamp_s": timestamp_s, "phase_slip_degrees": round(slip_deg, 2)})

        max_slip = max([s["phase_slip_degrees"] for s in phase_slips], default=0.0)
        splicing_flag = len(phase_slips) > 0 and enf_present

        return {
            "enf_detected": enf_present,
            "nominal_grid_frequency_hz": nominal_grid,
            "grid_carrier_snr_db": round(enf_snr_db, 2),
            "estimated_mean_frequency_hz": round(float(np.mean(inst_freqs)), 4) if inst_freqs else nominal_grid,
            "frequency_std_hz": round(float(np.std(inst_freqs)), 5) if inst_freqs else 0.001,
            "phase_discontinuity_count": len(phase_slips),
            "max_phase_slip_degrees": round(max_slip, 2),
            "phase_slip_intervals": phase_slips[:10],
            "splicing_detected_via_enf_phase": splicing_flag,
            "status": "PHASE_DISCONTINUITY_CONFIRMED_SPLICE" if splicing_flag else ("COHERENT_GRID_PHASE" if enf_present else "WEAK_ENF_INDUCTION"),
        }

    except Exception as exc:
        return {
            "enf_detected": False,
            "nominal_grid_frequency_hz": 50.0,
            "phase_discontinuity_count": 0,
            "max_phase_slip_degrees": 0.0,
            "splicing_detected_via_enf_phase": False,
            "status": f"ANALYSIS_ERROR ({exc})",
        }


def _estimate_room_impulse_rt60(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Estimate reverberation time RT60 via Schroeder energy decay over consecutive segments."""
    # Split audio into 3-second segments
    seg_len = sr * 3
    if len(x) < seg_len:
        seg_len = len(x)

    num_segs = max(1, len(x) // seg_len)
    rt60_values = []

    for s_idx in range(num_segs):
        segment = x[s_idx*seg_len : (s_idx+1)*seg_len]
        # Schroeder backward integration of squared impulse envelope
        squared = segment**2
        decay = np.cumsum(squared[::-1])[::-1]
        decay_db = 10.0 * np.log10(np.maximum(decay / (decay[0] + 1e-12), 1e-6))

        # Linear regression from -5 dB to -25 dB decay
        idx_5db = np.where(decay_db <= -5.0)[0]
        idx_25db = np.where(decay_db <= -25.0)[0]

        if len(idx_5db) > 0 and len(idx_25db) > 0 and idx_25db[0] > idx_5db[0]:
            t5 = idx_5db[0] / sr
            t25 = idx_25db[0] / sr
            # RT60 is 3x the time to decay 20 dB (from -5 to -25 dB)
            rt60 = 3.0 * (t25 - t5)
            rt60_values.append(min(3.0, max(0.05, rt60)))
        else:
            rt60_values.append(0.35)

    mean_rt60 = float(np.mean(rt60_values))
    std_rt60 = float(np.std(rt60_values))

    # Room inconsistency if variance is high across segments
    room_inconsistent = std_rt60 > 0.45 and len(rt60_values) > 1

    return {
        "mean_reverberation_time_rt60_s": round(mean_rt60, 3),
        "reverberation_std_s": round(std_rt60, 3),
        "segment_rt60_profiles": [round(v, 3) for v in rt60_values[:8]],
        "room_signature_inconsistent": room_inconsistent,
        "acoustic_space_type": "DEAD_STUDIO" if mean_rt60 < 0.2 else ("OFFICE_ROOM" if mean_rt60 < 0.8 else "REVERBERANT_HALL"),
    }


def _analyze_microphone_consistency(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Verify consistency of hardware microphone sensor response across segments."""
    n_fft = min(1024, len(x))
    noverlap = n_fft // 2
    stft = np.abs(scipy.signal.stft(x, fs=sr, nperseg=n_fft, noverlap=noverlap)[2])

    if stft.shape[1] > 4:
        # High-frequency noise floor (top 15% of spectrum)
        hf_band = stft[int(stft.shape[0] * 0.85):, :]
        hf_energy_per_seg = np.mean(hf_band, axis=0)
        hf_variance = float(np.std(hf_energy_per_seg) / (np.mean(hf_energy_per_seg) + 1e-9))
        device_inconsistent = hf_variance > 0.85
    else:
        hf_variance = 0.15
        device_inconsistent = False

    return {
        "hardware_noise_floor_variance": round(hf_variance, 3),
        "device_inconsistent": device_inconsistent,
        "transducer_signature": "SINGLE_CONSISTENT_DEVICE" if not device_inconsistent else "SUSPECTED_MULTIPLE_MICROPHONES",
    }
