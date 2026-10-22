"""Front end of the ASVspoof-trained LCNN, shared by training and serving.

The selected Phase 2 model (``ml/evaluation/select_asvspoof_frontend.py``)
uses LFCC features. Training (``ml/preprocessing/asvspoof_features.py``)
imports these functions, so the service computes exactly the features the
model was trained and evaluated on.

* Windows: an utterance is cut into 4-second windows (64,000 samples at
  16 kHz). One of at most 4 s is repeated until it fills one window; a longer
  one gives consecutive non-overlapping windows from the start, plus a final
  window holding its last 4 s when a remainder is left.
* LFCC: 20 coefficients plus deltas and double deltas. 20 ms Hamming window
  (320 samples) zero-padded to a 512-point FFT, 10 ms hop, centred frames, 20
  triangular filters equally spaced from 0 to 8 kHz, natural log with a 1e-10
  floor, orthonormal DCT-II keeping c0..c19, deltas over a 3-frame window.
  Shape (60, 401) per window.
* Input: the waveform as read from the file at 16 kHz, **without** peak
  normalisation (training read files with soundfile and did not normalise;
  normalising shifts c0).
* Features were cached as float16 for training; ``utterance_lfcc`` rounds
  through float16 the same way.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000
WINDOW_SAMPLES = 64000  # 4 seconds
HOP = 160
N_FFT = 512
FRAMES_PER_WINDOW = 1 + WINDOW_SAMPLES // HOP  # 401 centred frames

LFCC_FILTERS = 20
LFCC_COEFFS = 20
LFCC_WIN = 320  # 20 ms
LFCC_DELTA_WIDTH = 3
LOG_FLOOR = 1e-10


def window_count(num_samples: int, window: int = WINDOW_SAMPLES) -> int:
    if num_samples <= 0:
        raise ValueError("empty utterance")
    if num_samples <= window:
        return 1
    return num_samples // window + (1 if num_samples % window else 0)


def utterance_windows(waveform: np.ndarray, window: int = WINDOW_SAMPLES) -> np.ndarray:
    """Cut one utterance into fixed-length windows, shape ``(n_windows, window)``."""
    waveform = np.asarray(waveform, dtype=np.float32).ravel()
    n = waveform.size
    if n == 0:
        raise ValueError("empty utterance")
    if n <= window:
        repeats = -(-window // n)  # ceiling division
        return np.tile(waveform, repeats)[:window][None, :]
    windows = [waveform[i * window : (i + 1) * window] for i in range(n // window)]
    if n % window:
        windows.append(waveform[-window:])
    return np.stack(windows)


def linear_filterbank(
    sample_rate: int = SAMPLE_RATE, n_fft: int = N_FFT, n_filters: int = LFCC_FILTERS
) -> np.ndarray:
    """Triangular filters with centres equally spaced in Hz, shape (n_filters, n_fft//2+1)."""
    fft_freqs = np.linspace(0.0, sample_rate / 2, n_fft // 2 + 1)
    edges = np.linspace(0.0, sample_rate / 2, n_filters + 2)
    bank = np.zeros((n_filters, fft_freqs.size), dtype=np.float64)
    for m in range(n_filters):
        left, centre, right = edges[m], edges[m + 1], edges[m + 2]
        rising = (fft_freqs - left) / (centre - left)
        falling = (right - fft_freqs) / (right - centre)
        bank[m] = np.maximum(0.0, np.minimum(rising, falling))
    return bank


_FILTERBANK = linear_filterbank()


def lfcc_features(window: np.ndarray) -> np.ndarray:
    import librosa
    from scipy.fft import dct

    spectrum = librosa.stft(
        window,
        n_fft=N_FFT,
        hop_length=HOP,
        win_length=LFCC_WIN,
        window="hamming",
        center=True,
        pad_mode="constant",
    )
    power = np.abs(spectrum) ** 2
    energies = _FILTERBANK @ power
    cepstra = dct(np.log(np.maximum(energies, LOG_FLOOR)), type=2, axis=0, norm="ortho")
    cepstra = cepstra[:LFCC_COEFFS]
    delta = librosa.feature.delta(cepstra, width=LFCC_DELTA_WIDTH, order=1)
    delta2 = librosa.feature.delta(cepstra, width=LFCC_DELTA_WIDTH, order=2)
    return np.concatenate([cepstra, delta, delta2]).astype(np.float32)


def utterance_lfcc(waveform: np.ndarray) -> np.ndarray:
    """LFCC of every window of a 16 kHz utterance, (n_windows, 60, 401) float32, rounded as cached."""
    features = np.stack([lfcc_features(w) for w in utterance_windows(waveform)])
    return features.astype(np.float16).astype(np.float32)
