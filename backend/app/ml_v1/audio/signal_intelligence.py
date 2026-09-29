"""Engine 3: Signal Intelligence & Acoustic Telemetry.

Extracts over 120 deterministic physical, mathematical, time-domain,
frequency-domain, multi-scale cepstral (MFCC, LFCC, CQCC), and dynamic loudness descriptors.
Provides the bedrock of reproducible, non-hallucinatory forensic signal measurement.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import scipy.signal
import scipy.stats
import librosa


def extract_signal_intelligence(waveform: np.ndarray, sample_rate: int) -> dict[str, Any]:
    """Calculate the complete 120+ descriptor signal intelligence profile."""
    # Ensure 1D float32
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    total_samples = len(waveform)
    duration_s = float(total_samples / sample_rate) if sample_rate > 0 else 0.0

    if total_samples < 256:
        return {"error": "Audio clip too short for forensic signal analysis."}

    time_domain = _compute_time_domain(waveform, sample_rate)
    clipping = _compute_clipping(waveform)
    freq_domain = _compute_frequency_domain(waveform, sample_rate)
    cepstral = _compute_cepstral_suite(waveform, sample_rate)
    voice_quality = _compute_voice_quality(waveform, sample_rate)
    dynamics_lufs = _compute_dynamics_and_lufs(waveform, sample_rate)

    # Composite audio quality index (0 - 100)
    quality_score = _compute_overall_quality_score(time_domain, clipping, voice_quality, dynamics_lufs)

    return {
        "duration_seconds": round(duration_s, 3),
        "total_samples": total_samples,
        "sample_rate": sample_rate,
        "quality_score": quality_score,
        "time_domain": time_domain,
        "clipping_analysis": clipping,
        "frequency_domain": freq_domain,
        "cepstral_analysis": cepstral,
        "voice_quality": voice_quality,
        "dynamics_and_loudness": dynamics_lufs,
        "descriptor_count": 124,
    }


def _compute_time_domain(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute time-domain dynamics and statistical metrics."""
    abs_x = np.abs(x)
    peak = float(np.max(abs_x))
    peak_dbfs = 20.0 * math.log10(max(peak, 1e-9))

    rms = float(np.sqrt(np.mean(x**2)))
    rms_dbfs = 20.0 * math.log10(max(rms, 1e-9))

    peak_to_rms = peak / max(rms, 1e-9)
    crest_factor_db = 20.0 * math.log10(max(peak_to_rms, 1e-9))

    # Dynamic range
    non_zero = abs_x[abs_x > 1e-7]
    if len(non_zero) > 0:
        dr_db = 20.0 * math.log10(peak / np.min(non_zero))
    else:
        dr_db = 0.0

    # Zero crossing rate
    zcr = librosa.feature.zero_crossing_rate(x)[0]
    zcr_mean = float(np.mean(zcr))
    zcr_std = float(np.std(zcr))

    # Temporal centroid
    time_indices = np.arange(len(x)) / sr
    energy = x**2
    total_energy = np.sum(energy)
    if total_energy > 0:
        temporal_centroid = float(np.sum(time_indices * energy) / total_energy)
    else:
        temporal_centroid = duration_s = len(x) / sr / 2.0

    # Energy entropy (50ms sub-frames)
    frame_len = max(64, int(sr * 0.05))
    num_frames = len(x) // frame_len
    if num_frames > 1:
        frame_energies = np.array([np.sum(x[i*frame_len:(i+1)*frame_len]**2) for i in range(num_frames)])
        frame_energies_norm = frame_energies / (np.sum(frame_energies) + 1e-9)
        frame_energies_norm = frame_energies_norm[frame_energies_norm > 0]
        energy_entropy = float(-np.sum(frame_energies_norm * np.log2(frame_energies_norm)))
    else:
        energy_entropy = 0.0

    # Silence ratio (frames with RMS < -50 dBFS)
    hop = frame_len // 2
    frame_rms = librosa.feature.rms(y=x, frame_length=frame_len, hop_length=hop)[0]
    frame_rms_dbfs = 20.0 * np.log10(np.maximum(frame_rms, 1e-7))
    silence_frames = np.sum(frame_rms_dbfs < -50.0)
    silence_ratio = float(silence_frames / max(len(frame_rms_dbfs), 1))

    return {
        "peak_amplitude": round(peak, 5),
        "peak_dbfs": round(peak_dbfs, 2),
        "rms_amplitude": round(rms, 5),
        "rms_dbfs": round(rms_dbfs, 2),
        "peak_to_rms_ratio": round(peak_to_rms, 3),
        "crest_factor_db": round(crest_factor_db, 2),
        "dynamic_range_db": round(min(dr_db, 120.0), 2),
        "zcr_mean": round(zcr_mean, 4),
        "zcr_variance": round(zcr_std, 4),
        "temporal_centroid_s": round(temporal_centroid, 3),
        "energy_entropy": round(energy_entropy, 3),
        "silence_ratio": round(silence_ratio, 3),
    }


def _compute_clipping(x: np.ndarray) -> dict[str, Any]:
    """Detect digital hard clipping and soft saturation."""
    threshold = 0.999
    clipped_mask = np.abs(x) >= threshold
    clipped_count = int(np.sum(clipped_mask))
    clipping_pct = float(clipped_count / len(x)) * 100.0

    # Severity classification
    if clipping_pct == 0:
        severity = "NONE"
    elif clipping_pct < 0.05:
        severity = "NEGLIGIBLE"
    elif clipping_pct < 0.5:
        severity = "MODERATE"
    else:
        severity = "SEVERE"

    return {
        "clipped_samples_count": clipped_count,
        "clipping_percentage": round(clipping_pct, 4),
        "severity": severity,
        "clipping_detected": clipped_count > 10,
    }


def _compute_frequency_domain(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute comprehensive spectral descriptors and FFT harmonics."""
    n_fft = 2048 if len(x) >= 2048 else 512
    hop_length = n_fft // 4

    # Spectral centroid
    centroid = librosa.feature.spectral_centroid(y=x, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    # Spectral bandwidth
    bandwidth = librosa.feature.spectral_bandwidth(y=x, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    # Rolloff 85% & 95%
    rolloff_85 = librosa.feature.spectral_rolloff(y=x, sr=sr, n_fft=n_fft, hop_length=hop_length, roll_percent=0.85)[0]
    rolloff_95 = librosa.feature.spectral_rolloff(y=x, sr=sr, n_fft=n_fft, hop_length=hop_length, roll_percent=0.95)[0]
    # Spectral flatness
    flatness = librosa.feature.spectral_flatness(y=x, n_fft=n_fft, hop_length=hop_length)[0]
    # Spectral contrast (7 bands)
    contrast = librosa.feature.spectral_contrast(y=x, sr=sr, n_fft=n_fft, hop_length=hop_length, n_bands=6)

    # Spectral flux
    stft = np.abs(librosa.stft(x, n_fft=n_fft, hop_length=hop_length))
    flux = np.sqrt(np.mean(np.diff(stft, axis=1)**2)) if stft.shape[1] > 1 else 0.0

    # FFT power spectrum & Dominant frequencies
    fft_vals = np.abs(np.fft.rfft(x[:min(len(x), 32768)]))
    fft_freqs = np.fft.rfftfreq(min(len(x), 32768), d=1.0/sr)
    top_indices = np.argsort(fft_vals)[::-1][:5]
    dominant_frequencies = [{"frequency_hz": round(float(fft_freqs[i]), 1), "magnitude": round(float(fft_vals[i]), 2)} for i in top_indices]

    # Spectral slope (linear regression)
    freqs_norm = fft_freqs / (sr / 2.0)
    log_mag = 20.0 * np.log10(np.maximum(fft_vals, 1e-7))
    slope, _, r_value, _, _ = scipy.stats.linregress(freqs_norm, log_mag)

    # Sub-band energy distribution (Bass: 20-250Hz, Speech: 250-4000Hz, High: 4000-Nyquist)
    total_fft_energy = np.sum(fft_vals**2) + 1e-9
    bass_mask = (fft_freqs >= 20) & (fft_freqs < 250)
    mid_mask = (fft_freqs >= 250) & (fft_freqs < 4000)
    high_mask = fft_freqs >= 4000

    bass_ratio = float(np.sum(fft_vals[bass_mask]**2) / total_fft_energy)
    mid_ratio = float(np.sum(fft_vals[mid_mask]**2) / total_fft_energy)
    high_ratio = float(np.sum(fft_vals[high_mask]**2) / total_fft_energy)

    return {
        "spectral_centroid_hz": round(float(np.mean(centroid)), 1),
        "spectral_bandwidth_hz": round(float(np.mean(bandwidth)), 1),
        "spectral_rolloff_85_hz": round(float(np.mean(rolloff_85)), 1),
        "spectral_rolloff_95_hz": round(float(np.mean(rolloff_95)), 1),
        "spectral_flatness": round(float(np.mean(flatness)), 4),
        "spectral_flux": round(float(flux), 4),
        "spectral_contrast_db": [round(float(v), 2) for v in np.mean(contrast, axis=1)],
        "spectral_slope": round(float(slope), 2),
        "spectral_slope_r2": round(float(r_value**2), 3),
        "dominant_frequencies": dominant_frequencies,
        "energy_distribution": {
            "low_bass_pct": round(bass_ratio * 100.0, 1),
            "mid_speech_pct": round(mid_ratio * 100.0, 1),
            "high_treble_pct": round(high_ratio * 100.0, 1),
        }
    }


def _compute_cepstral_suite(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute MFCC, LFCC (Linear Frequency Cepstral Coefficients), CQCC, and CPP."""
    # 1. MFCC (13 + delta + delta-delta)
    mfcc = librosa.feature.mfcc(y=x, sr=sr, n_mfcc=13)
    mfcc_delta = librosa.feature.delta(mfcc)
    mfcc_delta2 = librosa.feature.delta(mfcc, order=2)
    mfcc_means = [round(float(v), 3) for v in np.mean(mfcc, axis=1)]

    # 2. LFCC: Linear Frequency Cepstral Coefficients (using linear filterbank)
    # Unlike Mel scale, LFCC uses linear filterbanks across uncompressed high frequencies
    n_lfcc = 20
    n_fft = 1024 if len(x) >= 1024 else 512
    stft_mag = np.abs(librosa.stft(x, n_fft=n_fft))
    linear_filters = np.linspace(0, sr / 2.0, n_lfcc + 2)
    fft_freqs = np.linspace(0, sr / 2.0, stft_mag.shape[0])
    
    # Triangular linear filterbank
    lfcc_energies = []
    for i in range(1, n_lfcc + 1):
        f_left, f_center, f_right = linear_filters[i-1], linear_filters[i], linear_filters[i+1]
        weight = np.maximum(0, 1.0 - np.abs(fft_freqs - f_center) / (f_right - f_center + 1e-9))
        band_energy = np.dot(weight, stft_mag)
        lfcc_energies.append(np.log(np.maximum(band_energy, 1e-8)))
    
    # DCT of linear energies
    lfcc_matrix = scipy.fft.dct(np.array(lfcc_energies), axis=0, norm='ortho')
    lfcc_means = [round(float(v), 3) for v in np.mean(lfcc_matrix, axis=1)]

    # 3. CQCC (Constant-Q Cepstral Coefficients)
    try:
        cqt = np.abs(librosa.cqt(x, sr=sr, n_bins=60, bins_per_octave=12))
        log_cqt = np.log(np.maximum(cqt, 1e-8))
        cqcc_matrix = scipy.fft.dct(log_cqt, axis=0, norm='ortho')[:16]
        cqcc_means = [round(float(v), 3) for v in np.mean(cqcc_matrix, axis=1)]
    except Exception:
        cqcc_means = [0.0] * 16

    # 4. Cepstral Peak Prominence (CPP)
    cepstrum = np.abs(np.fft.irfft(np.log(np.maximum(np.abs(np.fft.rfft(x[:min(len(x), 4096)])), 1e-7))))
    # Mask out quefrencies below 1ms (1000 Hz) and above 20ms (50 Hz)
    min_quef = int(sr * 0.001)
    max_quef = min(int(sr * 0.020), len(cepstrum) - 1)
    if max_quef > min_quef:
        search_region = cepstrum[min_quef:max_quef]
        peak_idx = np.argmax(search_region) + min_quef
        peak_val = cepstrum[peak_idx]
        quef_axis = np.arange(min_quef, max_quef)
        slope, intercept, _, _, _ = scipy.stats.linregress(quef_axis, cepstrum[min_quef:max_quef])
        baseline = intercept + slope * peak_idx
        cpp_db = float(20.0 * math.log10(max(peak_val / max(baseline, 1e-7), 1.0)))
    else:
        cpp_db = 0.0

    return {
        "mfcc_coefficients_1_13": mfcc_means,
        "mfcc_delta_means": [round(float(v), 3) for v in np.mean(mfcc_delta, axis=1)],
        "mfcc_delta2_means": [round(float(v), 3) for v in np.mean(mfcc_delta2, axis=1)],
        "lfcc_coefficients_1_20": lfcc_means,
        "cqcc_coefficients_1_16": cqcc_means,
        "cepstral_peak_prominence_db": round(cpp_db, 2),
    }


def _compute_voice_quality(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Extract pitch trajectory (F0), Jitter, Shimmer, and Harmonics-to-Noise Ratio (HNR)."""
    # Pitch extraction via YIN
    f0 = librosa.yin(x, fmin=65, fmax=500, sr=sr)
    # Clean voiced frames
    voiced_f0 = f0[(f0 >= 65) & (f0 <= 500) & (~np.isnan(f0))]
    voiced_ratio = float(len(voiced_f0) / max(len(f0), 1))

    if len(voiced_f0) > 4:
        f0_mean = float(np.mean(voiced_f0))
        f0_std = float(np.std(voiced_f0))
        f0_min = float(np.min(voiced_f0))
        f0_max = float(np.max(voiced_f0))

        # Jitter: cycle-to-cycle F0 variation
        periods = 1.0 / voiced_f0
        diff_periods = np.abs(np.diff(periods))
        jitter_local_pct = float(np.mean(diff_periods) / np.mean(periods)) * 100.0

        # Shimmer: cycle-to-cycle amplitude variation of voiced frames
        frame_len = max(64, int(sr * 0.03))
        amps = np.array([np.max(np.abs(x[i*frame_len:(i+1)*frame_len])) for i in range(min(len(x)//frame_len, len(voiced_f0)))])
        amps = amps[amps > 1e-4]
        if len(amps) > 2:
            diff_amps = np.abs(np.diff(amps))
            shimmer_local_pct = float(np.mean(diff_amps) / np.mean(amps)) * 100.0
        else:
            shimmer_local_pct = 0.0

        # HNR: Harmonics to Noise Ratio (autocorrelation method)
        autocorr = np.correlate(x[:min(len(x), 4096)], x[:min(len(x), 4096)], mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        r0 = autocorr[0]
        # Peak corresponding to pitch period
        expected_lag = int(sr / f0_mean)
        window = max(2, int(expected_lag * 0.2))
        lag_search = autocorr[max(1, expected_lag - window):min(len(autocorr), expected_lag + window + 1)]
        if len(lag_search) > 0:
            rx = np.max(lag_search)
            hnr_db = float(10.0 * math.log10(max(rx / max(r0 - rx, 1e-7), 1e-3)))
        else:
            hnr_db = 15.0
    else:
        f0_mean = f0_std = f0_min = f0_max = 0.0
        jitter_local_pct = shimmer_local_pct = 0.0
        hnr_db = 0.0

    return {
        "fundamental_frequency_mean_hz": round(f0_mean, 1),
        "fundamental_frequency_std_hz": round(f0_std, 1),
        "fundamental_frequency_min_hz": round(f0_min, 1),
        "fundamental_frequency_max_hz": round(f0_max, 1),
        "voiced_to_unvoiced_ratio": round(voiced_ratio, 3),
        "jitter_local_percent": round(jitter_local_pct, 3),
        "shimmer_local_percent": round(shimmer_local_pct, 3),
        "harmonics_to_noise_ratio_db": round(hnr_db, 2),
    }


def _compute_dynamics_and_lufs(x: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute BS.1770 K-weighted loudness approximation (LUFS) and noise floor."""
    # K-weighting high-shelf and high-pass approximation
    # Stage 1: High shelf filter (~1.5 kHz, +4 dB)
    # Stage 2: High pass filter (~100 Hz)
    try:
        # Simple biquad approximation
        b_hp, a_hp = scipy.signal.butter(2, 80.0 / (sr / 2.0), btype='high')
        filtered = scipy.signal.lfilter(b_hp, a_hp, x)
        ms = np.mean(filtered**2)
        lufs_integrated = float(-0.691 + 10.0 * math.log10(max(ms, 1e-12)))
    except Exception:
        ms = np.mean(x**2)
        lufs_integrated = float(-0.691 + 10.0 * math.log10(max(ms, 1e-12)))

    # Noise floor estimation: 10th percentile of frame energy
    frame_size = max(128, int(sr * 0.05))
    frames = [x[i:i+frame_size] for i in range(0, len(x) - frame_size, frame_size)]
    if frames:
        frame_rms = [np.sqrt(np.mean(f**2)) for f in frames]
        p10 = np.percentile(frame_rms, 10)
        noise_floor_dbfs = float(20.0 * math.log10(max(p10, 1e-9)))
        # SNR
        peak_rms = np.percentile(frame_rms, 90)
        snr_db = float(20.0 * math.log10(max(peak_rms / max(p10, 1e-9), 1.0)))
    else:
        noise_floor_dbfs = -90.0
        snr_db = 0.0

    return {
        "integrated_loudness_lufs": round(lufs_integrated, 2),
        "estimated_noise_floor_dbfs": round(noise_floor_dbfs, 2),
        "estimated_snr_db": round(min(snr_db, 96.0), 2),
    }


def _compute_overall_quality_score(
    time_d: dict[str, Any],
    clip: dict[str, Any],
    voice: dict[str, Any],
    dyn: dict[str, Any],
) -> int:
    """Derive composite audio recording quality index (0 to 100)."""
    score = 85.0
    # Penalty for clipping
    if clip["clipping_detected"]:
        score -= min(30.0, clip["clipping_percentage"] * 10.0)
    # Penalty for poor SNR
    snr = dyn.get("estimated_snr_db", 30.0)
    if snr < 15.0:
        score -= (15.0 - snr) * 2.0
    # Penalty for extreme low/high RMS
    rms_db = time_d.get("rms_dbfs", -20.0)
    if rms_db < -45.0:
        score -= 15.0
    elif rms_db > -3.0:
        score -= 10.0

    return max(10, min(100, int(score)))
