"""Stage 1: file hashes for the analysed audio.

Computes SHA-256, SHA-512, MD5 and SHA-1 of the uploaded file in one streaming
pass, so a recipient can check that a report refers to the file they hold.
This is a record of what was analysed, not a forensic acquisition procedure:
no evidence-handling standard is claimed.
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def compute_audio_vault_hashes(file_path: str | Path) -> dict[str, str]:
    """Compute SHA-256, SHA-512, MD5, and SHA-1 in a single streaming pass (64 KB blocks)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")

    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            sha512.update(chunk)
            md5.update(chunk)
            sha1.update(chunk)

    return {
        "sha256": sha256.hexdigest(),
        "sha512": sha512.hexdigest(),
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
    }


def create_evidence_record(
    file_path: str | Path,
    source_type: str = "DIRECT_UPLOAD",
    case_reference: str | None = None,
    analyst: str | None = None,
) -> dict[str, Any]:
    """Identify the analysed file: name, size, hashes and when it was read."""
    path = Path(file_path)
    stat = path.stat()
    hashes = compute_audio_vault_hashes(path)
    
    evidence_id = f"EVID-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{hashes['sha256'][:8].upper()}"
    acquisition_time = datetime.now(timezone.utc).isoformat()

    return {
        "evidence_id": evidence_id,
        "case_reference": case_reference or f"CASE-{hashes['sha256'][:8].upper()}",
        "original_filename": path.name,
        "file_size_bytes": stat.st_size,
        "file_size_formatted": f"{stat.st_size / (1024 * 1024):.2f} MB" if stat.st_size > 1048576 else f"{stat.st_size / 1024:.2f} KB",
        "acquisition_timestamp": acquisition_time,
        "source_type": source_type,
        "analyst": analyst or "SYSTEM_INGEST",
        "hashes": hashes,
    }
