"""scripts/benchmark_latency.py: percentiles, the hardware record and the summary."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import benchmark_latency as bl  # noqa: E402


def _rows():
    rows = []
    for device, scale in (("cuda", 1.0), ("cpu", 4.0)):
        for modality, base in (("image", 0.2), ("audio", 1.0), ("video", 3.0)):
            rows.append({"device": device, "modality": modality, "input": "x", "run": 0,
                         "seconds": 30.0, "cold_start": 1})
            rows += [{"device": device, "modality": modality, "input": "x", "run": k + 3,
                      "seconds": base * scale * (k + 1), "cold_start": 0} for k in range(20)]
    return rows


def test_percentiles_exclude_the_cold_start():
    summary = bl.percentiles(_rows())
    gpu_image = summary["cuda"]["image"]
    assert gpu_image["n"] == 20 and gpu_image["cold_start_s"] == 30.0
    assert abs(gpu_image["p50_s"] - 0.2 * 10.5) < 1e-9          # median of 0.2 * 1..20
    assert abs(gpu_image["p95_s"] - 0.2 * 19.05) < 1e-9         # numpy linear interpolation
    assert summary["cpu"]["video"]["max_s"] == 3.0 * 4.0 * 20


def test_hardware_record_has_the_fields_the_results_cite():
    record = bl.hardware()
    assert set(record) == {"cpu", "logical_cpus", "ram_gb", "gpu_driver", "os"}
    assert record["logical_cpus"] and record["cpu"]


def test_summarise_from_saved_timings(tmp_path):
    out = tmp_path / "latency"
    out.mkdir()
    with open(out / "timings.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=bl.COLUMNS)
        writer.writeheader()
        writer.writerows(_rows())
    (out / "config.json").write_text(json.dumps({"hardware": {"cpu": "test"}, "inputs": {}, "settings": {},
                                                 "runs": {}, "provenance": {"git_commit": "abc"}}), encoding="utf-8")
    results, figure = tmp_path / "latency.json", tmp_path / "latency.png"
    payload = bl.summarise(out, results_file=results, figure=figure)
    assert payload["status"] == "done" and payload["measured_at"] == {"git_commit": "abc"}
    assert set(payload["latency"]) == {"cuda", "cpu"}
    assert figure.stat().st_size > 0
    assert json.loads(results.read_text(encoding="utf-8"))["latency"]["cpu"]["audio"]["n"] == 20


def test_summarise_without_timings_says_not_run(tmp_path):
    payload = bl.summarise(tmp_path / "none", results_file=tmp_path / "l.json", figure=tmp_path / "f.png")
    assert payload["status"] == "not_run"
    assert not (tmp_path / "f.png").exists()
