#!/usr/bin/env python3
"""Phase 7 timing: the current video pipeline vs dense sampling for the pulse and flow stages.

A decision aid, not a detection result. Three synthetic 640x480, 30 fps clips
(10 s, 30 s, 60 s) of StyleGAN faces from faces-140k (no real person), with a
slow pan/zoom and a faint 1.2 Hz brightness modulation. No audio track (ffmpeg
is not installed); the audio stage is timed separately on concatenated
ASVspoof 2019 LA dev bona fide speech.

For each clip: ``analyze_video`` end to end with its per-stage times, then the
extra cost of a dense window (10 s at 10 fps around the keyframe): decoding,
face detection on every frame, the pulse stage and the optical-flow stage.

Writes ``paper_results/video_timing/timing.json`` with provenance.

Usage (PowerShell, from the repository root, DEEPSENTINEL_DATA set)::

    python ml/evaluation/video_pipeline_timing.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "paper_results/video_timing/timing.json"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

FPS, W, H = 30, 640, 480
LENGTHS = (10, 30, 60)
DENSE_FPS, DENSE_SECONDS = 10, 10


def make_video(face_path: Path, seconds: int, out: Path) -> None:
    face = np.asarray(Image.open(face_path).convert("RGB").resize((360, 360)), dtype=np.float32)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for k in range(seconds * FPS):
        t = k / FPS
        canvas = np.full((H, W, 3), 40.0, dtype=np.float32)
        scale = 1.0 + 0.05 * np.sin(2 * np.pi * t / 7)
        size = int(360 * scale)
        tile = cv2.resize(face, (size, size))
        x = int(W / 2 - size / 2 + 40 * np.sin(2 * np.pi * t / 11))
        y = int(H / 2 - size / 2 + 10 * np.sin(2 * np.pi * t / 5))
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + size), min(H, y + size)
        canvas[y0:y1, x0:x1] = tile[y0 - y:y1 - y, x0 - x:x1 - x]
        canvas *= 1.0 + 0.01 * np.sin(2 * np.pi * 1.2 * t)
        writer.write(cv2.cvtColor(np.clip(canvas, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    writer.release()


def dense_window(path: Path, centre_s: float) -> list[tuple[float, Image.Image]]:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start = max(0, int((centre_s - DENSE_SECONDS / 2) * fps))
    stop = min(total, start + int(DENSE_SECONDS * fps))
    step = max(1, round(fps / DENSE_FPS))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames = []
    for index in range(start, stop):
        ok, frame = cap.read()
        if not ok:
            break
        if (index - start) % step == 0:
            frames.append((index / fps, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))
    cap.release()
    return frames


def main() -> None:
    import torch
    from app.ml.faces import extract_faces
    from app.ml.video import analyze_video
    from app.ml.video.optical_flow import compute_optical_flow_anomaly
    from app.ml.video.rppg_biometrics import extract_rppg_biometrics

    faces = sorted((REPO / "data/raw/faces-140k/real_vs_fake/real-vs-fake/test/fake").glob("*.jpg"))[:3]
    work = Path(tempfile.mkdtemp(prefix="ds-video-timing-"))
    videos = []
    for face, seconds in zip(faces, LENGTHS, strict=True):
        path = work / f"synthetic_{seconds}s.mp4"
        make_video(face, seconds, path)
        videos.append(path)
    print("videos written", flush=True)

    analyze_video(videos[0], work / "warmup", "warmup")  # model loading
    results = {"device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
               "note": "other jobs (one CPU-bound audio run) were running at the same time",
               "videos": []}
    for path in videos:
        t0 = time.perf_counter()
        res = analyze_video(path, work / path.stem, path.stem)
        total_s = time.perf_counter() - t0
        ev = res.evidence
        stages = {m["stage"]: m["duration_ms"] for m in ev["pipeline_modules"]}
        keyframe_s = ev["worst_frame_timestamp_s"]

        t1 = time.perf_counter()
        dense = dense_window(path, keyframe_s)
        decode_s = time.perf_counter() - t1
        t1 = time.perf_counter()
        boxes = [extract_faces(img)[0].box for _, img in dense]
        faces_s = time.perf_counter() - t1
        t1 = time.perf_counter()
        rppg = extract_rppg_biometrics(dense, boxes)
        rppg_s = time.perf_counter() - t1
        t1 = time.perf_counter()
        motion, _ = compute_optical_flow_anomaly([np.array(img) for _, img in dense], boxes)
        flow_s = time.perf_counter() - t1
        results["videos"].append({
            "video": path.name,
            "duration_s": ev.get("duration_seconds"),
            "frames_sampled_now": ev["frames_analysed"],
            "faces_detected_now": ev["faces_detected_in_frames"],
            "current_total_s": round(total_s, 2),
            "current_stage_ms": stages,
            "current_rppg_status": ev["rppg_biometrics"].get("status"),
            "dense_frames": len(dense),
            "dense_faces_detected": sum(b is not None for b in boxes),
            "dense_decode_s": round(decode_s, 2),
            "dense_face_detection_s": round(faces_s, 2),
            "dense_rppg_s": round(rppg_s, 2),
            "dense_optical_flow_s": round(flow_s, 2),
            "dense_extra_total_s": round(decode_s + faces_s + rppg_s + flow_s, 2),
            "dense_rppg_status": rppg.get("status"),
            "dense_rppg_pulse_detected": rppg.get("biometric_pulse_detected"),
            "dense_rppg_bpm": rppg.get("estimated_heart_rate_bpm"),
        })
        print(json.dumps(results["videos"][-1]), flush=True)

    # Audio stage on speech of the same lengths (ASVspoof 2019 LA dev bona fide, concatenated).
    from app.ml.audio import run_comprehensive_audio_forensics
    from app.ml.preprocessing import load_audio, normalize_waveform
    from ml.common import read_manifest

    la = Path(os.environ["DEEPSENTINEL_DATA"]) / "ASVspoof2019" / "LA"
    bona = [r for r in read_manifest(REPO / "data/processed/asvspoof2019_la/manifest.csv", "dev") if r["label"] == 0]
    speech = np.concatenate([load_audio(la / r["relative_path"], 16000)[0] for r in bona[:40]])
    results["audio"] = []
    for seconds in LENGTHS:
        wave = normalize_waveform(speech[: seconds * 16000])
        times = []
        for _ in range(2):
            t1 = time.perf_counter()
            run_comprehensive_audio_forensics(la / bona[0]["relative_path"], wave, 16000, str(work / "audio"), "timing")
            times.append(time.perf_counter() - t1)
        results["audio"].append({"seconds": seconds, "run_s": [round(t, 2) for t in times]})
        print(json.dumps(results["audio"][-1]), flush=True)
    results["median_current_total_s"] = statistics.median(v["current_total_s"] for v in results["videos"])
    from ml.provenance import collect_provenance

    results["provenance"] = collect_provenance()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
