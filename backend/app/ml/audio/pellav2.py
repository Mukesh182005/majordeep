"""pellav2: a pretrained audio deepfake detector (inference only, nothing trained here).

Source: Hugging Face ``Sadanie/pellav2-audio-deepfake-detector`` (MIT licence),
pinned to revision ``HUB_REVISION``. The architecture and the preprocessing are
copied from the authors' ``pellav2_infer.py`` at that revision:

* Backbone: ``transformers.Wav2Vec2BertModel`` with the ``facebook/w2v-bert-2.0``
  configuration. The checkpoint holds every backbone weight, so the backbone is
  built from its configuration and the whole state dict is loaded with
  ``strict=True``; the pretrained backbone weights are never downloaded.
* Head: softmax-weighted sum of all hidden states, mean over unpadded frames,
  ``nn.Linear(hidden_size, 1)``. sigmoid(logit) = P(fake).
* Features: 80-bin Kaldi filterbank (``torchaudio.compliance.kaldi.fbank`` with
  ``dither=0``, ``window_type="povey"``, other options at their defaults) on the
  waveform scaled by 32768, per-utterance mean/variance normalisation (``1e-7``
  added to the variance), consecutive frame pairs stacked to 160 dimensions.
  torchaudio has no build for the torch this project pins, so ``kaldi_fbank``
  below is a line-for-line port of that function for these options;
  tests/test_audio_pellav2.py checks it against torchaudio when it is installed.

Input contract: 16 kHz mono float32 (other rates are resampled). The authors'
clip preparation is applied: DC removal, a 2nd-order 20 Hz high-pass
(zero-phase), then for each 4 s (64,000-sample) window loudness normalisation
to -23 LUFS, clipping to [-1, 1] and zero padding to 64,000 samples.

One deliberate change: the authors score only the centre 4 s. Here every
consecutive 4 s window is scored, up to ``max_windows``; a final partial window
shorter than 1 s is dropped unless it is the only one. The clip score is the
mean of the window probabilities, and each window's probability is kept for
the timeline.

Inference is float32 (never half precision), TF32 off, deterministic cuDNN.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from app.ml.base import resolve_device
from app.ml.checkpoints import extract_state_dict, load_checkpoint

logger = logging.getLogger(__name__)

HUB_REPO = "Sadanie/pellav2-audio-deepfake-detector"
HUB_REVISION = "29daea8b04acf2d3f11d1d0da6b01c17fc8a1e4b"
WEIGHTS_FILENAME = "pellav2_detector.pt"
BACKBONE_ID = "facebook/w2v-bert-2.0"
MODEL_LABEL = "pellav2 (w2v-BERT 2.0)"

SAMPLE_RATE = 16000
WINDOW_SAMPLES = 4 * SAMPLE_RATE  # 64,000
MIN_TAIL_SAMPLES = SAMPLE_RATE  # a final partial window shorter than 1 s is dropped
TARGET_LUFS = -23.0

# Kaldi fbank options used by the authors (the rest are torchaudio defaults).
_FRAME_LENGTH = 400  # 25 ms
_FRAME_SHIFT = 160  # 10 ms
_PADDED_FRAME = 512  # next power of two
_PREEMPHASIS = 0.97
_NUM_MEL_BINS = 80
_LOW_FREQ = 20.0


def _mel_scale(freq: float) -> float:
    return 1127.0 * math.log(1.0 + freq / 700.0)


def _mel_scale_tensor(freq: torch.Tensor) -> torch.Tensor:
    return 1127.0 * torch.log(1.0 + freq / 700.0)


def _mel_banks(device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    """torchaudio.compliance.kaldi.get_mel_banks for 80 bins, 512-point FFT, 20 Hz to Nyquist, no VTLN."""
    num_fft_bins = _PADDED_FRAME // 2
    high_freq = 0.5 * SAMPLE_RATE
    fft_bin_width = SAMPLE_RATE / _PADDED_FRAME
    mel_low, mel_high = _mel_scale(_LOW_FREQ), _mel_scale(high_freq)
    delta = (mel_high - mel_low) / (_NUM_MEL_BINS + 1)
    b = torch.arange(_NUM_MEL_BINS).unsqueeze(1)
    left, center, right = mel_low + b * delta, mel_low + (b + 1.0) * delta, mel_low + (b + 2.0) * delta
    mel = _mel_scale_tensor(fft_bin_width * torch.arange(num_fft_bins)).unsqueeze(0)
    up = (mel - left) / (center - left)
    down = (right - mel) / (right - center)
    banks = torch.max(torch.zeros(1), torch.min(up, down))
    return nn.functional.pad(banks.to(device=device, dtype=dtype), (0, 1), mode="constant", value=0)


def kaldi_fbank(waveform: torch.Tensor) -> torch.Tensor:
    """Log mel filterbank of a 1-D waveform, as torchaudio's kaldi.fbank with the authors' options.

    Frames that do not fit (snip_edges) are dropped; a waveform shorter than one
    frame gives an empty (0, 80) result.
    """
    dtype, device = waveform.dtype, waveform.device
    n = waveform.numel()
    if n < _FRAME_LENGTH:
        return torch.empty(0, _NUM_MEL_BINS, dtype=dtype, device=device)
    m = 1 + (n - _FRAME_LENGTH) // _FRAME_SHIFT
    frames = waveform.as_strided((m, _FRAME_LENGTH), (_FRAME_SHIFT * waveform.stride(0), waveform.stride(0)))
    frames = frames - frames.mean(dim=1, keepdim=True)  # remove_dc_offset
    shifted = nn.functional.pad(frames.unsqueeze(0), (1, 0), mode="replicate").squeeze(0)
    frames = frames - _PREEMPHASIS * shifted[:, :-1]
    window = torch.hann_window(_FRAME_LENGTH, periodic=False, device=device, dtype=dtype).pow(0.85)  # povey
    frames = nn.functional.pad(frames * window.unsqueeze(0), (0, _PADDED_FRAME - _FRAME_LENGTH), mode="constant", value=0)
    power = torch.fft.rfft(frames).abs().pow(2.0)
    energies = torch.mm(power, _mel_banks(device, dtype).T)
    return torch.max(energies, torch.tensor(torch.finfo(torch.float).eps, device=device, dtype=dtype)).log()


class Detector(nn.Module):
    """The authors' model class. ``backbone_config`` defaults to the w2v-BERT 2.0 configuration."""

    def __init__(self, backbone_config=None):
        super().__init__()
        from transformers import Wav2Vec2BertConfig, Wav2Vec2BertModel

        config = backbone_config if backbone_config is not None else Wav2Vec2BertConfig.from_pretrained(BACKBONE_ID)
        self.backbone = Wav2Vec2BertModel(config)
        self.layer_weights = nn.Parameter(torch.zeros(self.backbone.config.num_hidden_layers + 1))
        self.head = nn.Linear(self.backbone.config.hidden_size, 1)

    @staticmethod
    def features(wav: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        feats, lens = [], []
        with torch.autocast(device_type=wav.device.type, enabled=False):
            for x in wav.float():
                nz = torch.nonzero(x).flatten()
                n_s = int(nz[-1]) + 1 if len(nz) else len(x)
                f = kaldi_fbank(x[: max(n_s, _FRAME_LENGTH)] * 32768.0)
                f = (f - f.mean(0, keepdim=True)) / torch.sqrt(f.var(0, keepdim=True) + 1e-7)
                n = f.shape[0] // 2 * 2
                feats.append(f[:n].reshape(n // 2, 160))
                lens.append(n // 2)
        frames = max(lens)
        out = torch.zeros(len(feats), frames, 160, device=wav.device)
        mask = torch.zeros(len(feats), frames, dtype=torch.long, device=wav.device)
        for i, (f, n) in enumerate(zip(feats, lens)):
            out[i, :n] = f
            mask[i, :n] = 1
        return out, mask

    def forward(self, wav: torch.Tensor) -> torch.Tensor:
        feats, mask = self.features(wav)
        hs = self.backbone(input_features=feats, attention_mask=mask, output_hidden_states=True).hidden_states
        w = torch.softmax(self.layer_weights, dim=0)
        h = torch.stack(hs).mul(w[:, None, None, None]).sum(0)
        m = mask[:, :, None].float()
        h = (h * m).sum(1) / m.sum(1).clamp(min=1)
        return self.head(h).squeeze(-1)


@dataclass
class LoadedPellav2:
    module: Detector
    device: str
    metadata: dict[str, Any] = field(default_factory=dict)


_cache: dict[str, LoadedPellav2 | None] = {}
_lock = threading.Lock()


def _resolve_weights(source: str | Path) -> Path:
    """A local weights file, a folder holding ``pellav2_detector.pt``, or the Hub repo id."""
    path = Path(source)
    if path.is_file():
        return path
    if path.is_dir():
        return path / WEIGHTS_FILENAME
    from huggingface_hub import hf_hub_download

    revision = HUB_REVISION if str(source) == HUB_REPO else None
    return Path(hf_hub_download(repo_id=str(source), filename=WEIGHTS_FILENAME, revision=revision))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def build_pellav2(source: str | Path, device: str | None = None, backbone_config=None) -> LoadedPellav2:
    """Load the detector from ``source`` (see ``_resolve_weights``); raises on any failure."""
    weights = _resolve_weights(source)
    state = extract_state_dict(load_checkpoint(weights))
    module = Detector(backbone_config)
    module.load_state_dict(state, strict=True)
    device = resolve_device(device)
    module = module.float().eval().to(device)
    metadata = {
        "source": str(source),
        "revision": HUB_REVISION if str(source) == HUB_REPO else None,
        "weights_file": weights.name,
        "weights_sha256": _sha256(weights),
        "backbone": BACKBONE_ID,
        "licence": "MIT",
    }
    logger.info("Loaded %s from %s on %s", MODEL_LABEL, weights, device)
    return LoadedPellav2(module=module, device=device, metadata=metadata)


def get_pellav2() -> LoadedPellav2 | None:
    """The detector, loaded once per process; ``None`` (logged) if it cannot be loaded."""
    from app.config import settings

    key = str(settings.audio_pellav2_model_id)
    if key in _cache:
        return _cache[key]
    with _lock:
        if key not in _cache:
            try:
                _cache[key] = build_pellav2(key)
            except Exception as exc:
                logger.error("Failed to load %s from %s: %s", MODEL_LABEL, key, exc)
                _cache[key] = None
    return _cache[key]


def load_pellav2_verdict_config(weights_sha256: str | None) -> dict[str, Any]:
    """The pellav2 verdict thresholds (``settings.audio_pellav2_config_file``).

    Written by scripts/eval_audio_detector.py from ASVspoof 2019 LA dev scores.
    Refused unless it was fixed for these exact weights.
    """
    import json

    from app.config import settings
    from app.ml.base import DetectorUnavailableError

    path = Path(settings.audio_pellav2_config_file)
    if not path.is_file():
        raise DetectorUnavailableError(f"pellav2 verdict config not found: {path} (run scripts/eval_audio_detector.py)")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("weights_sha256") != weights_sha256:
        raise DetectorUnavailableError(f"{path.name} was fixed for different pellav2 weights.")
    return config


def _loudness(x: np.ndarray) -> float:
    try:
        import pyloudnorm as pyln

        if len(x) >= int(0.4 * SAMPLE_RATE):
            value = pyln.Meter(SAMPLE_RATE).integrated_loudness(x.astype(np.float64))
            if np.isfinite(value):
                return float(value)
    except Exception:
        pass
    return float(20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9) - 0.691)


def _condition(waveform: np.ndarray, sample_rate: int) -> np.ndarray:
    """Mono 16 kHz float32 with the authors' DC removal and 20 Hz high-pass."""
    from scipy.signal import butter, sosfiltfilt

    wav = np.asarray(waveform, dtype=np.float32)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sample_rate != SAMPLE_RATE:
        import librosa

        wav = librosa.resample(wav, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
    wav = wav - wav.mean() if wav.size else wav
    if len(wav) > 3 * SAMPLE_RATE // 100:
        wav = sosfiltfilt(butter(2, 20.0, btype="highpass", fs=SAMPLE_RATE, output="sos"), wav)
    return wav.astype(np.float32)


def window_starts(num_samples: int, max_windows: int) -> list[int]:
    """Start sample of each scored window: consecutive 4 s windows, a >= 1 s tail, at least one window."""
    starts = list(range(0, num_samples - WINDOW_SAMPLES + 1, WINDOW_SAMPLES))
    tail = num_samples - len(starts) * WINDOW_SAMPLES
    if not starts or tail >= MIN_TAIL_SAMPLES:
        starts.append(len(starts) * WINDOW_SAMPLES)
    return starts[: max(1, int(max_windows))]


def prepare_windows(waveform: np.ndarray, sample_rate: int, max_windows: int) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """(windows, spans): each window loudness-normalised and zero-padded to 64,000 samples."""
    wav = _condition(waveform, sample_rate)
    windows, spans = [], []
    for start in window_starts(len(wav), max_windows):
        segment = wav[start : start + WINDOW_SAMPLES]
        spans.append((start / SAMPLE_RATE, (start + len(segment)) / SAMPLE_RATE))
        if len(segment):
            gain = float(np.clip(TARGET_LUFS - _loudness(segment), -40.0, 40.0))
            segment = np.clip(segment * 10 ** (gain / 20), -1.0, 1.0).astype(np.float32)
        if len(segment) < WINDOW_SAMPLES:
            segment = np.concatenate([segment, np.zeros(WINDOW_SAMPLES - len(segment), np.float32)])
        windows.append(segment)
    return np.stack(windows), spans


def _window_logits(loaded: LoadedPellav2, windows: np.ndarray) -> np.ndarray:
    batch = torch.from_numpy(windows).to(loaded.device, dtype=torch.float32)
    device_type = torch.device(loaded.device).type
    previous_tf32 = torch.backends.cuda.matmul.allow_tf32
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        with torch.inference_mode(), torch.autocast(device_type=device_type, enabled=False), \
                torch.backends.cudnn.flags(enabled=True, benchmark=False, deterministic=True, allow_tf32=False):
            logits = loaded.module(batch).float().cpu().numpy()
    finally:
        torch.backends.cuda.matmul.allow_tf32 = previous_tf32
    return np.atleast_1d(logits)


def score_windows(waveform: np.ndarray, sample_rate: int, max_windows: int, loaded: LoadedPellav2 | None = None) -> list[float]:
    """P(fake) of each window (see ``prepare_windows``); empty if the model is unavailable."""
    loaded = loaded or get_pellav2()
    if loaded is None:
        return []
    windows, _ = prepare_windows(waveform, sample_rate, max_windows)
    return [float(1.0 / (1.0 + np.exp(-v))) for v in _window_logits(loaded, windows)]


def score_clip(waveform: np.ndarray, sample_rate: int, max_windows: int, loaded: LoadedPellav2 | None = None) -> dict[str, Any] | None:
    """Clip score (mean of the window probabilities) with every window's score; ``None`` if unavailable."""
    loaded = loaded or get_pellav2()
    if loaded is None:
        return None
    windows, spans = prepare_windows(waveform, sample_rate, max_windows)
    logits = _window_logits(loaded, windows)
    probs = [float(1.0 / (1.0 + np.exp(-v))) for v in logits]
    if not all(math.isfinite(p) for p in probs):
        logger.error("%s returned a non-finite score; treated as unavailable.", MODEL_LABEL)
        return None
    total_s = len(np.asarray(waveform).reshape(-1)) / sample_rate if np.asarray(waveform).ndim == 1 else None
    return {
        "prob": float(np.mean(probs)),
        "max_prob": float(np.max(probs)),
        "window_probs": [round(p, 4) for p in probs],
        "window_logits": [round(float(v), 4) for v in logits],
        "windows": [
            {"index": i, "start_s": round(s, 3), "end_s": round(e, 3), "probability": round(p, 4)}
            for i, ((s, e), p) in enumerate(zip(spans, probs, strict=True))
        ],
        "n_windows": len(probs),
        "seconds_scored": round(spans[-1][1], 3),
        "clip_seconds": None if total_s is None else round(total_s, 3),
        "model": MODEL_LABEL,
        "metadata": loaded.metadata,
        "inference": "float32, TF32 off, deterministic cuDNN",
    }
