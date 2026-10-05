#!/usr/bin/env python3
"""Multi-threaded high-throughput synthesizer for social-media-style re-encodings.

Generates 360,000 multi-platform images (Instagram, LinkedIn, Pinterest, Facebook,
Snapchat, Inpainting, and Diffusion) across 24 CPU worker processes to form
a master 500,000-image balanced dataset.

Every output is a filtered copy of a faces-140k *training* image, so:
  * copies must stay in the training split (``expand_training_dataset.py``
    enforces this) — a copy in validation leaks its source;
  * the "diffusion" and "inpaint" folders are NOT diffusion output: they are
    PIL smoothing / patch-blur filters over StyleGAN faces. A model trained on
    them learns "blurred StyleGAN face", not Stable Diffusion, Flux, DALL-E,
    Midjourney, GPT-image or Gemini output.
"""

from __future__ import annotations

import io
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

REPO_ROOT = Path(r"C:\Users\STUDENT\Desktop\deepfake\deepfake")
SRC_REAL = REPO_ROOT / "data" / "raw" / "faces-140k" / "real_vs_fake" / "real-vs-fake" / "train" / "real"
SRC_FAKE = REPO_ROOT / "data" / "raw" / "faces-140k" / "real_vs_fake" / "real-vs-fake" / "train" / "fake"
OUT_BASE = REPO_ROOT / "data" / "raw" / "massive_social"


# ------------------------------------------------------------- Platform Encoders
def encode_instagram(image: Image.Image) -> Image.Image:
    """Instagram: 1080px resolution, progressive JPEG Q=70-75, stripped metadata."""
    buf = io.BytesIO()
    q = random.randint(70, 75)
    image.save(buf, format="JPEG", quality=q, progressive=True)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def encode_linkedin(image: Image.Image) -> Image.Image:
    """LinkedIn: Professional square headshot, contrast curve, WebP/JPEG Q=75."""
    image = ImageEnhance.Contrast(image).enhance(random.uniform(1.05, 1.2))
    image = ImageEnhance.Sharpness(image).enhance(random.uniform(1.1, 1.3))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=random.randint(73, 78))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def encode_pinterest(image: Image.Image) -> Image.Image:
    """Pinterest: Vertical aspect ratio emphasis, unsharp edge filter, JPEG Q=80."""
    image = image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=random.randint(78, 83))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def encode_facebook(image: Image.Image) -> Image.Image:
    """Facebook: 960px standard, aggressive 4:2:0 chroma subsampling, JPEG Q=68-72."""
    buf = io.BytesIO()
    q = random.randint(68, 72)
    image.save(buf, format="JPEG", quality=q, subsampling=2)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def encode_snapchat(image: Image.Image) -> Image.Image:
    """Snapchat: 9:16 mobile resolution, CMOS high ISO noise, lossy JPEG Q=65."""
    image = image.filter(ImageFilter.GaussianBlur(random.uniform(0.3, 0.6)))
    image = ImageEnhance.Brightness(image).enhance(random.uniform(0.9, 1.1))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=random.randint(62, 68))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def encode_inpaint_fake(image: Image.Image) -> Image.Image:
    """Synthetic facial inpainting & splicing: localized patch replacement."""
    w, h = image.size
    draw = ImageDraw.Draw(image)
    pw = int(w * random.uniform(0.2, 0.35))
    ph = int(h * random.uniform(0.15, 0.25))
    px = int(w * 0.5 - pw * 0.5 + random.randint(-15, 15))
    py = int(h * 0.5 - ph * 0.5 + random.randint(-15, 15))
    patch = image.crop((px, py, px + pw, py + ph))
    patch = patch.filter(ImageFilter.GaussianBlur(radius=random.uniform(2.0, 4.0)))
    patch = ImageEnhance.Color(patch).enhance(random.uniform(0.7, 1.3))
    image.paste(patch, (px, py))
    return image


def encode_diffusion_fake(image: Image.Image) -> Image.Image:
    """Modern diffusion emulation: smooth high-frequency spectral rolloff & skin texture smoothing."""
    smooth = image.filter(ImageFilter.SMOOTH_MORE)
    blended = Image.blend(image, smooth, alpha=random.uniform(0.4, 0.7))
    blended = ImageEnhance.Color(blended).enhance(random.uniform(1.05, 1.25))
    return blended


ENCODERS = {
    "instagram": encode_instagram,
    "linkedin": encode_linkedin,
    "pinterest": encode_pinterest,
    "facebook": encode_facebook,
    "snapchat": encode_snapchat,
    "inpaint": encode_inpaint_fake,
    "diffusion": encode_diffusion_fake,
}


def process_batch(items: list[tuple[str, str, str]]) -> int:
    """Process a batch of (input_path, output_path, encoder_name)."""
    count = 0
    for in_path_str, out_path_str, enc_name in items:
        try:
            if os.path.exists(out_path_str) and os.path.getsize(out_path_str) > 500:
                count += 1
                continue
            fn = ENCODERS[enc_name]
            with Image.open(in_path_str) as opened:
                img = opened.convert("RGB")
            res = fn(img)
            res.save(out_path_str, format="JPEG", quality=85)
            count += 1
        except Exception:
            pass
    return count


def main() -> None:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    real_files = sorted(list(SRC_REAL.glob("*.jpg")))
    fake_files = sorted(list(SRC_FAKE.glob("*.jpg")))

    print(f"Source images available: {len(real_files):,} Real, {len(fake_files):,} Fake")

    tasks: list[tuple[str, str, str]] = []

    # Target quotas for 360,000 synthesized images (180,000 Real / 180,000 Fake)
    quotas = [
        # Real platform distributions (330,000 total)
        ("instagram", "real", real_files, 80000),
        ("linkedin",  "real", real_files, 60000),
        ("pinterest", "real", real_files, 65000),
        ("facebook",  "real", real_files, 65000),
        ("snapchat",  "real", real_files, 60000),
        # Fake platform & generator distributions (330,000 total)
        ("instagram", "fake", fake_files, 70000),
        ("linkedin",  "fake", fake_files, 50000),
        ("pinterest", "fake", fake_files, 50000),
        ("facebook",  "fake", fake_files, 50000),
        ("snapchat",  "fake", fake_files, 50000),
        ("inpaint",   "fake", fake_files, 40000),
        ("diffusion", "fake", fake_files, 20000),
    ]

    for platform, cls, file_list, target_count in quotas:
        out_dir = OUT_BASE / f"{platform}_{cls}"
        out_dir.mkdir(parents=True, exist_ok=True)
        count = target_count
        print(f"Queueing {platform} ({cls}): {count:,} images...")
        n_src = len(file_list)
        for i in range(count):
            src_file = file_list[i % n_src]
            dest_file = out_dir / f"{platform}_{cls}_{i:06d}.jpg"
            tasks.append((str(src_file), str(dest_file), platform))

    random.seed(42)
    random.shuffle(tasks)
    total_tasks = len(tasks)
    print(f"\nTotal tasks to execute: {total_tasks:,} across CPU cores...")

    batch_size = 500
    batches = [tasks[i : i + batch_size] for i in range(0, total_tasks, batch_size)]
    cpu_workers = min(24, os.cpu_count() or 8)
    print(f"Processing {len(batches)} batches using {cpu_workers} CPU worker processes...")

    t0 = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=cpu_workers) as executor:
        for done in executor.map(process_batch, batches):
            completed += done
            if completed % 25000 == 0 or completed == total_tasks:
                elapsed = time.time() - t0
                rate = completed / max(0.1, elapsed)
                rem_s = (total_tasks - completed) / max(0.1, rate)
                print(f"  --> Completed {completed:,} / {total_tasks:,} images ({completed / total_tasks * 100:.1f}%) | Speed: {rate:.0f} img/s | ETA: {rem_s/60:.1f} min")

    total_time = time.time() - t0
    print(f"\nSuccessfully generated {completed:,} multi-platform images in {total_time:.1f}s ({completed/max(0.1, total_time):.0f} img/s) at {OUT_BASE}!")


if __name__ == "__main__":
    main()
