"""UnivFD baseline: U. Ojha, Y. Li and Y. J. Lee, "Towards Universal Fake Image
Detectors that Generalize Across Generative Models", CVPR 2023.

Official code: https://github.com/WisconsinAIVision/UniversalFakeDetect (MIT),
cloned to ``$DEEPSENTINEL_DATA/baselines/UniversalFakeDetect``.

Reproduces the official evaluation path (``validate.py`` and
``models/clip_models.py``):

* preprocessing: ``CenterCrop(224)``, ``ToTensor``, ``Normalize`` with the CLIP
  mean and std (no resizing);
* backbone: CLIP ViT-L/14 loaded with the repository's own ``clip.load`` on the
  CPU, which keeps it in float32 (weights checked against OpenAI's published
  sha256 by that loader), then moved to the GPU;
* head: ``nn.Linear(768, 1)`` with ``pretrained_weights/fc_weights.pth``;
  output ``sigmoid(fc(encode_image(x)))`` = P(fake).

The vendored CLIP code imports ``ftfy`` for text tokenisation only; when that
package is absent it is replaced by a stub that raises if ever called.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ml.evaluation.baselines._loading import load_module, stub_text_only_dependency

CLIP_MEAN = [0.48145466, 0.4578275, 0.40821073]
CLIP_STD = [0.26862954, 0.26130258, 0.27577711]
FEATURE_DIM = 768  # ViT-L/14 image embedding (CHANNELS["ViT-L/14"] in clip_models.py)


def load_univfd(root: Path, device: str | None = None) -> Callable[[Path], float]:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from PIL import Image

    repo = root / "UniversalFakeDetect"
    stub_text_only_dependency("ftfy")
    clip = load_module("univfd_clip", repo / "models/clip/__init__.py", repo / "models/clip")
    backbone, _ = clip.load("ViT-L/14", device="cpu", download_root=str(root / "clip_weights"))
    head = nn.Linear(FEATURE_DIM, 1)
    head.load_state_dict(torch.load(repo / "pretrained_weights/fc_weights.pth", map_location="cpu", weights_only=True))

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    backbone = backbone.float().to(device).eval()
    head = head.float().to(device).eval()
    transform = transforms.Compose([
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=CLIP_MEAN, std=CLIP_STD),
    ])

    def score(path: Path) -> float:
        with Image.open(path) as opened:
            tensor = transform(opened.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            logit = head(backbone.encode_image(tensor).float())
        return float(torch.sigmoid(logit).item())

    return score
