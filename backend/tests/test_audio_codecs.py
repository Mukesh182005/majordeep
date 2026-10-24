"""ml/preprocessing/audio_codecs.py: condition assignment, length fitting and the codec round trip."""

from __future__ import annotations

import json
import math
import struct
import sys
import wave
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.preprocessing import audio_codecs as ac  # noqa: E402

PLAN = Path(__file__).resolve().parents[2] / "paper/config/audio_codec_plan.json"


def test_plan_lists_exactly_the_defined_conditions():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["conditions"]["names"] == list(ac.CODEC_CONDITIONS)


def test_assignment_is_stable_seeded_and_spread():
    names = list(ac.CODEC_CONDITIONS)
    ids = [f"LA_T_{i:07d}" for i in range(3300)]
    first = [ac.assign_condition(u, 1, names) for u in ids]
    assert first == [ac.assign_condition(u, 1, names) for u in ids]
    assert first != [ac.assign_condition(u, 2, names) for u in ids]
    counts = Counter(first)
    assert set(counts) == set(names) and min(counts.values()) > 200  # about 300 each


def test_fit_length():
    x = np.arange(5, dtype=np.float32)
    assert ac.fit_length(x, 3).tolist() == [0, 1, 2]
    assert ac.fit_length(x, 7).tolist() == [0, 1, 2, 3, 4, 0, 0]


@pytest.mark.parametrize("condition", ["mp3_64k", "aac_64k", "opus_24k"])
def test_round_trip_keeps_rate_and_length(tmp_path, condition):
    pytest.importorskip("imageio_ffmpeg")
    source = tmp_path / "tone.wav"
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 300 * i / 16000)))
                                    for i in range(24000)))
    out = ac.encode_decode(source, condition, num_samples=24000)
    assert out.dtype == np.float32 and out.shape == (24000,)
    assert np.abs(out).max() > 0.1  # the tone survived
