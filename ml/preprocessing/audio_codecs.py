"""Lossy re-encoding of speech for codec augmentation and codec robustness on dev.

Conditions are fixed in ``paper/config/audio_codec_plan.json`` before any
training or scoring that uses them. Each one encodes with the ffmpeg build
bundled with imageio-ffmpeg and decodes back to 16 kHz mono PCM with the same
ffmpeg, so the result does not depend on which decoders libsndfile has. The
decoded waveform is cut or zero-padded to the original length (codecs add a
few milliseconds of delay and padding), so its 4 s windows line up with the
original's and the feature cache keeps the manifest's window counts.

Resampling conditions (plan v2) take the 16 kHz file up to another rate and
back down, as the application does to every upload recorded at another rate:
with soxr (``librosa.resample``, the path of ``load_audio``) or with ffmpeg's
resampler (the path of a video's audio track).

A condition is assigned to an utterance from a hash of its id and a seed, so
the assignment does not depend on the order of the manifest.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000

# name -> (container suffix, ffmpeg encoder arguments)
CODEC_CONDITIONS: dict[str, tuple[str, list[str]]] = {
    "mp3_32k": (".mp3", ["-c:a", "libmp3lame", "-b:a", "32k"]),
    "mp3_64k": (".mp3", ["-c:a", "libmp3lame", "-b:a", "64k"]),
    "mp3_96k": (".mp3", ["-c:a", "libmp3lame", "-b:a", "96k"]),
    "mp3_128k": (".mp3", ["-c:a", "libmp3lame", "-b:a", "128k"]),
    "aac_32k": (".m4a", ["-c:a", "aac", "-b:a", "32k"]),
    "aac_64k": (".m4a", ["-c:a", "aac", "-b:a", "64k"]),
    "aac_96k": (".m4a", ["-c:a", "aac", "-b:a", "96k"]),
    "opus_16k": (".ogg", ["-c:a", "libopus", "-b:a", "16k"]),
    "opus_24k": (".ogg", ["-c:a", "libopus", "-b:a", "24k"]),
    "opus_32k": (".ogg", ["-c:a", "libopus", "-b:a", "32k"]),
    "opus_48k": (".ogg", ["-c:a", "libopus", "-b:a", "48k"]),
}


# name -> (intermediate rate, resampler)
RESAMPLE_CONDITIONS: dict[str, tuple[int, str]] = {
    "resample_22k": (22050, "soxr"),
    "resample_44k": (44100, "soxr"),
    "resample_48k": (48000, "soxr"),
    "resample_48k_ffmpeg": (48000, "ffmpeg"),
}
ALL_CONDITIONS: list[str] = [*CODEC_CONDITIONS, *RESAMPLE_CONDITIONS]


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def assign_condition(utt_id: str, seed: int, conditions: list[str]) -> str:
    """The condition of one utterance: a stable hash of (seed, utt_id) picks it."""
    digest = hashlib.sha256(f"{seed}:{utt_id}".encode()).digest()
    return conditions[int.from_bytes(digest[:8], "big") % len(conditions)]


def fit_length(waveform: np.ndarray, num_samples: int) -> np.ndarray:
    if waveform.size >= num_samples:
        return waveform[:num_samples]
    return np.concatenate([waveform, np.zeros(num_samples - waveform.size, dtype=waveform.dtype)])


def encode_decode(source: Path, condition: str, num_samples: int | None = None, exe: str | None = None,
                  workdir: Path | None = None) -> np.ndarray:
    """``source`` re-encoded (or resampled) with ``condition`` and decoded to float32 16 kHz mono."""
    import soundfile as sf

    if condition in RESAMPLE_CONDITIONS:
        waveform = resample_round_trip(source, condition, exe, workdir)
        return fit_length(waveform, num_samples) if num_samples is not None else waveform
    suffix, args = CODEC_CONDITIONS[condition]
    exe = exe or ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="ds-codec-", dir=workdir) as tmp:
        encoded, decoded = Path(tmp) / f"x{suffix}", Path(tmp) / "x.wav"
        common = [exe, "-nostdin", "-v", "error", "-y"]
        subprocess.run([*common, "-i", str(source), *args, str(encoded)], check=True, capture_output=True,
                       timeout=120)
        subprocess.run([*common, "-i", str(encoded), "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
                        str(decoded)], check=True, capture_output=True, timeout=120)
        waveform, rate = sf.read(str(decoded), dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"decoded at {rate} Hz")
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    return fit_length(waveform, num_samples) if num_samples is not None else waveform


def resample_round_trip(source: Path, condition: str, exe: str | None = None, workdir: Path | None = None) -> np.ndarray:
    """16 kHz -> the condition's rate -> 16 kHz, with soxr or with ffmpeg."""
    import soundfile as sf

    rate, resampler = RESAMPLE_CONDITIONS[condition]
    if resampler == "soxr":
        import librosa

        waveform, sr = sf.read(str(source), dtype="float32", always_2d=False)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        up = librosa.resample(waveform, orig_sr=sr, target_sr=rate, res_type="soxr_hq")
        return librosa.resample(up, orig_sr=rate, target_sr=SAMPLE_RATE, res_type="soxr_hq").astype(np.float32)
    exe = exe or ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="ds-resample-", dir=workdir) as tmp:
        up, down = Path(tmp) / "up.wav", Path(tmp) / "down.wav"
        common = [exe, "-nostdin", "-v", "error", "-y"]
        subprocess.run([*common, "-i", str(source), "-ar", str(rate), "-c:a", "pcm_s16le", str(up)],
                       check=True, capture_output=True, timeout=120)
        subprocess.run([*common, "-i", str(up), "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(down)],
                       check=True, capture_output=True, timeout=120)
        waveform, _ = sf.read(str(down), dtype="float32", always_2d=False)
    return waveform.mean(axis=1) if waveform.ndim > 1 else waveform
