#!/usr/bin/env python3
"""End-to-end latency per modality on this machine, on GPU and on CPU.

Each run times ``app.ml.pipeline.analyze``, the worker's function for an
upload, from file to result (evidence plots included, into a temporary folder).
Every device runs in its own process with ``DEVICE`` set, so models load on
that device. Inputs:

* image: faces-140k test images, half real and half StyleGAN (256 x 256 px;
  phone photos are larger, so image times here are a lower bound);
* audio: ASVspoof 2019 LA **dev** utterances (no eval file is read);
* video: a 10 s, 640 x 480, 30 fps synthetic clip of one StyleGAN face, made by
  ``ml/evaluation/video_pipeline_timing.py``'s generator (no audio track).

The first call per modality (model loading) is recorded as the cold start and
excluded from the percentiles; then ``--warmup`` more calls are discarded.
Other jobs running at the same time slow every number down: run this on an
otherwise idle machine. The hardware is recorded with the timings.

Writes
    paper_results/latency/{timings.csv, config.json}
    results/latency.json, results/figures/latency.png

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python scripts/benchmark_latency.py run              # GPU (if available) and CPU
    python scripts/benchmark_latency.py summarise        # rebuild from timings.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_pipeline as ep  # noqa: E402  (also puts the repository and backend/ on sys.path)

REPO_ROOT = ep.REPO_ROOT
OUT_DIR = REPO_ROOT / "paper_results/latency"
RESULTS_FILE = REPO_ROOT / "results/latency.json"
FIGURE = REPO_ROOT / "results/figures/latency.png"
FACES_TEST = REPO_ROOT / "data/raw/faces-140k/real_vs_fake/real-vs-fake/test"
MODALITIES = ("image", "audio", "video")
COLUMNS = ["device", "modality", "input", "run", "seconds", "cold_start"]


# --------------------------------------------------------------------------- hardware


def cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def ram_bytes() -> int | None:
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    return None


def gpu_driver() -> str | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def hardware() -> dict:
    ram = ram_bytes()
    return {"cpu": cpu_name(), "logical_cpus": os.cpu_count(),
            "ram_gb": round(ram / 2**30, 1) if ram else None, "gpu_driver": gpu_driver(),
            "os": platform.platform()}


# --------------------------------------------------------------------------- inputs


def pick_inputs(manifest: Path, la_root: Path, faces_dir: Path, workdir: Path, n_images: int, n_audio: int,
                seed: int) -> dict[str, list[Path]]:
    from ml.preprocessing.build_asvspoof2019_la import read_manifest

    rng = np.random.default_rng(seed)
    images = []
    for cls in ("real", "fake"):
        files = sorted((faces_dir / cls).glob("*.jpg"))
        if len(files) < n_images // 2:
            raise SystemExit(f"Not enough images in {faces_dir / cls}.")
        images += [files[i] for i in sorted(rng.choice(len(files), n_images // 2, replace=False))]
    dev = sorted((r for r in read_manifest(manifest) if r["split"] == "dev"), key=lambda r: r["utt_id"])
    audio = [la_root / dev[i]["relative_path"] for i in sorted(rng.choice(len(dev), n_audio, replace=False))]

    from ml.evaluation.video_pipeline_timing import make_video

    video = workdir / "synthetic_10s.mp4"
    make_video(images[-1], 10, video)
    return {"image": images, "audio": audio, "video": [video]}


# --------------------------------------------------------------------------- timing


def time_device(inputs: dict[str, list[Path]], runs: dict[str, int], warmup: int) -> list[dict]:
    """Timings in this process (DEVICE is read by app.config at import)."""
    from app.config import settings
    from app.ml.pipeline import analyze
    from app.models import MediaType

    media = {"image": MediaType.IMAGE, "audio": MediaType.AUDIO, "video": MediaType.VIDEO}
    rows = []
    for modality in MODALITIES:
        files = inputs[modality]
        for k in range(1 + warmup + runs[modality]):
            path = files[k % len(files)]
            with tempfile.TemporaryDirectory(prefix="ds-latency-") as evidence:
                t0 = time.perf_counter()
                analyze(media[modality], path, evidence, f"latency-{modality}-{k}")
                seconds = time.perf_counter() - t0
            if k == 0 or k > warmup:
                rows.append({"device": settings.device, "modality": modality, "input": path.name,
                             "run": k, "seconds": round(seconds, 4), "cold_start": int(k == 0)})
            print(f"  {settings.device} {modality} {k}: {seconds:.3f} s", flush=True)
    return rows


def percentiles(rows: list[dict]) -> dict:
    summary: dict = {}
    for device in sorted({r["device"] for r in rows}):
        summary[device] = {}
        for modality in MODALITIES:
            warm = np.array([float(r["seconds"]) for r in rows
                             if r["device"] == device and r["modality"] == modality and not int(r["cold_start"])])
            cold = [float(r["seconds"]) for r in rows
                    if r["device"] == device and r["modality"] == modality and int(r["cold_start"])]
            if warm.size:
                summary[device][modality] = {
                    "n": int(warm.size), "p50_s": float(np.percentile(warm, 50)), "p95_s": float(np.percentile(warm, 95)),
                    "mean_s": float(warm.mean()), "max_s": float(warm.max()),
                    "cold_start_s": cold[0] if cold else None,
                }
    return summary


def plot_latency(summary: dict, rows: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted = "#fcfcfb", "#0b0b0b", "#52514e"
    colours = {"cuda": "#2a78d6", "cpu": "#eb6834"}
    devices = [d for d in ("cuda", "cpu") if d in summary]
    fig, axes = plt.subplots(1, len(MODALITIES), figsize=(9, 2.8), facecolor=surface)
    for ax, modality in zip(axes, MODALITIES):
        ax.set_facecolor(surface)
        for x, device in enumerate(devices):
            values = [float(r["seconds"]) for r in rows
                      if r["device"] == device and r["modality"] == modality and not int(r["cold_start"])]
            if not values:
                continue
            jitter = np.linspace(-0.12, 0.12, len(values))
            ax.scatter(x + jitter, values, s=14, color=colours[device], alpha=0.6, linewidths=0)
            stats = summary[device][modality]
            ax.plot([x - 0.25, x + 0.25], [stats["p50_s"]] * 2, color=ink, linewidth=2)
            ax.text(x + 0.28, stats["p50_s"], f"p50 {stats['p50_s']:.2f} s", va="center", fontsize=7.5, color=ink)
        ax.set_xticks(range(len(devices)), ["GPU" if d == "cuda" else "CPU" for d in devices], fontsize=8.5,
                      color=ink)
        ax.set_xlim(-0.5, len(devices) - 0.2)
        ax.set_ylim(bottom=0)
        ax.set_title(modality.capitalize(), fontsize=9.5, color=ink, loc="left")
        ax.tick_params(axis="y", labelsize=8, colors=muted)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color("#d6d5d0")
        ax.spines["bottom"].set_color("#d6d5d0")
    axes[0].set_ylabel("Seconds per file (warm)", fontsize=8.5, color=muted)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


def summarise(out_dir: Path = OUT_DIR, results_file: Path = RESULTS_FILE, figure: Path = FIGURE) -> dict:
    from ml.provenance import collect_provenance

    timings = out_dir / "timings.csv"
    if not timings.is_file():
        payload = {"status": "not_run", "reason": f"No saved timings in {ep._rel(out_dir)}; run `run` first.",
                   "provenance": collect_provenance(None)}
    else:
        rows = ep.read_csv(timings)
        config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
        summary = percentiles(rows)
        plot_latency(summary, rows, figure)
        payload = {"status": "done", "source": ep._rel(timings), "timings_sha256": ep._sha256(timings),
                   "figure": ep._rel(figure), "hardware": config["hardware"], "inputs": config["inputs"],
                   "settings": config["settings"], "runs": config["runs"], "latency": summary,
                   "measured_at": config["provenance"]}
        payload["provenance"] = collect_provenance(None)
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {ep._rel(results_file)}")
    return payload


# --------------------------------------------------------------------------- commands


def cmd_worker(args: argparse.Namespace) -> int:
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    inputs = {k: [Path(p) for p in v] for k, v in inputs.items()}
    rows = time_device(inputs, {"image": args.image_runs, "audio": args.audio_runs, "video": args.video_runs},
                       args.warmup)
    Path(args.out).write_text(json.dumps(rows), encoding="utf-8")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root
    from ml.provenance import collect_provenance

    la_root = args.asvspoof_root or default_la_root()
    if la_root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")
    if not args.faces_dir.is_dir():
        raise SystemExit(f"{args.faces_dir} not found: pass --faces-dir (the faces-140k test folder).")
    provenance = collect_provenance(args.manifest, seeds=[args.seed])
    devices = args.devices or (["cuda", "cpu"] if _cuda_available() else ["cpu"])
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="ds-latency-inputs-") as tmp:
        inputs = pick_inputs(args.manifest, la_root, args.faces_dir, Path(tmp), args.images, args.audio_files,
                             args.seed)
        inputs_file = Path(tmp) / "inputs.json"
        inputs_file.write_text(json.dumps({k: [str(p) for p in v] for k, v in inputs.items()}), encoding="utf-8")
        for device in devices:
            out = Path(tmp) / f"{device}.json"
            env = {**os.environ, "DEVICE": device}
            cmd = [sys.executable, str(Path(__file__).resolve()), "worker", "--inputs", str(inputs_file),
                   "--out", str(out), "--warmup", str(args.warmup), "--image-runs", str(args.image_runs),
                   "--audio-runs", str(args.audio_runs), "--video-runs", str(args.video_runs)]
            print(f"device {device}", flush=True)
            subprocess.run(cmd, env=env, check=True)
            rows += json.loads(out.read_text(encoding="utf-8"))
        names = {k: [p.name for p in v] for k, v in inputs.items()}

    from app.config import settings

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "timings.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    config = {
        "purpose": "End-to-end latency per modality (app.ml.pipeline.analyze), this machine",
        "hardware": hardware(),
        "inputs": {"image": {"source": "faces-140k test (half real, half StyleGAN), 256 x 256 px",
                             "files": names["image"]},
                   "audio": {"source": "ASVspoof 2019 LA dev", "files": names["audio"]},
                   "video": {"source": "synthetic 10 s, 640 x 480, 30 fps StyleGAN-face clip, no audio track",
                             "files": names["video"]}},
        "runs": {"warmup_discarded": args.warmup, "image": args.image_runs, "audio": args.audio_runs,
                 "video": args.video_runs, "devices": devices, "seed": args.seed},
        "settings": {"audio_model_source": settings.audio_model_source, "video_sample_fps": settings.video_sample_fps,
                     "video_max_frames": settings.video_max_frames,
                     "image_model_backbone": settings.image_model_backbone},
        "provenance": provenance,
    }
    (OUT_DIR / "config.json").write_text(json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8")
    summarise()
    return 0


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="measure on every device")
    run.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    run.add_argument("--asvspoof-root", type=Path, default=None)
    run.add_argument("--faces-dir", type=Path, default=FACES_TEST)
    run.add_argument("--devices", nargs="*", default=None, help="default: cuda (if available) and cpu")
    run.add_argument("--images", type=int, default=20)
    run.add_argument("--audio-files", type=int, default=20)
    run.add_argument("--seed", type=int, default=0)
    for name, default in (("warmup", 2), ("image-runs", 30), ("audio-runs", 30), ("video-runs", 8)):
        run.add_argument(f"--{name}", type=int, default=default)
    worker = sub.add_parser("worker", help=argparse.SUPPRESS)
    worker.add_argument("--inputs", required=True)
    worker.add_argument("--out", required=True)
    for name in ("warmup", "image-runs", "audio-runs", "video-runs"):
        worker.add_argument(f"--{name}", type=int, required=True)
    sub.add_parser("summarise", help="rebuild results/latency.json from the saved timings")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "worker":
        return cmd_worker(args)
    summarise()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
