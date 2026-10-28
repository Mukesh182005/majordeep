"""pellav2 (app/ml/audio/pellav2.py): the port, the loading path and the verdict wiring.

No downloads: the model tests use a tiny Wav2Vec2BertConfig; the filterbank is
checked against torchaudio output recorded in fixtures/pellav2_kaldi_fbank_reference.json
(torchaudio has no build for the torch this project pins).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
pytest.importorskip("scipy")

from app.config import settings  # noqa: E402
from app.ml.audio import pellav2 as pv  # noqa: E402

SR = 16000
FBANK_REFERENCE = Path(__file__).parent / "fixtures" / "pellav2_kaldi_fbank_reference.json"


def _tiny_config():
    return transformers.Wav2Vec2BertConfig(
        hidden_size=32, num_hidden_layers=2, num_attention_heads=2, intermediate_size=64,
        output_hidden_size=32, conv_depthwise_kernel_size=3, position_embeddings_type=None,
    )


@pytest.fixture(scope="module")
def tiny():
    torch.manual_seed(0)
    module = pv.Detector(_tiny_config()).float().eval()
    return pv.LoadedPellav2(module=module, device="cpu", metadata={"weights_sha256": "tiny", "revision": None})


def _noise(seconds: float, seed: int = 0) -> np.ndarray:
    return (0.1 * np.random.default_rng(seed).standard_normal(int(seconds * SR))).astype(np.float32)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(10.0, [0, 64000, 128000]), (0.5, [0]), (8.5, [0, 64000]), (9.0, [0, 64000, 128000]), (4.0, [0])],
)
def test_window_starts(seconds, expected):
    # consecutive 4 s windows; a final partial window is kept only if it is >= 1 s or the only one
    assert pv.window_starts(int(seconds * SR), max_windows=8) == expected


def test_window_starts_respects_the_cap():
    assert pv.window_starts(60 * SR, max_windows=8) == [i * 64000 for i in range(8)]


def test_kaldi_fbank_matches_torchaudio():
    reference = json.loads(FBANK_REFERENCE.read_text(encoding="utf-8"))["signals"]
    for n, d in reference.items():
        mine = pv.kaldi_fbank(torch.tensor(d["x"], dtype=torch.float32) * 32768.0).numpy()
        expected = np.array(d["fbank"], dtype=np.float32)
        assert mine.shape == expected.shape, n
        np.testing.assert_allclose(mine, expected, atol=1e-4, err_msg=f"{n} samples")


def test_prepared_windows_are_loudness_normalised_and_padded():
    windows, spans = pv.prepare_windows(_noise(10.0), SR, max_windows=8)
    assert windows.shape == (3, 64000) and windows.dtype == np.float32
    assert spans[-1] == (8.0, 10.0)
    assert np.all(windows[2, 32000:] == 0.0)  # the 2 s tail is zero-padded
    assert np.abs(windows).max() <= 1.0


def test_score_windows_counts_and_range(tiny):
    probs = pv.score_windows(_noise(10.0), SR, 8, loaded=tiny)
    assert len(probs) == 3 and all(0.0 <= p <= 1.0 for p in probs)
    assert len(pv.score_windows(_noise(0.5), SR, 8, loaded=tiny)) == 1


def test_score_clip_is_the_mean_of_the_windows(tiny):
    clip = pv.score_clip(_noise(10.0, seed=3), SR, 8, loaded=tiny)
    assert clip["n_windows"] == 3 and clip["model"] == pv.MODEL_LABEL
    assert clip["prob"] == pytest.approx(np.mean(clip["window_probs"]), abs=1e-4)
    assert clip["max_prob"] == pytest.approx(max(clip["window_probs"]), abs=1e-4)


def test_same_input_gives_the_same_score(tiny):
    wave = _noise(6.0, seed=5)
    assert pv.score_clip(wave, SR, 8, loaded=tiny)["window_logits"] == pv.score_clip(wave, SR, 8, loaded=tiny)["window_logits"]


def test_checkpoint_loads_strictly_through_build_pellav2(tiny, tmp_path):
    path = tmp_path / pv.WEIGHTS_FILENAME
    torch.save(tiny.module.state_dict(), path)
    loaded = pv.build_pellav2(tmp_path, device="cpu", backbone_config=_tiny_config())
    wave = _noise(5.0, seed=9)
    assert pv.score_clip(wave, SR, 8, loaded=loaded)["window_logits"] == pv.score_clip(wave, SR, 8, loaded=tiny)["window_logits"]
    assert len(loaded.metadata["weights_sha256"]) == 64

    state = tiny.module.state_dict()
    state["unexpected.weight"] = torch.zeros(1)
    torch.save(state, path)
    with pytest.raises(RuntimeError):
        pv.build_pellav2(tmp_path, device="cpu", backbone_config=_tiny_config())


def test_unavailable_model_scores_nothing(monkeypatch):
    monkeypatch.setattr(pv, "get_pellav2", lambda: None)
    assert pv.score_clip(_noise(2.0), SR, 8) is None
    assert pv.score_windows(_noise(2.0), SR, 8) == []


# --------------------------------------------------------------------------- pipeline wiring


def _stub_clip(prob: float) -> dict:
    return {
        "prob": prob, "max_prob": prob, "window_probs": [prob], "window_logits": [0.0],
        "windows": [{"index": 0, "start_s": 0.0, "end_s": 3.0, "probability": prob}],
        "n_windows": 1, "seconds_scored": 3.0, "clip_seconds": 3.0, "model": pv.MODEL_LABEL,
        "metadata": {"weights_sha256": "stub-sha", "revision": "stub"}, "inference": "stub",
    }


@pytest.fixture()
def pellav2_config(tmp_path, monkeypatch):
    path = tmp_path / "pellav2_verdict_config.json"
    path.write_text(json.dumps({
        "weights_sha256": "stub-sha", "threshold": 0.5, "inconclusive_band": 0.08,
        "authentic_below": 0.42, "flagged_at_or_above": 0.58,
        "decision_rule": "pellav2 probability p: authentic if p < 0.42, flagged if p >= 0.58",
    }), encoding="utf-8")
    monkeypatch.setattr(settings, "audio_pellav2_config_file", path)
    return path


def _run(tmp_path):
    from test_audio_lcnn_mode import run_suite, write_reference_clip

    tmp_path.mkdir(parents=True, exist_ok=True)
    return run_suite(write_reference_clip(tmp_path / "clip.wav"), tmp_path / "evidence")


def test_pellav2_decides_when_in_verdict(tmp_path, monkeypatch, pellav2_config):
    monkeypatch.setattr(settings, "audio_pellav2_enabled", True)
    monkeypatch.setattr(settings, "audio_pellav2_in_verdict", True)
    monkeypatch.setattr(pv, "score_clip", lambda *a, **k: _stub_clip(0.9))

    result = _run(tmp_path)
    assert result["models_output"]["fused_ai_probability"] == 0.9
    assert result["models_output"]["model_stage_source"] == "pellav2"
    assert result["fusion_decision"]["final_verdict"] == "AI_GENERATED"
    assert result["fusion_decision"]["verdict_source"] == "pellav2"
    assert [s["source"] for s in result["model_windows"]] == ["pellav2"]
    stage6 = next(m for m in result["pipeline_modules"] if m["stage"] == 6)
    assert "decides the verdict" in stage6["findings"][0]


def test_pellav2_low_score_is_authentic(tmp_path, monkeypatch, pellav2_config):
    monkeypatch.setattr(settings, "audio_pellav2_enabled", True)
    monkeypatch.setattr(settings, "audio_pellav2_in_verdict", True)
    monkeypatch.setattr(pv, "score_clip", lambda *a, **k: _stub_clip(0.1))
    assert _run(tmp_path)["fusion_decision"]["final_verdict"] == "AUTHENTIC"


def test_shown_but_not_in_verdict_leaves_the_lcnn_verdict_unchanged(tmp_path, monkeypatch):
    baseline = _run(tmp_path / "off")
    monkeypatch.setattr(settings, "audio_pellav2_enabled", True)
    monkeypatch.setattr(pv, "score_clip", lambda *a, **k: _stub_clip(0.99))
    shown = _run(tmp_path / "on")

    assert shown["models_output"]["model_stage_source"] == "lcnn_asvspoof"
    assert shown["models_output"]["fused_ai_probability"] == baseline["models_output"]["fused_ai_probability"]
    assert shown["fusion_decision"]["final_verdict"] == baseline["fusion_decision"]["final_verdict"]
    assert shown["models_output"]["pellav2"]["prob"] == 0.99
    stage6 = next(m for m in shown["pipeline_modules"] if m["stage"] == 6)
    assert "pellav2 (w2v-BERT 2.0): 99.0% over 1 window(s) (unvalidated, not in verdict)" in stage6["summary"]


def test_in_verdict_without_a_frozen_config_falls_back_to_the_lcnn(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_pellav2_enabled", True)
    monkeypatch.setattr(settings, "audio_pellav2_in_verdict", True)
    monkeypatch.setattr(settings, "audio_pellav2_config_file", tmp_path / "missing.json")
    monkeypatch.setattr(pv, "score_clip", lambda *a, **k: _stub_clip(0.99))

    result = _run(tmp_path)
    assert result["models_output"]["model_stage_source"] == "lcnn_asvspoof"
    stage6 = next(m for m in result["pipeline_modules"] if m["stage"] == 6)
    assert any("not in the verdict" in f for f in stage6["findings"])


def test_config_for_other_weights_is_refused(pellav2_config):
    from app.ml.base import DetectorUnavailableError

    with pytest.raises(DetectorUnavailableError):
        pv.load_pellav2_verdict_config("some-other-sha")
