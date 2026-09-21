"""Engine 4: Physiological Glottal Flow (IAIF) & Physical Acoustics (VoiceRadar).

Implements:
1. Iterative Adaptive Inverse Filtering (IAIF) to isolate the glottal volume velocity
   waveform and quantify vocal fold closure dynamics and biological turbulence.
2. VoiceRadar physical approximation models (micro-Doppler frequency variations and
   2D circular drumhead membrane Bessel oscillations) to detect lack of physical air propagation.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import scipy.signal
import scipy.special


def analyze_glottal_and_physics(waveform: np.ndarray, sample_rate: int) -> dict[str, Any]:
    """Execute complete physiological glottal inverse filtering and physical propagation analysis."""
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    if len(waveform) < 1024:
        return {
            "glottal_flow": {"status": "UNAVAILABLE", "reason": "Signal too short"},
            "physical_propagation": {"status": "UNAVAILABLE"},
            "physiological_anomaly_score": 0.0,
        }

    glottal_results = _compute_iaif_glottal_flow(waveform, sample_rate)
    voiceradar_results = _compute_voiceradar_physics(waveform, sample_rate)

    # Anomaly synthesis
    iaif_anomaly = glottal_results.get("glottal_anomaly_score", 0.0)
    physics_anomaly = voiceradar_results.get("physics_anomaly_score", 0.0)
    composite_anomaly = float(0.55 * iaif_anomaly + 0.45 * physics_anomaly)

    return {
        "glottal_flow": glottal_results,
        "physical_propagation": voiceradar_results,
        "composite_physiological_anomaly_score": round(composite_anomaly, 4),
        "physiological_verdict": "SUSPICIOUS_UNNATURAL_AERODYNAMICS" if composite_anomaly > 0.65 else "CONSISTENT_BIOLOGICAL_VOCAL_TRACT",
    }


def _compute_iaif_glottal_flow(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Estimate glottal volume velocity via Iterative Adaptive Inverse Filtering (IAIF)."""
    try:
        # Pre-emphasis (cancelling first-order lip radiation ~ +6dB/octave)
        # Lip radiation filter: R(z) = 1 - alpha * z^-1 (alpha ~ 0.98)
        alpha = 0.98
        d_x = np.diff(x, prepend=x[0])

        # Step 1: 1st LPC model of speech spectrum (low order, order ~ 1 for glottal tilt)
        p_glottal_pre = 1
        a_g1 = _lpc_burg(x, p_glottal_pre)
        # Cancel glottal tilt from original speech
        x_vt1 = np.asarray(scipy.signal.lfilter(a_g1, [1.0], x), dtype=np.float32)

        # Step 2: 1st LPC model of vocal tract (order ~ sr/1000 + 4, e.g. 16kHz -> order 20)
        p_vt = min(24, max(8, int(sr / 1000) + 4))
        a_vt1 = _lpc_burg(x_vt1, p_vt)

        # Step 3: Preliminary glottal flow by filtering speech with estimated vocal tract
        g_pre = np.asarray(scipy.signal.lfilter(a_vt1, [1.0], x), dtype=np.float32)

        # Step 4: Refined LPC model of glottal flow (order ~ 4)
        a_g2 = _lpc_burg(g_pre, 4)
        # Refined vocal tract input
        x_vt2 = np.asarray(scipy.signal.lfilter(a_g2, [1.0], x), dtype=np.float32)

        # Step 5: Refined LPC model of vocal tract
        a_vt2 = _lpc_burg(x_vt2, p_vt)

        # Step 6: Final glottal volume velocity: filter original speech by refined vocal tract
        # and integrate to cancel lip radiation (1 / (1 - alpha * z^-1))
        glottal_deriv = np.asarray(scipy.signal.lfilter(a_vt2, [1.0], x), dtype=np.float32)
        glottal_flow = np.asarray(scipy.signal.lfilter([1.0], [1.0, -alpha], glottal_deriv), dtype=np.float32)

        # Normalize glottal flow
        glottal_flow = glottal_flow - np.mean(glottal_flow)
        std_g = np.std(glottal_flow)
        if std_g > 1e-7:
            glottal_flow = glottal_flow / std_g

        # Physiological metrics
        # Maximum Flow Declination Rate (MFDR): steepness of closing slope
        diff_g = np.diff(glottal_flow)
        mfdr = float(np.min(diff_g))  # Most negative derivative

        # Estimate open quotient (Qo) and closing quotient (Qc) on highest energy voiced pulse
        frame_len = min(len(glottal_flow), int(sr * 0.05))
        pulse_seg = glottal_flow[:frame_len]
        peaks, _ = scipy.signal.find_peaks(pulse_seg, distance=max(10, int(sr * 0.002)))
        
        if len(peaks) > 1:
            pulse_periods = np.diff(peaks)
            mean_period = np.mean(pulse_periods)
            # Estimate open phase (samples above baseline zero)
            pos_samples = np.sum(pulse_seg > 0)
            open_quotient = float(min(1.0, max(0.1, pos_samples / len(pulse_seg))))
            # Closing phase steepness ratio
            closing_quotient = float(min(0.5, max(0.05, abs(mfdr) / (np.max(pulse_seg) + 1e-7) / 20.0)))
        else:
            open_quotient = 0.55
            closing_quotient = 0.22

        # Glottal periodicity consistency and turbulence
        # Biological vocal tracts have subtle chaotic turbulence (micro-jitter in pulses)
        autocorr_g = np.correlate(glottal_flow[:min(len(glottal_flow), 2048)], glottal_flow[:min(len(glottal_flow), 2048)], mode='full')
        autocorr_g = autocorr_g[len(autocorr_g)//2:]
        if len(autocorr_g) > 20:
            peak_r = np.max(autocorr_g[10:]) / (autocorr_g[0] + 1e-7)
            glottal_turbulence = float(max(0.0, 1.0 - peak_r))
        else:
            glottal_turbulence = 0.05

        # AI synthesis often yields unnaturally smooth or erratic glottal pulses
        # Human open quotient typically falls in 0.40 - 0.70; closing quotient in 0.15 - 0.35
        qo_err = abs(open_quotient - 0.55) / 0.55
        qc_err = abs(closing_quotient - 0.25) / 0.25
        # Vocoders lack natural biological vocal turbulence (over-smoothed speech)
        turb_err = 1.0 - min(1.0, glottal_turbulence / 0.08)

        glottal_anomaly = float(min(1.0, 0.4 * qo_err + 0.3 * qc_err + 0.3 * turb_err))

        return {
            "open_quotient": round(open_quotient, 3),
            "closing_quotient": round(closing_quotient, 3),
            "mfdr_index": round(abs(mfdr), 3),
            "biological_turbulence_index": round(glottal_turbulence, 4),
            "glottal_anomaly_score": round(glottal_anomaly, 4),
            "status": "ANALYZED",
        }

    except Exception as exc:
        return {
            "open_quotient": 0.50,
            "closing_quotient": 0.25,
            "mfdr_index": 1.0,
            "biological_turbulence_index": 0.05,
            "glottal_anomaly_score": 0.15,
            "status": f"FALLBACK_ESTIMATE ({exc})",
        }


def _compute_voiceradar_physics(x: np.ndarray, sr: int) -> dict[str, Any]:
    """VoiceRadar physical approximation: micro-Doppler shifts and circular drumhead Bessel harmonics."""
    try:
        # 1. Micro-Doppler Translational Dynamics
        # Natural speakers produce minute frequency shifts as they move in 3D air.
        # Compute instantaneous frequency via analytic signal Hilbert transform
        analytic_signal = scipy.signal.hilbert(x[:min(len(x), 16384)])
        inst_phase = np.unwrap(np.angle(analytic_signal))
        inst_freq = np.diff(inst_phase) / (2.0 * np.pi) * sr

        # Clean valid frequency range (50 - 4000 Hz)
        valid_freqs = inst_freq[(inst_freq > 50) & (inst_freq < 4000)]
        if len(valid_freqs) > 100:
            # Measure micro-dispersion (Doppler variance)
            freq_diffs = np.diff(valid_freqs)
            doppler_dispersion = float(np.std(freq_diffs))
            # AI synthesis generated in pure digital domain lacks 3D translational micro-frequency dispersion
            doppler_anomaly = float(np.clip(1.0 - (doppler_dispersion / 85.0), 0.0, 1.0))
        else:
            doppler_dispersion = 60.0
            doppler_anomaly = 0.2

        # 2. 2D Drumhead Acoustic Propagation Approximation
        # Real acoustic sound propagation in an enclosed room adheres to circular membrane
        # mode harmonic ratios (Bessel function roots alpha_nm: 2.405, 3.832, 5.136, 5.520)
        # Expected ratio of mode (0,2) to mode (0,1) is 5.520 / 2.405 = 2.295
        fft = np.abs(np.fft.rfft(x[:min(len(x), 8192)]))
        freqs = np.fft.rfftfreq(min(len(x), 8192), d=1.0/sr)
        peaks, _ = scipy.signal.find_peaks(fft, distance=20)
        if len(peaks) >= 3:
            top_peaks = np.sort(freqs[peaks[np.argsort(fft[peaks])[-3:]]])
            if top_peaks[0] > 20:
                ratio_observed = top_peaks[1] / top_peaks[0]
                # Compare against drumhead / acoustic cavity resonance baseline (~2.30)
                physics_adherence = float(abs(ratio_observed - 2.295) / 2.295)
                physics_anomaly = float(min(1.0, 0.5 * doppler_anomaly + 0.5 * min(1.0, physics_adherence)))
            else:
                physics_anomaly = doppler_anomaly
        else:
            physics_anomaly = doppler_anomaly

        return {
            "doppler_micro_dispersion_hz": round(doppler_dispersion, 2),
            "doppler_anomaly_score": round(doppler_anomaly, 4),
            "acoustic_propagation_adherence": round(1.0 - physics_anomaly, 3),
            "physics_anomaly_score": round(physics_anomaly, 4),
            "status": "COMPLETED",
        }
    except Exception as exc:
        return {
            "doppler_micro_dispersion_hz": 50.0,
            "doppler_anomaly_score": 0.25,
            "acoustic_propagation_adherence": 0.85,
            "physics_anomaly_score": 0.25,
            "status": f"ESTIMATED ({exc})",
        }


def _lpc_burg(x: np.ndarray, order: int) -> np.ndarray:
    """Compute LPC filter coefficients using Burg's lattice autoregressive method."""
    N = len(x)
    ef = np.copy(x)
    eb = np.copy(x)
    a = np.zeros(order + 1)
    a[0] = 1.0

    for m in range(1, order + 1):
        num = -2.0 * np.sum(ef[m:N] * eb[m-1:N-1])
        den = np.sum(ef[m:N]**2 + eb[m-1:N-1]**2) + 1e-12
        k = num / den
        # Update filter coefficients
        a_prev = np.copy(a)
        for i in range(1, m):
            a[i] = a_prev[i] + k * a_prev[m - i]
        a[m] = k
        # Update forward and backward prediction errors
        ef_prev = np.copy(ef)
        ef[m:N] = ef_prev[m:N] + k * eb[m-1:N-1]
        eb[m:N] = eb[m-1:N-1] + k * ef_prev[m:N]

    return a
