"""CNNDetection baseline: S.-Y. Wang, O. Wang, R. Zhang, A. Owens and A. A. Efros,
"CNN-generated images are surprisingly easy to spot... for now", CVPR 2020.

Official code: https://github.com/PeterWang512/CNNDetection (CC BY-NC-SA 4.0),
cloned to ``$DEEPSENTINEL_DATA/baselines/CNNDetection``; weights from
``weights/download_weights.sh`` (``blur_jpg_prob0.5.pth``, the model the
repository's ``demo.py`` uses by default).

Reproduces the official single-image path (``demo.py``):

* preprocessing: no crop (the ``demo.py`` default and the README's
  recommended "uncropped" evaluation), ``ToTensor``, ``Normalize`` with the
  ImageNet mean and std;
* model: ``networks.resnet.resnet50(num_classes=1)`` with ``state_dict['model']``;
  output ``sigmoid`` = probability of being synthetic. Float32 throughout.

Pass ``crop=224`` to reproduce the paper's centre-crop setting instead.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ml.evaluation.baselines._loading import load_module

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def load_cnndetection(
    root: Path,
    weights: str = "blur_jpg_prob0.5.pth",
    crop: int | None = None,
    device: str | None = None,
) -> Callable[[Path], float]:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image

    repo = root / "CNNDetection"
    resnet = load_module("cnndetection_resnet", repo / "networks/resnet.py")
    model = resnet.resnet50(num_classes=1)
    state = torch.load(repo / "weights" / weights, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = model.float().to(device).eval()

    steps = [transforms.CenterCrop(crop)] if crop is not None else []
    transform = transforms.Compose([
        *steps,
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    def score(path: Path) -> float:
        with Image.open(path) as opened:
            tensor = transform(opened.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            return float(model(tensor).sigmoid().item())

    return score
