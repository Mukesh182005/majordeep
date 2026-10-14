"""End-to-end check of the ASVspoof training and scoring scripts on a tiny fake corpus."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ml.preprocessing.asvspoof_features import build_cache  # noqa: E402
from ml.preprocessing.build_asvspoof2019_la import (  # noqa: E402
    add_num_samples,
    parse_protocol,
    read_manifest,
    sha256_file,
    write_manifest,
)

pytest.importorskip("torch")


def _fake_corpus(root: Path) -> Path:
    import soundfile as sf

    rng = np.random.default_rng(11)
    protocols = root / "LA/ASVspoof2019_LA_cm_protocols"
    protocols.mkdir(parents=True)
    lines = {"train": [], "dev": []}
    for split, prefix, speakers in (("train", "LA_T_", ("LA_0001", "LA_0002")), ("dev", "LA_D_", ("LA_0101",))):
        for i in range(8):
            spoof = i % 2 == 1
            attack = f"A0{1 + i % 6}" if spoof else "-"
            lines[split].append(f"{speakers[i % len(speakers)]} {prefix}{i:07d} - {attack} {'spoof' if spoof else 'bonafide'}")
    rows = []
    for split, text in lines.items():
        path = protocols / f"{split}.txt"
        path.write_text("\n".join(text) + "\n", encoding="utf-8")
        rows += parse_protocol(path, split)
    for row in rows:
        n = int(rng.integers(20000, 90000))
        tone = np.sin(2 * np.pi * (300 if row["label"] else 180) * np.arange(n) / 16000)
        audio = (0.2 * tone + 0.05 * rng.standard_normal(n)).astype(np.float32)
        path = root / "LA" / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), audio, 16000, subtype="PCM_16")
    assert add_num_samples(rows, root / "LA") == []
    manifest = root / "processed/manifest.csv"
    write_manifest(manifest, rows)
    rows = read_manifest(manifest)
    for split in ("train", "dev"):
        build_cache(rows, root / "LA", manifest.parent / "features", split, ["lfcc"], workers=1,
                    manifest_sha256=sha256_file(manifest))
    return manifest


def test_train_one_epoch_then_score_dev(tmp_path):
    manifest = _fake_corpus(tmp_path)
    cache = manifest.parent / "features"
    checkpoint = tmp_path / "ckpt/audio_lcnn_asvspoof_lfcc_seed0.pt"
    run_dir = tmp_path / "run"
    env = {**os.environ, "DEEPSENTINEL_DATA": str(tmp_path / "no_data_here")}
    common = ["--cache", str(cache)]
    train = subprocess.run(
        [sys.executable, str(REPO / "ml/training/train_asvspoof.py"), "--features", "lfcc", "--seed", "0",
         "--epochs", "1", "--batch-size", "4", "--device", "cpu", "--output", str(checkpoint),
         "--run-dir", str(run_dir), "--manifest", str(manifest), *common],
        capture_output=True, text=True, env=env, cwd=REPO, timeout=600,
    )
    assert train.returncode == 0, train.stdout[-2000:] + train.stderr[-2000:]
    assert checkpoint.is_file()
    config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert config["best_epoch"] == 1 and 0.0 <= config["dev_eer"] <= 1.0
    assert config["train_config"]["class_balance"].startswith("weighted BCE")
    with open(run_dir / "dev_scores.csv", newline="", encoding="utf-8") as handle:
        scores = list(csv.DictReader(handle))
    assert len(scores) == 8 and set(scores[0]) == {"utt_id", "attack_id", "label", "score"}

    # A second run must refuse to overwrite the checkpoint.
    again = subprocess.run(
        [sys.executable, str(REPO / "ml/training/train_asvspoof.py"), "--features", "lfcc", "--output",
         str(checkpoint), "--run-dir", str(run_dir), *common],
        capture_output=True, text=True, env=env, cwd=REPO, timeout=600,
    )
    assert again.returncode != 0 and "already exists" in (again.stdout + again.stderr)

    out_dir = tmp_path / "scores"
    score = subprocess.run(
        [sys.executable, str(REPO / "ml/evaluation/eval_asvspoof.py"), "--checkpoint", str(checkpoint),
         "--split", "dev", "--output", str(out_dir), "--device", "cpu", *common],
        capture_output=True, text=True, env=env, cwd=REPO, timeout=600,
    )
    assert score.returncode == 0, score.stdout[-2000:] + score.stderr[-2000:]
    metrics = json.loads((out_dir / f"{checkpoint.stem}_dev_metrics.json").read_text(encoding="utf-8"))
    assert metrics["n_bonafide"] == 4 and metrics["n_spoof"] == 4 and metrics["min_tdcf"] is None

    # The eval split cannot be scored without the dev-based selection and explicit confirmation.
    refused = subprocess.run(
        [sys.executable, str(REPO / "ml/evaluation/eval_asvspoof.py"), "--checkpoint", str(checkpoint),
         "--split", "eval", "--output", str(out_dir), *common],
        capture_output=True, text=True, env=env, cwd=REPO, timeout=600,
    )
    assert refused.returncode != 0 and "confirm-final-eval" in (refused.stdout + refused.stderr)


def test_protected_checkpoint_names_are_refused(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "ml/training/train_asvspoof.py"), "--features", "lfcc",
         "--output", str(tmp_path / "audio_detector.pt"), "--cache", str(tmp_path)],
        capture_output=True, text=True, cwd=REPO, timeout=600,
    )
    assert result.returncode != 0 and "never overwritten" in (result.stdout + result.stderr)
