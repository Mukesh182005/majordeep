"""Test fixtures: an isolated database and storage tree per test session.

The environment is configured at import time, before ``app.config`` is imported
anywhere. Settings are read once at import and cached, so setting them from
inside a fixture would be too late — the app would already have opened the
developer's real database.
"""

from __future__ import annotations

import io
import math
import os
import struct
import tempfile
import wave
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="deepfake-test-"))

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{TEST_ROOT / 'test.db'}",
        "STORAGE_DIR": str(TEST_ROOT / "uploads"),
        "EVIDENCE_DIR": str(TEST_ROOT / "evidence"),
        "REPORT_DIR": str(TEST_ROOT / "reports"),
        "CHECKPOINT_DIR": str(TEST_ROOT / "checkpoints"),
        "CELERY_BROKER_URL": "",  # eager mode: no Redis needed
        "CELERY_RESULT_BACKEND": "",
        "JWT_SECRET_KEY": "test-secret-key-not-for-production",
        "MAX_UPLOAD_MB": "5",
        "UPLOAD_RATE_LIMIT_PER_HOUR": "50",
        "GUEST_RATE_LIMIT_PER_HOUR": "50",
        # The default audio model stage is the ASVspoof LCNN, whose weights are
        # never committed. Tests use a random-weight LCNN with a matching
        # calibration and frozen verdict config (written by _test_audio_lcnn):
        # they check the wiring, not accuracy.
        "AUDIO_MODEL_SOURCE": "lcnn_asvspoof",
        "AUDIO_LCNN_CALIBRATION_FILE": str(TEST_ROOT / "config" / "audio_calibration.json"),
        "AUDIO_VERDICT_CONFIG_FILE": str(TEST_ROOT / "config" / "frozen_audio_config.json"),
        # TruFor's weights (260 MB) are downloaded on first use; tests stub it (tests/test_trufor.py).
        "TRUFOR_ENABLED": "false",
        # pellav2 weights are 2.3 GB; tests that need it enable it with a tiny model
        # (tests/test_audio_pellav2.py).
        "AUDIO_PELLAV2_ENABLED": "false",
        "AUDIO_PELLAV2_CONFIG_FILE": str(TEST_ROOT / "config" / "pellav2_verdict_config.json"),
    }
)


@pytest.fixture(scope="session")
def test_root() -> Path:
    """Root of this session's isolated storage tree."""
    return TEST_ROOT


def write_test_audio_lcnn(checkpoint_dir: Path, config_dir: Path, seed: int = 0, name: str = "audio_lcnn_test.pt") -> dict:
    """A random-weight LCNN checkpoint, a calibration naming it, and a frozen verdict config for it."""
    import hashlib
    import json

    import torch

    from app.ml.models_arch import build_audio_model

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    checkpoint = checkpoint_dir / name
    torch.save({"state_dict": build_audio_model().state_dict(), "frontend": "lfcc",
                "model_version": f"audio-lcnn-test-seed{seed}"}, checkpoint)
    sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    calibration = {"checkpoint": f"checkpoints/{name}", "checkpoint_sha256": sha, "frontend": "lfcc",
                   "method": "platt_balanced", "a": 0.8, "b": 0.1}
    threshold, band = 0.5, 0.08
    frozen = {"checkpoint": calibration["checkpoint"], "checkpoint_sha256": sha, "threshold": threshold,
              "inconclusive_band": band, "authentic_below": threshold - band, "flagged_at_or_above": threshold + band,
              "decision_rule": "test rule: LCNN probability against 0.42 / 0.58"}
    (config_dir / "audio_calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
    (config_dir / "frozen_audio_config.json").write_text(json.dumps(frozen), encoding="utf-8")
    return {"calibration": calibration, "frozen": frozen, "checkpoint": checkpoint}


@pytest.fixture(scope="session", autouse=True)
def _test_audio_lcnn():
    """Put the random-weight test LCNN where the session's settings point."""
    try:
        import torch  # noqa: F401
    except ImportError:  # pragma: no cover - the ml-marked tests skip themselves
        return None
    return write_test_audio_lcnn(TEST_ROOT / "checkpoints", TEST_ROOT / "config")


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_root():
    yield
    import shutil

    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    """FastAPI test client with the app's lifespan (and table creation) run."""
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _anonymous_client_by_default(request):
    """The shared client must not carry a login cookie set by an earlier test.

    Login sets an httpOnly session cookie, and the session-scoped TestClient
    keeps cookies, so without this every request after any login would be
    authenticated. Tests that exercise the cookie set it themselves.
    """
    if "client" in request.fixturenames:
        request.getfixturevalue("client").cookies.clear()
    yield


@pytest.fixture
def auth_headers(client):
    """Register a fresh user and return its Authorization header (no cookie kept)."""
    import uuid

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse-battery", "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def png_bytes() -> bytes:
    """A small valid PNG."""
    pytest.importorskip("PIL")
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (128, 128), (120, 90, 70)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(scope="session")
def wav_bytes() -> bytes:
    """A 2-second 16 kHz mono PCM WAV containing a 440 Hz tone."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(
            b"".join(
                struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440 * i / 16000)))
                for i in range(32000)
            )
        )
    return buffer.getvalue()


@pytest.fixture
def torch_available() -> bool:
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def requires_torch():
    """Skip marker for tests that need the inference stack installed."""
    return pytest.mark.skipif(
        __import__("importlib").util.find_spec("torch") is None,
        reason="PyTorch is not installed (pip install -r requirements-ml.txt)",
    )


@pytest.fixture(scope="session")
def face_photo():
    """A real photograph containing a detectable face.

    scikit-image bundles this sample, so the face-detection path can be tested
    without shipping a photo of a real person in this repository.
    """
    skimage_data = pytest.importorskip("skimage.data", reason="scikit-image not installed")
    from PIL import Image

    return Image.fromarray(skimage_data.astronaut())


@pytest.fixture(scope="session")
def face_photo_bytes(face_photo) -> bytes:
    buffer = io.BytesIO()
    face_photo.save(buffer, format="PNG")
    return buffer.getvalue()
