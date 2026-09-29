"""Cryptographic and perceptual image hashing (Modules 3 & 4)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from PIL import Image
import imagehash


def compute_all_hashes(file_path: str | Path, image: Image.Image | None = None) -> dict[str, Any]:
    """
    Compute cryptographic hashes from file bytes and perceptual hashes from image pixels.
    """
    file_path = Path(file_path)
    file_bytes = file_path.read_bytes()

    # Module 3: Cryptographic Hashes
    md5_hash = hashlib.md5(file_bytes).hexdigest()
    sha1_hash = hashlib.sha1(file_bytes).hexdigest()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    sha512_hash = hashlib.sha512(file_bytes).hexdigest()

    # Module 4: Perceptual Hashes
    if image is None:
        with Image.open(file_path) as opened:
            pil_img = opened.convert("RGB")
    else:
        pil_img = image

    try:
        phash_val = str(imagehash.phash(pil_img))
    except Exception:
        phash_val = "unavailable"

    try:
        dhash_val = str(imagehash.dhash(pil_img))
    except Exception:
        dhash_val = "unavailable"

    try:
        ahash_val = str(imagehash.average_hash(pil_img))
    except Exception:
        ahash_val = "unavailable"

    try:
        whash_val = str(imagehash.whash(pil_img))
    except Exception:
        whash_val = "unavailable"

    return {
        "md5": md5_hash,
        "sha1": sha1_hash,
        "sha256": sha256_hash,
        "sha512": sha512_hash,
        "phash": phash_val,
        "dhash": dhash_val,
        "ahash": ahash_val,
        "whash": whash_val,
    }


def compute_hash_similarity(hash_a: str, hash_b: str) -> float:
    """Return similarity score [0.0, 1.0] between two hex hashes of equal length."""
    if not hash_a or not hash_b or hash_a == "unavailable" or hash_b == "unavailable":
        return 0.0
    try:
        ha = imagehash.hex_to_hash(hash_a)
        hb = imagehash.hex_to_hash(hash_b)
        dist = ha - hb
        max_dist = len(ha.hash.flatten())
        return round(1.0 - (dist / max_dist), 4)
    except Exception:
        return 0.0
