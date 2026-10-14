"""ASVspoof 2019 LA protocol pipeline: parsing, split integrity, windows, features, cache."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.preprocessing.asvspoof_features import (  # noqa: E402
    FRAMES_PER_WINDOW,
    WINDOW_SAMPLES,
    build_cache,
    lfcc_features,
    linear_filterbank,
    logmel_features,
    utterance_features,
    utterance_windows,
    window_count,
)
from ml.preprocessing.build_asvspoof2019_la import (  # noqa: E402
    EXPECTED_ATTACKS,
    add_num_samples,
    attack_problems,
    parse_protocol,
    read_manifest,
    split_integrity_problems,
    write_manifest,
)

REAL_MANIFEST = Path(__file__).resolve().parents[2] / "data/processed/asvspoof2019_la/manifest.csv"

FAKE_TRAIN = """\
LA_0079 LA_T_1138215 - - bonafide
LA_0079 LA_T_1271820 - A01 spoof
LA_0080 LA_T_1272637 - A06 spoof
"""
FAKE_EVAL = """\
LA_0039 LA_E_2834763 - A11 spoof
LA_0014 LA_E_8877452 - - bonafide
"""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- protocol
class TestProtocolParser:
    def test_parses_fields_labels_and_paths(self, tmp_path):
        rows = parse_protocol(_write(tmp_path / "train.txt", FAKE_TRAIN), "train")
        assert [r["utt_id"] for r in rows] == ["LA_T_1138215", "LA_T_1271820", "LA_T_1272637"]
        assert [r["label"] for r in rows] == [0, 1, 1]
        assert [r["attack_id"] for r in rows] == ["-", "A01", "A06"]
        assert rows[0]["speaker_id"] == "LA_0079"
        assert rows[1]["relative_path"] == "ASVspoof2019_LA_train/flac/LA_T_1271820.flac"
        assert {r["split"] for r in rows} == {"train"}

    def test_split_comes_from_the_protocol_file(self, tmp_path):
        rows = parse_protocol(_write(tmp_path / "eval.txt", FAKE_EVAL), "eval")
        assert {r["split"] for r in rows} == {"eval"}
        assert rows[0]["relative_path"].startswith("ASVspoof2019_LA_eval/flac/")

    @pytest.mark.parametrize(
        "line",
        [
            "LA_0079 LA_T_1 - A01 bonafide",  # bona fide with an attack id
            "LA_0079 LA_T_1 - - spoof",  # spoof without an attack id
            "LA_0079 LA_T_1 - A01 maybe",  # unknown key
            "LA_0079 LA_T_1 - A01",  # missing column
        ],
    )
    def test_rejects_malformed_rows(self, tmp_path, line):
        with pytest.raises(ValueError):
            parse_protocol(_write(tmp_path / "bad.txt", line + "\n"), "train")


class TestSplitIntegrity:
    def test_clean_splits_have_no_problems(self, tmp_path):
        rows = parse_protocol(_write(tmp_path / "t.txt", FAKE_TRAIN), "train")
        rows += parse_protocol(_write(tmp_path / "e.txt", FAKE_EVAL), "eval")
        assert split_integrity_problems(rows) == []

    def test_utterance_in_two_splits_is_reported(self, tmp_path):
        rows = parse_protocol(_write(tmp_path / "t.txt", FAKE_TRAIN), "train")
        leaked = parse_protocol(_write(tmp_path / "d.txt", "LA_0099 LA_T_1138215 - - bonafide\n"), "dev")
        problems = split_integrity_problems(rows + leaked)
        assert any("LA_T_1138215" in p for p in problems)

    def test_speaker_in_two_splits_is_reported(self, tmp_path):
        rows = parse_protocol(_write(tmp_path / "t.txt", FAKE_TRAIN), "train")
        other = parse_protocol(_write(tmp_path / "d.txt", "LA_0079 LA_D_1 - - bonafide\n"), "dev")
        assert any("LA_0079" in p for p in split_integrity_problems(rows + other))

    def test_attack_design_check(self):
        rows = [{"split": "train", "label": 1, "attack_id": f"A{i:02d}"} for i in range(1, 7)]
        rows += [{"split": "eval", "label": 1, "attack_id": f"A{i:02d}"} for i in range(7, 20)]
        assert attack_problems(rows) == []
        rows.append({"split": "train", "label": 1, "attack_id": "A07"})  # an eval attack in train
        assert attack_problems(rows) != []
        assert EXPECTED_ATTACKS["eval"] == {f"A{i:02d}" for i in range(7, 20)}


@pytest.mark.skipif(not REAL_MANIFEST.exists(), reason="full ASVspoof 2019 LA manifest not built")
class TestRealManifest:
    def test_official_design_holds(self):
        rows = read_manifest(REAL_MANIFEST)
        assert split_integrity_problems(rows) == []
        attacks = {s: {r["attack_id"] for r in rows if r["split"] == s and r["label"] == 1} for s in ("train", "eval")}
        assert attacks["train"] == {f"A{i:02d}" for i in range(1, 7)}
        assert attacks["eval"] == {f"A{i:02d}" for i in range(7, 20)}


# --------------------------------------------------------------------------- windows
class TestWindows:
    def test_short_utterance_is_repeated_to_four_seconds(self):
        wave = np.arange(1, 24001, dtype=np.float32)  # 1.5 s
        windows = utterance_windows(wave)
        assert windows.shape == (1, WINDOW_SAMPLES)
        assert np.array_equal(windows[0, :24000], wave)
        assert np.array_equal(windows[0, 24000:48000], wave)
        assert np.array_equal(windows[0, 48000:], wave[:16000])

    def test_exact_four_seconds_is_one_window(self):
        wave = np.random.default_rng(0).standard_normal(WINDOW_SAMPLES).astype(np.float32)
        windows = utterance_windows(wave)
        assert windows.shape == (1, WINDOW_SAMPLES) and np.array_equal(windows[0], wave)

    def test_long_utterance_gives_consecutive_windows_and_the_tail(self):
        wave = np.arange(9 * 16000, dtype=np.float32)  # 9 s
        windows = utterance_windows(wave)
        assert windows.shape == (3, WINDOW_SAMPLES)
        assert np.array_equal(windows[0], wave[:64000])  # training input: first 4 s
        assert np.array_equal(windows[1], wave[64000:128000])
        assert np.array_equal(windows[2], wave[-64000:])

    @pytest.mark.parametrize("n", [1, 100, 63999, 64000, 64001, 128000, 128001, 300000])
    def test_window_count_matches_windows(self, n):
        assert window_count(n) == utterance_windows(np.ones(n, dtype=np.float32)).shape[0]


# --------------------------------------------------------------------------- front ends
class TestFrontEnds:
    def _tone(self, seconds=4.0):
        t = np.arange(int(16000 * seconds)) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t) + 0.01 * np.random.default_rng(1).standard_normal(t.size)).astype(
            np.float32
        )

    def test_logmel_shape(self):
        feats = logmel_features(self._tone())
        assert feats.shape == (64, FRAMES_PER_WINDOW) and np.isfinite(feats).all()
        assert feats.max() == pytest.approx(0.0)  # dB relative to the window maximum

    def test_lfcc_shape_and_deltas(self):
        feats = lfcc_features(self._tone())
        assert feats.shape == (60, FRAMES_PER_WINDOW) and np.isfinite(feats).all()
        # A steady tone has near-zero deltas away from the edges.
        assert np.abs(feats[20:40, 10:-10]).mean() < 0.1 * np.abs(feats[:20, 10:-10]).mean()

    def test_linear_filters_overlap_to_one_between_first_and_last_centre(self):
        bank = linear_filterbank()
        freqs = np.linspace(0, 8000, bank.shape[1])
        centres = np.linspace(0, 8000, 22)[1:-1]
        inside = (freqs >= centres[0]) & (freqs <= centres[-1])
        assert np.allclose(bank.sum(axis=0)[inside], 1.0)

    def test_utterance_features_cover_every_window(self):
        feats = utterance_features(self._tone(9.0), ["logmel", "lfcc"])
        assert feats["logmel"].shape == (3, 64, FRAMES_PER_WINDOW)
        assert feats["lfcc"].shape == (3, 60, FRAMES_PER_WINDOW)


# --------------------------------------------------------------------------- end to end
def _fake_la_tree(root: Path) -> tuple[Path, list[dict]]:
    import soundfile as sf

    rng = np.random.default_rng(7)
    protocols = root / "ASVspoof2019_LA_cm_protocols"
    protocols.mkdir(parents=True)
    _write(protocols / "train.txt", FAKE_TRAIN)
    _write(protocols / "eval.txt", FAKE_EVAL)
    rows = parse_protocol(protocols / "train.txt", "train") + parse_protocol(protocols / "eval.txt", "eval")
    lengths = [24000, 64000, 100000, 150000, 30000]
    for row, n in zip(rows, lengths, strict=True):
        path = root / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), (0.1 * rng.standard_normal(n)).astype(np.float32), 16000, subtype="PCM_16")
    return root, rows


def test_manifest_and_cache_round_trip(tmp_path):
    from ml.preprocessing.asvspoof_features import load_waveform
    from ml.preprocessing.build_asvspoof2019_la import sha256_file
    from ml.training.asvspoof_dataset import (
        ASVspoofTrainDataset,
        ASVspoofWindowDataset,
        CachedSplit,
    )

    la_root, rows = _fake_la_tree(tmp_path / "LA")
    assert add_num_samples(rows, la_root) == []
    assert [r["num_samples"] for r in rows] == [24000, 64000, 100000, 150000, 30000]

    manifest = tmp_path / "out" / "manifest.csv"
    write_manifest(manifest, rows)
    rows = read_manifest(manifest)
    sha = sha256_file(manifest)
    features_dir = tmp_path / "out" / "features"
    for split in ("train", "eval"):
        build_cache(rows, la_root, features_dir, split, ["logmel", "lfcc"], workers=1, manifest_sha256=sha)

    cache = CachedSplit(features_dir, "lfcc", "train")
    assert len(cache) == 3 and list(cache.n_windows) == [1, 1, 2]
    train = ASVspoofTrainDataset(cache)
    feats, label, utt = train[2]
    assert feats.shape == (1, 60, FRAMES_PER_WINDOW) and feats.dtype.is_floating_point
    assert (label, utt) == (1, "LA_T_1272637")
    direct = utterance_features(load_waveform(la_root / rows[2]["relative_path"]), ["lfcc"])["lfcc"]
    assert np.allclose(feats[0].numpy(), direct[0], atol=0.05, rtol=1e-2)  # float16 storage

    windows = ASVspoofWindowDataset(CachedSplit(features_dir, "logmel", "eval"))
    assert len(windows) == 3 + 1  # 150,000 samples -> 3 windows; 30,000 -> 1
    assert [windows[i][2] for i in range(len(windows))] == ["LA_E_2834763"] * 3 + ["LA_E_8877452"]

    # Resume: pretend extraction stopped after the first utterance; a rerun completes it.
    progress = features_dir / "logmel" / "train.progress.json"
    state = json.loads(progress.read_text())
    progress.write_text(json.dumps({**state, "done": 1, "complete": False}))
    with pytest.raises(RuntimeError):
        CachedSplit(features_dir, "logmel", "train")
    build_cache(rows, la_root, features_dir, "train", ["logmel"], workers=1, manifest_sha256=sha)
    assert CachedSplit(features_dir, "logmel", "train").n_windows.sum() == 4


def test_feature_cache_holds_no_absolute_paths(tmp_path):
    la_root, rows = _fake_la_tree(tmp_path / "LA")
    add_num_samples(rows, la_root)
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, rows)
    text = manifest.read_text(encoding="utf-8")
    assert str(tmp_path) not in text and os.sep + "LA" + os.sep not in text
