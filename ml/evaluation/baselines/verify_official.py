#!/usr/bin/env python3
"""Check that the baseline wrappers reproduce the official repositories' outputs.

* CNNDetection: runs the official ``demo.py`` (subprocess, its default settings)
  and our wrapper on the same files; ``demo.py`` prints two decimals.
* UnivFD: builds the official ``get_model("CLIP:ViT-L/14")`` with
  ``fc_weights.pth`` and the ``validate.py`` transform, and compares the
  sigmoid outputs with our wrapper's.

Usage (PowerShell)::

    python ml/evaluation/baselines/verify_official.py image1.png image2.jpg
"""

from __future__ import annotations

import functools
import subprocess
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ml.evaluation.baselines import baselines_root  # noqa: E402


def main(images: list[Path]) -> int:
    import torch
    import torchvision.transforms as T
    from PIL import Image

    from ml.evaluation.baselines.cnndetection import load_cnndetection
    from ml.evaluation.baselines.univfd import CLIP_MEAN, CLIP_STD, load_univfd

    root = baselines_root()
    worst = 0.0
    ours_cnn = load_cnndetection(root)
    print("CNNDetection: official demo.py vs wrapper")
    for image in images:
        out = subprocess.run(
            [sys.executable, "demo.py", "-f", str(image.resolve()), "-m", "weights/blur_jpg_prob0.5.pth"],
            cwd=root / "CNNDetection", capture_output=True, text=True,
        )
        official = [line for line in out.stdout.splitlines() if "probability" in line]
        official_pct = float(official[-1].split(":")[1].strip().rstrip("%")) if official else float("nan")
        ours_pct = round(ours_cnn(image) * 100, 2)
        worst = max(worst, abs(official_pct - ours_pct) / 100)
        print(f"  {image.name}: official {official_pct:.2f}% | wrapper {ours_pct:.2f}%")

    if "ftfy" not in sys.modules:
        sys.modules["ftfy"] = types.ModuleType("ftfy")  # text tokenisation only; unused here
    sys.path.insert(0, str(root / "UniversalFakeDetect"))
    import models.clip.clip as official_clip  # official repository code

    official_clip.load = functools.partial(official_clip.load, download_root=str(root / "clip_weights"))
    from models import get_model

    model = get_model("CLIP:ViT-L/14")
    model.fc.load_state_dict(torch.load(root / "UniversalFakeDetect/pretrained_weights/fc_weights.pth",
                                        map_location="cpu", weights_only=True))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.eval().to(device)
    transform = T.Compose([T.CenterCrop(224), T.ToTensor(), T.Normalize(CLIP_MEAN, CLIP_STD)])
    ours_uni = load_univfd(root)
    print("UnivFD: official get_model path vs wrapper")
    for image in images:
        with torch.no_grad(), Image.open(image) as opened:
            official = model(transform(opened.convert("RGB")).unsqueeze(0).to(device)).sigmoid().item()
        ours = ours_uni(image)
        worst = max(worst, abs(official - ours))
        print(f"  {image.name}: official {official:.6f} | wrapper {ours:.6f}")
    print(f"Largest absolute difference: {worst:.2e}")
    return 0 if worst < 1e-4 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: verify_official.py IMAGE [IMAGE ...]")
    raise SystemExit(main([Path(p) for p in sys.argv[1:]]))
