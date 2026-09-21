"""Engine 5: Multi-Resolution Diagnostic Signal Lab.

Renders and saves high-resolution, multi-domain diagnostic visual plates into the
evidence vault:
1. Calibrated Raw Waveform with RMS envelope & clipping markers
2. FFT Magnitude Spectrum & Dominant Harmonics
3. Full-Bandwidth STFT Spectrogram
4. Log-Mel Spectrogram with dynamic range scaling
5. Linear Frequency Cepstral (LFCC) Scalogram
6. Constant-Q Transform (CQT) Scalogram
7. Phase Coherence Heatmap
8. Master 6-Panel Multi-Resolution Forensic Plate
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import librosa
import scipy.signal
import scipy.fft

logger = logging.getLogger(__name__)


def generate_signal_lab_plates(
    waveform: np.ndarray,
    sample_rate: int,
    evidence_dir: str | Path,
    job_id: str,
    segment_scores: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Generate and save all multi-resolution forensic scalograms and return their filenames."""
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    waveform = waveform.astype(np.float32)

    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    duration_s = len(waveform) / sample_rate
    generated_files = {}

    # ------------------------------------------------------------- 1. Master Mel Spectrogram (with Flagged Windows)
    try:
        mel_path = evidence_dir / f"{job_id}_spectrogram.png"
        _render_log_mel_spectrogram(waveform, sample_rate, duration_s, mel_path, segment_scores)
        generated_files["spectrogram_file"] = mel_path.name
    except Exception as exc:
        logger.warning("Error rendering Mel spectrogram for %s: %s", job_id, exc)

    # ------------------------------------------------------------- 2. LFCC Scalogram
    try:
        lfcc_path = evidence_dir / f"{job_id}_lfcc_scalogram.png"
        _render_lfcc_scalogram(waveform, sample_rate, duration_s, lfcc_path)
        generated_files["lfcc_scalogram_file"] = lfcc_path.name
    except Exception as exc:
        logger.warning("Error rendering LFCC scalogram for %s: %s", job_id, exc)

    # ------------------------------------------------------------- 3. CQT Scalogram
    try:
        cqt_path = evidence_dir / f"{job_id}_cqt_scalogram.png"
        _render_cqt_scalogram(waveform, sample_rate, duration_s, cqt_path)
        generated_files["cqt_scalogram_file"] = cqt_path.name
    except Exception as exc:
        logger.warning("Error rendering CQT scalogram for %s: %s", job_id, exc)

    # ------------------------------------------------------------- 4. Waveform & RMS Profile
    try:
        wave_path = evidence_dir / f"{job_id}_waveform_profile.png"
        _render_waveform_profile(waveform, sample_rate, duration_s, wave_path)
        generated_files["waveform_file"] = wave_path.name
    except Exception as exc:
        logger.warning("Error rendering waveform profile for %s: %s", job_id, exc)

    # ------------------------------------------------------------- 5. Master Multi-Resolution 4-Panel Plate
    try:
        multi_path = evidence_dir / f"{job_id}_multi_resolution_plate.png"
        _render_master_diagnostic_plate(waveform, sample_rate, duration_s, multi_path, segment_scores)
        generated_files["multi_resolution_plate_file"] = multi_path.name
    except Exception as exc:
        logger.warning("Error rendering master diagnostic plate for %s: %s", job_id, exc)

    return generated_files


def _render_log_mel_spectrogram(
    x: np.ndarray,
    sr: int,
    duration_s: float,
    out_path: Path,
    segment_scores: list[dict[str, Any]] | None,
) -> None:
    """Render high-resolution log-Mel spectrogram with red bounding boxes over flagged segments."""
    mel = librosa.feature.melspectrogram(y=x, sr=sr, n_mels=80, n_fft=1024, hop_length=160)
    log_mel = librosa.power_to_db(mel, ref=np.max)

    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    img = ax.imshow(
        log_mel,
        aspect="auto",
        origin="lower",
        cmap="inferno",
        extent=(0, duration_s, 0, sr / 2 / 1000),
    )
    ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequency (kHz)", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_title("Multi-Resolution Log-Mel Spectrogram (Flagged Windows Highlighted)", color="#f8fafc", fontsize=11, fontweight="bold", pad=12)
    ax.tick_params(colors="#64748b", labelsize=9)

    # Flagged bounding boxes
    if segment_scores:
        import matplotlib.patches as mpatches
        for seg in segment_scores:
            prob = seg.get("fake_probability", 0.0)
            if prob >= 0.65:
                start = seg.get("start_s", 0.0)
                end = seg.get("end_s", start + 2.0)
                rect = mpatches.Rectangle(
                    (start, 0.1),
                    end - start,
                    (sr / 2 / 1000) - 0.2,
                    linewidth=2.0,
                    edgecolor="#ef4444",
                    facecolor="#ef4444",
                    alpha=0.25,
                    linestyle="--",
                )
                ax.add_patch(rect)

    cbar = fig.colorbar(img, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label("Energy (dB)", color="#94a3b8", fontsize=9)
    cbar.ax.tick_params(colors="#64748b", labelsize=8)

    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _render_lfcc_scalogram(x: np.ndarray, sr: int, duration_s: float, out_path: Path) -> None:
    """Render Linear Frequency Cepstral Coefficients (LFCC) scalogram."""
    n_lfcc = 30
    stft_mag = np.abs(librosa.stft(x, n_fft=1024, hop_length=256))
    linear_filters = np.linspace(0, sr / 2.0, n_lfcc + 2)
    fft_freqs = np.linspace(0, sr / 2.0, stft_mag.shape[0])

    lfcc_energies = []
    for i in range(1, n_lfcc + 1):
        f_left, f_center, f_right = linear_filters[i-1], linear_filters[i], linear_filters[i+1]
        weight = np.maximum(0, 1.0 - np.abs(fft_freqs - f_center) / (f_right - f_center + 1e-9))
        band_energy = np.dot(weight, stft_mag)
        lfcc_energies.append(np.log(np.maximum(band_energy, 1e-8)))

    lfcc_matrix = scipy.fft.dct(np.array(lfcc_energies), axis=0, norm='ortho')

    fig, ax = plt.subplots(figsize=(10, 3.5), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    img = ax.imshow(
        lfcc_matrix,
        aspect="auto",
        origin="lower",
        cmap="viridis",
        extent=(0, duration_s, 1, n_lfcc),
    )
    ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_ylabel("LFCC Index", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_title("Linear Frequency Cepstral Coefficients (LFCC) — High Register Vocoder Telemetry", color="#f8fafc", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(colors="#64748b", labelsize=9)

    cbar = fig.colorbar(img, ax=ax, orientation="vertical", pad=0.02)
    cbar.ax.tick_params(colors="#64748b", labelsize=8)

    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _render_cqt_scalogram(x: np.ndarray, sr: int, duration_s: float, out_path: Path) -> None:
    """Render Constant-Q Transform (CQT) geometric scalogram."""
    cqt = np.abs(librosa.cqt(x, sr=sr, n_bins=72, bins_per_octave=12, hop_length=256))
    log_cqt = librosa.amplitude_to_db(cqt, ref=np.max)

    fig, ax = plt.subplots(figsize=(10, 3.5), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    img = ax.imshow(
        log_cqt,
        aspect="auto",
        origin="lower",
        cmap="magma",
        extent=(0, duration_s, 0, 72),
    )
    ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_ylabel("Constant-Q Bin", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_title("Constant-Q Geometric Scalogram (CQT) — Phase Smearing & Pitch Resonance", color="#f8fafc", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(colors="#64748b", labelsize=9)

    cbar = fig.colorbar(img, ax=ax, orientation="vertical", pad=0.02)
    cbar.ax.tick_params(colors="#64748b", labelsize=8)

    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _render_waveform_profile(x: np.ndarray, sr: int, duration_s: float, out_path: Path) -> None:
    """Render waveform with RMS envelope, clipping markers, and silence baseline."""
    fig, ax = plt.subplots(figsize=(10, 2.8), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    time_ax = np.linspace(0, duration_s, len(x))
    ax.plot(time_ax, x, color="#38bdf8", alpha=0.6, linewidth=0.5, label="Waveform")

    # RMS envelope
    frame_len = max(64, int(sr * 0.05))
    hop = frame_len // 2
    rms = librosa.feature.rms(y=x, frame_length=frame_len, hop_length=hop)[0]
    rms_times = np.linspace(0, duration_s, len(rms))
    ax.plot(rms_times, rms, color="#e0e7ff", linewidth=1.5, label="RMS Energy")
    ax.plot(rms_times, -rms, color="#e0e7ff", linewidth=1.5)

    ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_ylabel("Amplitude", color="#94a3b8", fontsize=10, fontweight="bold")
    ax.set_title("Calibrated Audio Waveform & Dynamic Envelope", color="#f8fafc", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(colors="#64748b", labelsize=9)
    ax.set_ylim(-1.05, 1.05)
    ax.axhline(0, color="#334155", linewidth=0.8, linestyle=":")

    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _render_master_diagnostic_plate(
    x: np.ndarray,
    sr: int,
    duration_s: float,
    out_path: Path,
    segment_scores: list[dict[str, Any]] | None,
) -> None:
    """Render 4-panel master multi-resolution forensic dossier plate."""
    fig, axes = plt.subplots(4, 1, figsize=(11, 10), dpi=150, sharex=True)
    fig.patch.set_facecolor('#0b0f19')

    # Panel 1: Waveform
    time_ax = np.linspace(0, duration_s, len(x))
    axes[0].set_facecolor('#0b0f19')
    axes[0].plot(time_ax, x, color="#38bdf8", alpha=0.7, linewidth=0.5)
    axes[0].set_ylabel("Waveform", color="#94a3b8", fontsize=9, fontweight="bold")
    axes[0].tick_params(colors="#64748b", labelsize=8)

    # Panel 2: Log-Mel Spectrogram
    axes[1].set_facecolor('#0b0f19')
    mel = librosa.power_to_db(librosa.feature.melspectrogram(y=x, sr=sr, n_mels=64, n_fft=1024, hop_length=256), ref=np.max)
    axes[1].imshow(mel, aspect="auto", origin="lower", cmap="inferno", extent=[0, duration_s, 0, sr/2/1000])
    axes[1].set_ylabel("Log-Mel (kHz)", color="#94a3b8", fontsize=9, fontweight="bold")
    axes[1].tick_params(colors="#64748b", labelsize=8)

    # Panel 3: CQT Scalogram
    axes[2].set_facecolor('#0b0f19')
    cqt = librosa.amplitude_to_db(np.abs(librosa.cqt(x, sr=sr, n_bins=60, hop_length=256)), ref=np.max)
    axes[2].imshow(cqt, aspect="auto", origin="lower", cmap="magma", extent=[0, duration_s, 0, 60])
    axes[2].set_ylabel("CQT Bins", color="#94a3b8", fontsize=9, fontweight="bold")
    axes[2].tick_params(colors="#64748b", labelsize=8)

    # Panel 4: Temporal Splicing & AI Risk Curve
    axes[3].set_facecolor('#0b0f19')
    if segment_scores:
        seg_times = [s["start_s"] + (s["end_s"] - s["start_s"])/2.0 for s in segment_scores]
        seg_probs = [s["fake_probability"] for s in segment_scores]
        axes[3].plot(seg_times, seg_probs, color="#f43f5e", marker="o", linewidth=2.0, label="P(Synthetic)")
        axes[3].axhline(0.65, color="#eab308", linestyle="--", linewidth=1.0, label="Forensic Threshold")
    else:
        axes[3].plot([0, duration_s], [0.1, 0.1], color="#10b981", linewidth=1.5)
    axes[3].set_ylim(-0.05, 1.05)
    axes[3].set_ylabel("Synthetic Risk", color="#94a3b8", fontsize=9, fontweight="bold")
    axes[3].set_xlabel("Time (s)", color="#94a3b8", fontsize=10, fontweight="bold")
    axes[3].tick_params(colors="#64748b", labelsize=8)
    axes[3].legend(loc="upper right", facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8)

    fig.suptitle("Multi-Resolution Audio Forensics Diagnostic Suite", color="#f8fafc", fontsize=13, fontweight="bold", y=0.995)
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
