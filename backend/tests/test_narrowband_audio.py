"""Phone-quality (narrowband) audio is detected and noted; the verdict guard is off by default."""

from __future__ import annotations

import numpy as np

from app.ml.audio.codec_guard import NARROWBAND_CUTOFF_DB, high_band_db

SR = 16000


def _noise_speech(seconds: float = 3.0, lowpass_hz: float | None = None) -> np.ndarray:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(int(seconds * SR))
    if lowpass_hz is not None:
        spec = np.fft.rfft(x)
        spec[np.fft.rfftfreq(x.size, 1 / SR) > lowpass_hz] = 0
        x = np.fft.irfft(spec, n=x.size)
    return x.astype(np.float32)


def test_wideband_audio_is_not_narrowband():
    assert high_band_db(_noise_speech(), SR) > NARROWBAND_CUTOFF_DB


def test_audio_cut_at_4_khz_is_narrowband():
    assert high_band_db(_noise_speech(lowpass_hz=3800), SR) < NARROWBAND_CUTOFF_DB


def test_too_short_or_low_rate_audio_is_not_judged():
    assert high_band_db(np.zeros(100, np.float32), SR) is None
    assert high_band_db(_noise_speech(), 8000) is None


def test_the_verdict_guard_is_off_by_default():
    from app.config import settings

    assert settings.audio_narrowband_guard is False
