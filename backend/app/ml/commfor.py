"""Community Forensics AI-generated image detector (pretrained, inference only).

Park and Owens, "Community Forensics: Using Thousands of Generators to Train
Fake Image Detectors", CVPR 2025, arXiv:2411.04125. Code and weights are MIT
licensed; the weights are the authors' release on Hugging Face
(``OwensLab/commfor-model-384``). Nothing here is trained or fine-tuned.

The model is a timm ``vit_small_patch16_384`` with a single-logit head;
sigmoid(logit) is P(fake). Preprocessing follows the authors'
``dataloader.get_transform(mode="test")``: resize the short side to 440,
centre-crop 384, ImageNet normalisation.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import torch
from PIL import Image

from app.ml.base import resolve_device

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "OwensLab/commfor-model-384"
WEIGHTS_FILENAME = "model.safetensors"
ARCHITECTURE = "vit_small_patch16_384"
# The authors wrap the timm model as ``self.vit``, so every checkpoint key
# carries this prefix.
_KEY_PREFIX = "vit."

_RESIZE = 440
_CROP = 384
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)


def _resolve_weights(model_id: str | Path) -> Path:
    """A local weights file, a folder holding ``model.safetensors``, or a Hub repo id."""
    path = Path(model_id)
    if path.is_file():
        return path
    if path.is_dir():
        candidate = path / WEIGHTS_FILENAME
        if not candidate.is_file():
            raise FileNotFoundError(f"{candidate} not found")
        return candidate
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=str(model_id), filename=WEIGHTS_FILENAME))


def build_transform():
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize(_RESIZE),
            transforms.CenterCrop(_CROP),
            transforms.ToTensor(),
            transforms.Normalize(mean=_MEAN, std=_STD),
        ]
    )


class CommForScorer:
    """Scores an image with the Community Forensics ViT.

    ``__call__`` mimics a transformers image-classification pipeline, so the
    scorer can stand in wherever the scene detectors call ``pipe(image, top_k=None)``.
    """

    def __init__(self, model_id: str | Path = DEFAULT_MODEL_ID, device: str | None = None):
        import timm
        from safetensors.torch import load_file

        self.model_id = str(model_id)
        self.device = resolve_device(device)
        weights = _resolve_weights(model_id)

        state = load_file(str(weights), device="cpu")
        state = {k[len(_KEY_PREFIX):] if k.startswith(_KEY_PREFIX) else k: v for k, v in state.items()}
        model = timm.create_model(ARCHITECTURE, pretrained=False, num_classes=1)
        model.load_state_dict(state, strict=True)
        # float32 only: half precision produced NaN scores in the face model
        # (KNOWN_ISSUES), so it is not used here either.
        self.model = model.float().eval().to(self.device)
        self.transform = build_transform()
        logger.info("Loaded Community Forensics detector from %s on %s", weights, self.device)

    def fake_probability(self, image: Image.Image | str | Path) -> float | None:
        """P(fake) for ``image``, or ``None`` if the model output is not a number."""
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device, dtype=torch.float32)
        device_type = torch.device(self.device).type
        with torch.inference_mode(), torch.autocast(device_type=device_type, enabled=False):
            logit = self.model(tensor).float()
        probability = float(torch.sigmoid(logit).item())
        return probability if math.isfinite(probability) else None

    def __call__(self, image: Image.Image | str | Path, top_k: int | None = None) -> list[dict[str, float | str]]:
        """``[{"label": "real", ...}, {"label": "fake", ...}]``, like a transformers pipeline.

        With an integer ``top_k`` the ``top_k`` highest-scoring labels are
        returned, highest first. Raises ``ValueError`` on a non-finite score
        rather than returning NaN, so a caller that skips failed detectors
        never fuses a NaN.
        """
        p = self.fake_probability(image)
        if p is None:
            raise ValueError(f"{self.model_id} returned a non-finite score")
        predictions = [{"label": "real", "score": 1.0 - p}, {"label": "fake", "score": p}]
        if top_k is None:
            return predictions
        return sorted(predictions, key=lambda item: item["score"], reverse=True)[:top_k]
