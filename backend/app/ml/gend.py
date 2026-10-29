"""GenD face-swap deepfake detector (pretrained, inference only).

Yermakov et al., "Deepfake Detection that Generalizes Across Benchmarks", WACV 2026,
arXiv 2508.06248. Code: github.com/yermandy/GenD (MIT); model class vendored
unchanged in ``app/ml/video/gend_model.py``. Weights: Hugging Face
``settings.gend_model_id`` (default ``yermandy/GenD_CLIP_L_14``, MIT), which also
downloads the ``openai/clip-vit-large-patch14`` vision tower on first use.

Labels: ``softmax(logits)[:, 1]`` is P(fake), index 0 is real (the authors' ``app/run.py``).

Face crop: the authors crop 1.3 x the detector's box, square (``detector.py -s 1.3``).
``square_face_crop`` does the same around the MTCNN box (without the 25 % margin the
rest of the pipeline adds), padding with black where the square leaves the frame.
The authors align faces with RetinaFace landmarks; this pipeline does not.

Inference is float32.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from PIL import Image

from app.config import settings
from app.ml.base import resolve_device

logger = logging.getLogger(__name__)

CROP_SCALE = 1.3
CITATION = "Yermakov et al., GenD, WACV 2026 (MIT)"

_MODEL: Any = None
_FAILED = False
_LOCK = threading.Lock()


def get_gend():
    """The GenD model, loaded once per process; ``None`` (error logged once) if it cannot load."""
    global _MODEL, _FAILED
    if _MODEL is not None or _FAILED or not settings.gend_enabled:
        return _MODEL
    with _LOCK:
        if _MODEL is None and not _FAILED:
            try:
                from app.ml.video.gend_model import GenD

                model = GenD.from_pretrained(settings.gend_model_id)
                _MODEL = model.float().eval().to(resolve_device())
                logger.info("Loaded GenD %s on %s", settings.gend_model_id, resolve_device())
            except Exception as exc:
                _FAILED = True
                logger.error("GenD unavailable: %s", exc)
    return _MODEL


def square_face_crop(image: Image.Image, box: tuple[int, int, int, int], scale: float = CROP_SCALE) -> Image.Image:
    """Square crop centred on ``box`` with side ``scale * max(w, h)``; black where it leaves the image."""
    x1, y1, x2, y2 = box
    side = max(1, round(scale * max(x2 - x1, y2 - y1)))
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    left, top = round(cx - side / 2), round(cy - side / 2)
    # PIL pads with black outside the image when the crop box exceeds it.
    return image.convert("RGB").crop((left, top, left + side, top + side))


def score_faces(faces: list[Image.Image], batch_size: int = 16) -> list[float]:
    """P(fake) for each face crop, in order; ``[]`` if the model is unavailable or there are no faces."""
    import torch

    model = get_gend()
    if model is None or not faces:
        return []
    device = next(model.parameters()).device
    scores: list[float] = []
    with torch.inference_mode(), torch.autocast(device_type=device.type, enabled=False):
        for i in range(0, len(faces), batch_size):
            batch = torch.stack([model.feature_extractor.preprocess(f.convert("RGB")) for f in faces[i : i + batch_size]])
            logits = model(batch.to(device, dtype=torch.float32)).float()
            scores += [float(p) for p in logits.softmax(dim=-1)[:, 1].cpu()]
    return scores
