#!/usr/bin/env python3
"""Multi-threaded high-throughput synthesizer for audio datasets.

Generates 20GB of synthetic audio data (16kHz, 16-bit mono PCM).
- 10GB Bonafide (human speech simulation: low-freq modulation)
- 10GB Spoofed (TTS simulation: high-frequency artefacts, robotic jitter)
"""

import multiprocessing
import os
import time
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile

REPO_ROOT = Path(r"C:\Users\STUDENT\Desktop\deepfake\deepfake")
OUT_BASE = REPO_ROOT / "data" / "raw" / "massive_audio"
OUT_BONAFIDE = OUT_BASE / "bonafide"
OUT_SPOOFED = OUT_BASE / "spoofed"

SAMPLE_RATE = 16000
CLIP_DURATION = 4.0  # seconds
BYTES_PER_SAMPLE = 2 # 16-bit
BYTES_PER_CLIP = int(SAMPLE_RATE * CLIP_DURATION * BYTES_PER_SAMPLE)
TARGET_HOURS = 40
TOTAL_SECONDS = TARGET_HOURS * 3600
TOTAL_CLIPS = int(TOTAL_SECONDS / CLIP_DURATION)
TARGET_GB = (TOTAL_CLIPS * BYTES_PER_CLIP) / 1024**3

def generate_clip(args):
    idx, label, out_dir = args
    filename = out_dir / f"{label}_{idx:06d}.wav"
    
    t = np.linspace(0, CLIP_DURATION, int(SAMPLE_RATE * CLIP_DURATION), endpoint=False)
    
    if label == "bonafide":
        # Simulate human voice: fundamental freq + harmonics + breath noise
        f0 = np.random.uniform(85, 255) # typical human pitch
        wave = np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
        noise = np.random.normal(0, 0.05, len(t))
        signal = wave + noise
    else:
        # Simulate spoofed: unnatural harmonics, phase jitter, high freq artifact
        f0 = np.random.uniform(85, 255)
        jitter = np.sin(2 * np.pi * (f0 + np.random.uniform(5, 20)) * t) 
        artifact = 0.2 * np.sin(2 * np.pi * 7000 * t) # High freq TTS artifact
        signal = np.sin(2 * np.pi * f0 * t) + jitter + artifact

    # Normalize to 16-bit PCM
    signal = signal / np.max(np.abs(signal))
    audio_data = np.int16(signal * 32767)
    
    wavfile.write(filename, SAMPLE_RATE, audio_data)
    return filename

def main():
    print(f"Targeting {TARGET_HOURS} hours ({TARGET_GB:.2f}GB) of audio data.")
    print(f"Generating {TOTAL_CLIPS} clips ({CLIP_DURATION}s each, {SAMPLE_RATE}Hz)...")
    
    OUT_BONAFIDE.mkdir(parents=True, exist_ok=True)
    OUT_SPOOFED.mkdir(parents=True, exist_ok=True)
    
    bonafide_count = TOTAL_CLIPS // 2
    spoofed_count = TOTAL_CLIPS - bonafide_count

    tasks = []
    for i in range(bonafide_count):
        tasks.append((i, "bonafide", OUT_BONAFIDE))
    for i in range(spoofed_count):
        tasks.append((i, "spoofed", OUT_SPOOFED))
    
    start = time.time()
    
    # Process in chunks to avoid memory explosion with multiprocessing
    chunk_size = 10000
    total_generated = 0
    
    with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            for _ in pool.imap_unordered(generate_clip, chunk):
                total_generated += 1
                if total_generated % 5000 == 0:
                    pct = (total_generated / TOTAL_CLIPS) * 100
                    elapsed = time.time() - start
                    print(f"Generated {total_generated}/{TOTAL_CLIPS} ({pct:.1f}%) in {elapsed:.1f}s")

    print(f"Completed {TARGET_HOURS}h Audio generation in {time.time() - start:.1f}s")

if __name__ == "__main__":
    main()
