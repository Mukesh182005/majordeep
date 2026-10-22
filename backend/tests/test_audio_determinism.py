"""The same audio file scored in two fresh processes gives identical scores.

Each process loads the model from scratch and scores the clip through the
serving path (``load_audio`` then ``score_lcnn_asvspoof``) on the configured
device; the outputs must match exactly, not approximately. The session's
random-weight test LCNN is always checked; the real served checkpoint too when
it is present.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SR = 16000

SCORE_IN_FRESH_PROCESS = """
import json, sys
from app.ml.preprocessing import load_audio
from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
from app.ml.registry import get_audio_lcnn_asvspoof
waveform, rate = load_audio(sys.argv[1], 16000)
result = score_lcnn_asvspoof(waveform, rate)
print(json.dumps({"device": get_audio_lcnn_asvspoof().device, "mean": result["mean_spoof_logit"],
                  "probability": result["probability"],
                  "windows": [w["spoof_logit"] for w in result["windows"]]}))
"""


def _clip(path: Path) -> Path:
    import soundfile as sf

    rng = np.random.default_rng(7)
    t = np.arange(int(9.5 * SR)) / SR
    signal = 0.3 * np.sin(2 * np.pi * 150 * t) * (1 + np.sin(2 * np.pi * 3 * t)) + 0.01 * rng.standard_normal(t.size)
    sf.write(str(path), signal.astype(np.float32), SR, subtype="PCM_16")
    return path


def _score_twice(clip: Path, env_overrides: dict[str, str]) -> list[dict]:
    env = {**os.environ, **env_overrides}
    outputs = []
    for _ in range(2):
        done = subprocess.run([sys.executable, "-c", SCORE_IN_FRESH_PROCESS, str(clip)], cwd=BACKEND, env=env,
                              capture_output=True, text=True, timeout=300, check=False)
        assert done.returncode == 0, done.stderr[-2000:]
        outputs.append(json.loads(done.stdout.strip().splitlines()[-1]))
    return outputs


def test_same_clip_same_score_in_two_fresh_processes(tmp_path):
    first, second = _score_twice(_clip(tmp_path / "clip.wav"), {})
    assert len(first["windows"]) == 3  # 9.5 s: two 4 s windows and the last 4 s
    assert first == second


def test_served_checkpoint_same_score_in_two_fresh_processes(tmp_path):
    calibration = REPO / "paper" / "config" / "audio_calibration.json"
    checkpoint = REPO / json.loads(calibration.read_text(encoding="utf-8"))["checkpoint"]
    if not checkpoint.is_file():
        pytest.skip(f"{checkpoint.name} not present (weights are never committed)")
    overrides = {
        "CHECKPOINT_DIR": str(checkpoint.parent),
        "AUDIO_LCNN_CALIBRATION_FILE": str(calibration),
        "AUDIO_VERDICT_CONFIG_FILE": str(REPO / "paper" / "config" / "frozen_audio_config.json"),
    }
    first, second = _score_twice(_clip(tmp_path / "clip.wav"), overrides)
    assert first == second
