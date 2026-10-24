"""scripts/robustness.py: image transforms, the codec round trip, the frozen rule and the audio summary."""

from __future__ import annotations

import json
import math
import struct
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import eval_pipeline as ep  # noqa: E402
import robustness as rb  # noqa: E402

RULE = {"authentic_below": 0.417, "flagged_at_or_above": 0.577}


def _image(size=(2000, 1000)):
    from PIL import Image

    gradient = np.add.outer(np.arange(size[1]), np.arange(size[0])) % 256
    return Image.fromarray(np.stack([gradient] * 3, axis=-1).astype(np.uint8))


def test_image_transforms():
    image = _image()
    same, quality = rb.transform_image(image, "jpeg30")
    assert same.size == image.size and quality == 30
    half, quality = rb.transform_image(image, "resize50")
    assert half.size == (1000, 500) and quality is None
    whatsapp, quality = rb.transform_image(image, "whatsapp")
    assert max(whatsapp.size) == 1600 and quality == 70
    small, _ = rb.transform_image(_image((800, 600)), "whatsapp")
    assert small.size == (800, 600)  # never enlarged
    with pytest.raises(ValueError):
        rb.transform_image(image, "blur")


def test_image_copies_keep_their_group_and_condition(tmp_path):
    root, out = tmp_path / "root", tmp_path / "out"
    (root / "ai").mkdir(parents=True)
    _image((300, 200)).save(root / "ai" / "a1.png")
    rows = [{"image_id": "a1", "relative_path": "ai/a1.png", "label": 1, "generator": "sdxl_1.0",
             "source": "test", "condition": "original", "group": ""}]
    manifest = rb.make_image_copies(rows, root, out)
    assert [r["condition"] for r in manifest] == ["original", *rb.IMAGE_CONDITIONS]
    assert {r["group"] for r in manifest} == {"a1"}
    assert len({r["image_id"] for r in manifest}) == len(manifest)
    from PIL import Image

    for row in manifest[1:]:
        with Image.open(out / row["relative_path"]) as copy:
            assert copy.format == ("PNG" if row["condition"] == "resize50" else "JPEG")


def test_frozen_rule_matches_the_backend_boundaries():
    assert rb.frozen_verdict(0.577, RULE) == "flagged"
    assert rb.frozen_verdict(0.5769, RULE) == "inconclusive"
    assert rb.frozen_verdict(0.417, RULE) == "inconclusive"
    assert rb.frozen_verdict(0.4169, RULE) == "authentic"


def _tone_wav(path: Path, seconds: float = 2.0, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate)))
                          for i in range(int(seconds * rate)))
        handle.writeframes(frames)


@pytest.mark.parametrize("condition", list(rb.AUDIO_CODECS))
def test_codec_round_trip_keeps_the_length(tmp_path, condition):
    pytest.importorskip("imageio_ffmpeg")
    from app.ml.preprocessing import load_audio

    source = tmp_path / "tone.wav"
    _tone_wav(source)
    encoded = rb.encode(source, condition, tmp_path, rb.ffmpeg_exe())
    assert encoded.suffix == rb.AUDIO_CODECS[condition]["suffix"] and encoded.stat().st_size > 0
    waveform, rate = load_audio(encoded, 16000)
    assert rate == 16000
    assert abs(len(waveform) - 32000) < 0.1 * 32000  # codec padding only


def _rows():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(30):
        label = int(i >= 10)
        attack = "-" if label == 0 else ("A07" if i < 20 else "A08")
        for condition, noise in (("original", 0.05), ("mp3_64k", 0.3), ("opus_32k", 0.1)):
            p = float(np.clip((0.9 if label else 0.1) + rng.normal(0, noise), 1e-6, 1 - 1e-6))
            rows.append({"utt_id": f"u{i}", "label": label, "attack_id": attack, "condition": condition,
                         "probability": p, "cm_score": -math.log(p / (1 - p)), "n_windows": 1, "error": ""})
    return rows


def test_audio_metrics_per_condition():
    metrics = rb.audio_metrics(_rows(), RULE, n_resamples=50)
    assert set(metrics["conditions"]) == set(rb.CONDITIONS)
    original = metrics["conditions"]["original"]
    assert original["eer"] == 0.0 and original["auc"]["auc"] == 1.0
    assert set(original["per_attack_eer"]) == {"A07", "A08"}
    assert original["frozen_rule_verdicts"]["bonafide"]["authentic"]["n"] == 10
    assert metrics["conditions"]["mp3_64k"]["auc"]["auc"] <= 1.0
    assert set(metrics["delong_vs_original"]) == set(rb.AUDIO_CODECS)


def test_summarise_writes_metrics_figure_and_its_index_section(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "OUT_DIR", tmp_path / "no_end_to_end_run")
    out = tmp_path / "audio_codec_robustness"
    out.mkdir()
    rows = _rows()
    ep.write_sample(out / "sample.csv", [{"utt_id": f"u{i}", "label": int(i >= 10), "attack_id": "-",
                                          "relative_path": f"u{i}.flac"} for i in range(30)])
    import csv

    with open(out / "scores.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rb.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (out / "config.json").write_text(json.dumps({"sample": {"size": 30}, "codecs": {}, "rule": RULE,
                                                 "inference": "float32"}), encoding="utf-8")
    index = tmp_path / "INDEX.md"
    index.write_text("| a | b | c | d | e |\n", encoding="utf-8")
    results, figure = tmp_path / "robustness.json", tmp_path / "fig.png"
    payload = rb.summarise(out, results_file=results, figure=figure, index=index)
    assert payload["audio"]["status"] == "done"
    assert payload["image"]["status"] == "not_run"
    assert figure.stat().st_size > 0
    assert "<!-- begin:audio_codec_robustness -->" in index.read_text(encoding="utf-8")
    assert json.loads((out / "metrics.json").read_text(encoding="utf-8"))["original_vs_end_to_end_run"] is None


def test_summarise_refuses_a_missing_condition(tmp_path):
    out = tmp_path / "run"
    out.mkdir()
    rows = [r for r in _rows() if not (r["utt_id"] == "u3" and r["condition"] == "opus_32k")]
    ep.write_sample(out / "sample.csv", [{"utt_id": f"u{i}", "label": 0, "attack_id": "-", "relative_path": "x"}
                                         for i in range(30)])
    import csv

    with open(out / "scores.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rb.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (out / "config.json").write_text(json.dumps({"rule": RULE}), encoding="utf-8")
    with pytest.raises(SystemExit, match="every condition"):
        rb.summarise(out, results_file=tmp_path / "r.json", figure=tmp_path / "f.png", index=tmp_path / "I.md")
