"""CommForScorer against a reference built the authors' way, without downloading weights."""

from __future__ import annotations

import math

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
timm = pytest.importorskip("timm")
safetensors_torch = pytest.importorskip("safetensors.torch")
transforms = pytest.importorskip("torchvision.transforms")

from app.ml.commfor import WEIGHTS_FILENAME, CommForScorer  # noqa: E402


class _AuthorsModel(torch.nn.Module):
    """The authors' layout: the timm ViT wrapped as ``self.vit``, one-logit head."""

    def __init__(self) -> None:
        super().__init__()
        self.vit = timm.create_model("vit_small_patch16_384", pretrained=False)
        self.vit.head = torch.nn.Linear(384, 1)

    def forward(self, x):
        return self.vit(x)


# The authors' dataloader.get_transform(mode="test"), written out independently
# of app.ml.commfor so a drift in either one is caught.
_AUTHORS_TEST_TRANSFORM = transforms.Compose(
    [
        transforms.Resize(440),
        transforms.CenterCrop(384),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ]
)


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    """A reference model with perturbed weights, saved as ``<folder>/model.safetensors``."""
    torch.manual_seed(0)
    model = _AuthorsModel()
    with torch.no_grad():
        for param in model.parameters():
            param.add_(0.02 * torch.randn_like(param))
    model.eval()
    folder = tmp_path_factory.mktemp("commfor")
    state = {k: v.contiguous() for k, v in model.state_dict().items()}
    safetensors_torch.save_file(state, str(folder / WEIGHTS_FILENAME))
    return model, folder


@pytest.fixture(scope="module")
def scorer(reference):
    return CommForScorer(reference[1], device="cpu")


def _random_image(seed: int) -> Image.Image:
    pixels = np.random.default_rng(seed).integers(0, 256, (300, 500, 3), dtype=np.uint8)
    return Image.fromarray(pixels)


@pytest.mark.parametrize("seed", [1, 2])
def test_matches_reference_model(reference, scorer, seed):
    model, _ = reference
    image = _random_image(seed)
    with torch.inference_mode():
        expected = float(torch.sigmoid(model(_AUTHORS_TEST_TRANSFORM(image).unsqueeze(0))).item())
    assert scorer.fake_probability(image) == pytest.approx(expected, abs=1e-5)


def test_call_returns_real_and_fake_summing_to_one(scorer):
    predictions = scorer(_random_image(3), top_k=None)
    assert {item["label"] for item in predictions} == {"real", "fake"}
    assert math.isclose(sum(item["score"] for item in predictions), 1.0, abs_tol=1e-9)


def test_zero_weight_is_reported_but_not_fused(monkeypatch, scorer):
    import app.ml.image_pipeline as ip

    class _Fixed:
        def __call__(self, image, top_k=None):
            return [{"label": "real", "score": 0.9}, {"label": "fake", "score": 0.1}]

    detectors = [
        ip.LoadedSceneDetector(ip.SceneDetectorSpec("fixed", 1.0, "test"), _Fixed(), frozenset({"real"})),
        ip.LoadedSceneDetector(
            ip.SceneDetectorSpec("commfor-test", 0.0, "test", loader="commfor"), scorer, frozenset({"real"})
        ),
    ]
    monkeypatch.setattr(ip, "get_scene_detector", lambda: detectors)

    image = _random_image(4)
    scene = ip.score_scene(image)
    assert scene["model_scores"]["commfor-test"] == round(scorer.fake_probability(image), 4)
    assert scene["scene_ai_prob"] == pytest.approx(0.1, abs=1e-6)


def test_unexpected_key_fails_strict_load(reference, tmp_path):
    state = safetensors_torch.load_file(str(reference[1] / WEIGHTS_FILENAME))
    state["unexpected.weight"] = state["vit.head.bias"].clone()
    bad = tmp_path / WEIGHTS_FILENAME
    safetensors_torch.save_file(state, str(bad))
    with pytest.raises(RuntimeError):
        CommForScorer(bad, device="cpu")
