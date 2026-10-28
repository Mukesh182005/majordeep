"""TruFor image forgery detection and localisation (pretrained, inference only).

Guillaro, Cozzolino, Sud, Dufour and Verdoliva, "TruFor: Leveraging all-round
clues for trustworthy image forgery detection and localization", CVPR 2023.
Model code: ``app/ml/trufor_vendor`` (GRIP-UNINA licence: informational and
nonprofit use only; see its README). Weights: ``TruFor_weights.zip`` from
GRIP-UNINA, downloaded on first use and checked against a pinned SHA-256.

TruFor looks for local edits (splicing, copy-move, inpainting) rather than
whole-image generation. Per image it returns:

* ``score``: whole-image integrity score, P(manipulated) from the detection head;
* a localisation map, P(manipulated) per pixel;
* a confidence map: where the localisation can be trusted.

Input exactly as the authors' ``data_core.py``: RGB as float, divided by 256,
the model applies its own ImageNet normalisation. Images whose long side
exceeds ``settings.trufor_max_side`` are downscaled first to bound GPU memory,
which the authors do not do; this is recorded on every result.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import settings
from app.ml.base import resolve_device

logger = logging.getLogger(__name__)

WEIGHTS_URL = "https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip"
WEIGHTS_SHA256 = "ac1d90e329a72e0d66e8665e123a19e94bfae3209c3ef8a4f9ca3b91578c7844"  # trufor.pth.tar
CITATION = "Guillaro et al., TruFor, CVPR 2023 (GRIP-UNINA; nonprofit use only)"

_MODEL: LoadedTruFor | None = None
_FAILED = False
_LOCK = threading.Lock()


@dataclass
class LoadedTruFor:
    module: Any
    device: str
    weights: Path


def _config():
    """The authors' test configuration (test_docker/src/trufor.yaml), without a YAML file."""
    from yacs.config import CfgNode as CN

    c = CN()
    c.MODEL = CN()
    c.MODEL.NAME = "detconfcmx"
    c.MODEL.PRETRAINED = ""
    c.MODEL.MODS = ("RGB", "NP++")
    c.MODEL.EXTRA = CN(new_allowed=True)
    c.MODEL.EXTRA.BACKBONE = "mit_b2"
    c.MODEL.EXTRA.DECODER = "MLPDecoder"
    c.MODEL.EXTRA.DECODER_EMBED_DIM = 512
    c.MODEL.EXTRA.PREPRC = "imagenet"
    c.MODEL.EXTRA.BN_EPS = 0.001
    c.MODEL.EXTRA.BN_MOMENTUM = 0.1
    c.MODEL.EXTRA.DETECTION = "confpool"
    c.MODEL.EXTRA.CONF = True
    c.DATASET = CN()
    c.DATASET.NUM_CLASSES = 2
    c.freeze()
    return c


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weights_path() -> Path:
    """``settings.trufor_weights`` if set, else the cached download (fetched once)."""
    if settings.trufor_weights:
        return Path(settings.trufor_weights)
    cache = Path(settings.trufor_cache_dir)
    target = cache / "trufor.pth.tar"
    if target.is_file():
        return target
    import urllib.request

    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "TruFor_weights.zip"
    logger.info("Downloading TruFor weights from %s", WEIGHTS_URL)
    urllib.request.urlretrieve(WEIGHTS_URL, archive)  # nosec B310 - fixed https URL, hash checked below
    with zipfile.ZipFile(archive) as z:
        member = next(n for n in z.namelist() if n.endswith("trufor.pth.tar"))
        target.write_bytes(z.read(member))
    archive.unlink()
    return target


def _load_state_dict(path: Path) -> dict:
    """Restricted (weights_only) load; the file also holds a NumPy scalar and dtype, which are allowlisted."""
    import torch

    numpy_globals = [np.dtype, type(np.dtype("float64"))]
    try:
        from numpy.core.multiarray import scalar
    except ImportError:  # NumPy 2
        from numpy._core.multiarray import scalar
    numpy_globals.append(scalar)
    with torch.serialization.safe_globals(numpy_globals):
        payload = torch.load(path, map_location="cpu", weights_only=True)
    return payload["state_dict"]


def get_trufor() -> LoadedTruFor | None:
    """Load TruFor once per process; ``None`` (with an error logged once) if it cannot load."""
    global _MODEL, _FAILED
    if _MODEL is not None or _FAILED or not settings.trufor_enabled:
        return _MODEL
    with _LOCK:
        if _MODEL is None and not _FAILED:
            try:
                path = weights_path()
                digest = _sha256(path)
                if digest != WEIGHTS_SHA256:
                    raise ValueError(f"{path.name} sha256 {digest[:12]} does not match the pinned weights")
                from app.ml.trufor_vendor.cmx.builder_np_conf import myEncoderDecoder

                model = myEncoderDecoder(cfg=_config())
                model.load_state_dict(_load_state_dict(path), strict=True)
                device = resolve_device()
                _MODEL = LoadedTruFor(model.float().eval().to(device), device, path)
                logger.info("Loaded TruFor from %s on %s", path, device)
            except Exception as exc:
                _FAILED = True
                logger.error("TruFor unavailable: %s", exc)
    return _MODEL


def _input_tensor(image: Image.Image, max_side: int):
    import torch

    rgb = image.convert("RGB")
    w, h = rgb.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        rgb = rgb.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BICUBIC)
    arr = np.asarray(rgb, dtype=np.float32).transpose(2, 0, 1) / 256.0
    return torch.from_numpy(arr).unsqueeze(0), rgb, scale


def analyze(image: Image.Image, heatmap_path: Path | None = None, loaded: LoadedTruFor | None = None) -> dict | None:
    """Integrity score, localisation summary and (optionally) a heatmap overlay; ``None`` if unavailable."""
    import torch
    from torch.nn import functional as F

    loaded = loaded or get_trufor()
    if loaded is None:
        return None
    tensor, resized, scale = _input_tensor(image, settings.trufor_max_side)
    with torch.inference_mode(), torch.autocast(device_type=torch.device(loaded.device).type, enabled=False):
        pred, conf, det, _ = loaded.module(tensor.to(loaded.device, dtype=torch.float32))
        score = float(torch.sigmoid(det).item())
        heat = F.softmax(pred.squeeze(0), dim=0)[1].float().cpu().numpy()
        reliability = torch.sigmoid(conf.squeeze(0))[0].float().cpu().numpy()
    if not math.isfinite(score):
        return None
    mask = heat >= 0.5
    result: dict[str, Any] = {
        "score": round(score, 4),
        "manipulated_area_fraction": round(float(mask.mean()), 4),
        "mean_localisation": round(float(heat.mean()), 4),
        "mean_confidence": round(float(reliability.mean()), 4),
        "analysed_size": list(resized.size),
        "downscaled": scale < 1.0,
        "model": "TruFor (CVPR 2023)",
        "citation": CITATION,
        "heatmap_file": None,
    }
    if mask.any():
        ys, xs = np.where(mask)
        inv = 1.0 / scale
        result["region_box"] = [int(xs.min() * inv), int(ys.min() * inv), int((xs.max() + 1) * inv), int((ys.max() + 1) * inv)]
    if heatmap_path is not None:
        from app.ml.gradcam import overlay_heatmap

        overlay_heatmap(resized, heat, heatmap_path)
        result["heatmap_file"] = Path(heatmap_path).name
    return result
