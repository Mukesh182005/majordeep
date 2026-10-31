"""AI-generated video detector: CLIP frame features + a linear head trained here.

Method (a linear probe on frozen CLIP features, as in Ojha et al., "Towards Universal
Fake Image Detectors that Generalize Across Generative Models", CVPR 2023, applied to
video frames): the ``openai/clip-vit-large-patch14`` vision tower embeds
``settings.video_scene_frames`` evenly spaced frames of the frames the pipeline
already samples; the video feature is the mean and standard deviation of the
L2-normalised frame embeddings plus the mean change between consecutive frames.
A logistic-regression head (``ml/training/train_aivideo.py``) maps it to P(AI-generated).

The head, its feature scaling and its threshold (chosen on validation) live in
``<checkpoint_dir>/aivideo_clip/head.json``. Without that file the detector is off.
``video_features`` is shared by training and inference so both compute the same thing.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import settings
from app.ml.base import resolve_device

logger = logging.getLogger(__name__)

CLIP_ID = "openai/clip-vit-large-patch14"
CITATION = "Linear probe on CLIP ViT-L/14 features (Ojha et al., CVPR 2023), trained in this repo"

_ENCODER: Any = None
_HEAD: dict | None = None
_FAILED = False
_LOCK = threading.Lock()


def head_path() -> Path:
    return Path(settings.checkpoint_dir) / "aivideo_clip" / "head.json"


def get_encoder():
    """(processor, vision model) loaded once per process; ``None`` if it cannot load."""
    global _ENCODER, _FAILED
    if _ENCODER is not None or _FAILED:
        return _ENCODER
    with _LOCK:
        if _ENCODER is None and not _FAILED:
            try:
                from transformers import CLIPImageProcessor, CLIPVisionModel

                model = CLIPVisionModel.from_pretrained(CLIP_ID).float().eval().to(resolve_device())
                _ENCODER = (CLIPImageProcessor.from_pretrained(CLIP_ID), model)
            except Exception as exc:
                _FAILED = True
                logger.error("AI-video encoder unavailable: %s", exc)
    return _ENCODER


def get_head() -> dict | None:
    global _HEAD
    if _HEAD is None and head_path().exists():
        _HEAD = json.loads(head_path().read_text(encoding="utf-8"))
    return _HEAD


def frame_embeddings(frames: list[Image.Image]) -> np.ndarray | None:
    """L2-normalised CLIP embeddings, one row per frame."""
    import torch

    enc = get_encoder()
    if enc is None or not frames:
        return None
    processor, model = enc
    device = next(model.parameters()).device
    with torch.inference_mode(), torch.autocast(device_type=device.type, enabled=False):
        pixels = processor(images=[f.convert("RGB") for f in frames], return_tensors="pt")["pixel_values"]
        emb = model(pixel_values=pixels.to(device, dtype=torch.float32)).pooler_output.float().cpu().numpy()
    return emb / np.linalg.norm(emb, axis=1, keepdims=True).clip(1e-8)


def video_features(frames: list[Image.Image]) -> np.ndarray | None:
    """Mean, standard deviation and mean consecutive change of the frame embeddings."""
    emb = frame_embeddings(frames)
    if emb is None:
        return None
    diff = np.abs(np.diff(emb, axis=0)).mean(axis=0) if len(emb) > 1 else np.zeros(emb.shape[1], emb.dtype)
    return np.concatenate([emb.mean(axis=0), emb.std(axis=0), diff]).astype(np.float32)


def score_video_frames(frames: list[Image.Image]) -> dict | None:
    """``{"probability", "threshold"}`` or ``None`` when the head or encoder is missing."""
    head = get_head()
    if head is None:
        return None
    feat = video_features(frames)
    if feat is None:
        return None
    z = (feat - np.asarray(head["mean"], np.float32)) / np.asarray(head["scale"], np.float32)
    logit = float(z @ np.asarray(head["coef"], np.float32) + head["intercept"])
    return {"probability": float(1 / (1 + np.exp(-logit))), "threshold": float(head["threshold"])}
