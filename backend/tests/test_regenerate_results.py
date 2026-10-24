"""scripts/regenerate_results.py: what counts as the same result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import regenerate_results as rr  # noqa: E402


def _file(name: str, content: bytes) -> Path:
    path = rr.REPO_ROOT / "results" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_json_matches_when_only_provenance_differs(tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "REPO_ROOT", tmp_path)
    path = _file("x.json", json.dumps({"auc": 0.9, "provenance": {"utc_time": "now"}}).encode())
    assert rr.compare(path, json.dumps({"auc": 0.9, "provenance": {"utc_time": "then"}}).encode()) is None
    assert "auc" in rr.compare(path, json.dumps({"auc": 0.8, "provenance": {}}).encode())


def test_figures_compare_byte_for_byte_and_new_files_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "REPO_ROOT", tmp_path)
    path = _file("figures/f.png", b"\x89PNG-a")
    assert rr.compare(path, b"\x89PNG-a") is None
    assert "bytes differ" in rr.compare(path, b"\x89PNG-b")
    assert "not committed" in rr.compare(path, None)
