#!/usr/bin/env python3
"""Write the small upload fixtures the browser tests use (none of them is committed).

  real.jpg      a real photo from accuracy_test/100_real
  ai.jpg        an AI image from accuracy_test/100_ai
  speech.wav    5 s, 16 kHz mono, a synthetic voiced signal
  clip.mp4      5 s, 10 fps, 320x240 synthetic video (no real face: the face-swap branch is
                exercised only as "no face found")
  not_image.jpg a text file renamed to .jpg

Run from the repository root:  python frontend/e2e/fixtures/make_fixtures.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SR = 16000


def first_image(folder: Path) -> Path:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not files:
        raise SystemExit(f"no image in {folder}")
    return files[0]


def main() -> None:
    shutil.copyfile(first_image(REPO / "accuracy_test" / "100_real"), HERE / "real.jpg")
    shutil.copyfile(first_image(REPO / "accuracy_test" / "100_ai"), HERE / "ai.jpg")

    import soundfile as sf

    t = np.arange(5 * SR) / SR
    f0 = 140 + 8 * np.sin(2 * np.pi * 4.5 * t)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    voiced = sum((0.6 / k) * np.sin(k * phase) for k in range(1, 12))
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 2.0 * t - np.pi / 2))
    rng = np.random.default_rng(0)
    sf.write(HERE / "speech.wav", (0.3 * voiced * envelope + 0.005 * rng.standard_normal(t.size)).astype(np.float32),
             SR, subtype="PCM_16")

    import cv2

    writer = cv2.VideoWriter(str(HERE / "clip.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (320, 240))
    for i in range(50):
        frame = np.full((240, 320, 3), 40 + i, dtype=np.uint8)
        cv2.circle(frame, (160 + int(40 * np.sin(i / 8)), 120), 50, (200, 180, 160), -1)
        writer.write(frame)
    writer.release()

    (HERE / "not_image.jpg").write_text("This is a text file, not a JPEG image.\n", encoding="utf-8")
    print("fixtures written to", HERE)


if __name__ == "__main__":
    main()
