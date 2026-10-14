"""Provenance helper — the record attached to every paper result."""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.provenance import REPO_ROOT, collect_provenance, sha256_file  # noqa: E402

REQUIRED_KEYS = {
    "git_commit",
    "git_dirty",
    "python",
    "torch",
    "cuda_build",
    "gpu_name",
    "utc_time",
    "command_line",
    "manifest_sha256",
    "seeds",
    "libraries",
}


def test_sha256_matches_hashlib(tmp_path):
    manifest = tmp_path / "manifest.csv"
    content = b"utt_id,label\nLA_T_0000001,0\n" * 1000
    manifest.write_bytes(content)
    assert sha256_file(manifest, chunk_size=64) == hashlib.sha256(content).hexdigest()


def test_record_has_every_required_field(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_bytes(b"a,b\n1,2\n")
    record = collect_provenance(manifest, seeds=0, argv=["train.py", "--seed", "0"])

    assert record.keys() >= REQUIRED_KEYS
    assert record["manifest_sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert record["seeds"] == [0]
    assert record["command_line"] == ["train.py", "--seed", "0"]
    assert record["python"].count(".") == 2
    assert datetime.fromisoformat(record["utc_time"]).utcoffset() == timedelta(0)


def test_manifest_outside_repo_records_no_absolute_path(tmp_path):
    manifest = tmp_path / "secret_dir" / "manifest.csv"
    manifest.parent.mkdir()
    manifest.write_text("x\n", encoding="utf-8")
    record = collect_provenance(manifest)
    assert record["manifest"] == "manifest.csv"
    assert str(tmp_path) not in str(record)


def test_git_commit_is_recorded_inside_the_repository():
    if not (REPO_ROOT / ".git").exists():
        return
    record = collect_provenance()
    assert record["git_commit"] is not None and len(record["git_commit"]) == 40
    assert isinstance(record["git_dirty"], bool)
    assert record["manifest_sha256"] is None
