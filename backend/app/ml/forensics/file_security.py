"""File-level security analysis and embedded payload detection (Modules 2 & 10)."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

MAGIC_SIGNATURES = {
    "JPEG": b"\xff\xd8\xff",
    "PNG": b"\x89PNG\r\n\x1a\n",
    "GIF": (b"GIF87a", b"GIF89a"),
    "WEBP": b"RIFF",
    "TIFF_LE": b"II*\x00",
    "TIFF_BE": b"MM\x00*",
    "BMP": b"BM",
    "ICO": b"\x00\x00\x01\x00",
}


def _verify_pe_executable(file_bytes: bytes, offset: int) -> bool:
    """Verify if MZ signature is a true PE/DOS executable, not random entropy bytes."""
    if offset + 64 > len(file_bytes):
        return False
    # Check for classic DOS stub strings
    window = file_bytes[offset:offset + 512]
    if b"This program" in window or b"DOS mode" in window:
        return True
    try:
        e_lfanew = int.from_bytes(file_bytes[offset + 0x3C:offset + 0x40], byteorder="little")
        if 0 < e_lfanew < 1024 and (offset + e_lfanew + 4) <= len(file_bytes):
            if file_bytes[offset + e_lfanew:offset + e_lfanew + 4] == b"PE\x00\x00":
                return True
    except Exception:
        pass
    return False


def analyze_file_security(file_path: str | Path) -> dict[str, Any]:
    file_path = Path(file_path)
    file_bytes = file_path.read_bytes()
    file_size = len(file_bytes)
    ext = file_path.suffix.lower().lstrip(".")

    # 1. Detect Magic Bytes
    detected_format = "UNKNOWN"
    for fmt, sig in MAGIC_SIGNATURES.items():
        if isinstance(sig, tuple):
            if any(file_bytes.startswith(s) for s in sig):
                detected_format = fmt
                break
        elif file_bytes.startswith(sig):
            if fmt == "WEBP" and len(file_bytes) > 12 and file_bytes[8:12] != b"WEBP":
                continue
            detected_format = fmt
            break

    # Detect AVIF / HEIC via ftyp box
    if detected_format == "UNKNOWN" and len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp":
        major_brand = file_bytes[8:12].lower()
        if major_brand in (b"avif", b"avis"):
            detected_format = "AVIF"
        elif major_brand in (b"heic", b"heix", b"mif1", b"msf1"):
            detected_format = "HEIC" 

    # MIME Type
    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "application/octet-stream"

    # Extension Mismatch Check
    expected_extensions = {
        "JPEG": ["jpg", "jpeg", "jpe", "jfif"],
        "PNG": ["png"],
        "GIF": ["gif"],
        "WEBP": ["webp"],
        "BMP": ["bmp"],
        "TIFF_LE": ["tif", "tiff"],
        "TIFF_BE": ["tif", "tiff"],
        "AVIF": ["avif"],
        "HEIC": ["heic", "heif"],
        "ICO": ["ico"],
    }
    allowed_exts = expected_extensions.get(detected_format, [])
    extension_mismatch = (detected_format != "UNKNOWN") and (ext not in allowed_exts)

    # 2. Header & Trailer Structural Inspection & EOF Trailing Data
    trailing_data_detected = False
    trailing_bytes_count = 0
    structure_valid = True
    anomalies: list[str] = []
    eoi_offset = file_size

    if detected_format == "JPEG":
        eoi_index = file_bytes.rfind(b"\xff\xd9")
        if eoi_index == -1:
            structure_valid = False
            anomalies.append("Missing JPEG End-Of-Image (EOI 0xFFD9) marker; file may be truncated.")
        elif eoi_index + 2 < file_size:
            trailing_data_detected = True
            eoi_offset = eoi_index + 2
            trailing_bytes_count = file_size - eoi_offset
            anomalies.append(f"Detected {trailing_bytes_count} trailing bytes appended after EOF.")
    elif detected_format == "PNG":
        iend_index = file_bytes.rfind(b"IEND\xaeB`\x82")
        if iend_index == -1:
            structure_valid = False
            anomalies.append("Missing PNG IEND marker; container is corrupted or truncated.")
        elif iend_index + 8 < file_size:
            trailing_data_detected = True
            eoi_offset = iend_index + 8
            trailing_bytes_count = file_size - eoi_offset
            anomalies.append(f"Detected {trailing_bytes_count} trailing bytes after PNG IEND chunk.")

    # 3. Embedded File / Signature Scanning (Module 10)
    # Rigorous multi-byte archive signatures
    embedded_objects: list[dict[str, Any]] = []

    # Check trailing bytes first (prime location for steganography/polyglot malware)
    scan_regions = []
    if trailing_data_detected:
        scan_regions.append(("trailing_data", file_bytes[eoi_offset:], eoi_offset))
    scan_regions.append(("container", file_bytes, 0))

    strict_signatures = {
        "ZIP Archive": b"PK\x03\x04",
        "RAR Archive": b"Rar!\x1a\x07",
        "7-Zip Archive": b"7z\xbc\xaf\x27\x1c",
        "PDF Document": b"%PDF-",
        "Linux ELF Executable": b"\x7fELF",
        "GZIP Compressed": b"\x1f\x8b\x08",
        "Embedded JavaScript": b"<script",
        "PHP Script Payload": b"<?php",
    }

    found_types = set()
    for region_name, data, base_offset in scan_regions:
        for obj_name, sig in strict_signatures.items():
            if obj_name in found_types:
                continue
            pos = data.find(sig, 16 if base_offset == 0 else 0)
            if pos != -1:
                # If found in trailing data or outside header comments, flag
                if region_name == "trailing_data" or obj_name in ("ZIP Archive", "RAR Archive", "PDF Document"):
                    found_types.add(obj_name)
                    abs_pos = base_offset + pos
                    embedded_objects.append({
                        "type": obj_name,
                        "offset": abs_pos,
                        "location": region_name,
                        "suspicion": "HIGH" if region_name == "trailing_data" else "MEDIUM",
                    })
                    anomalies.append(f"Embedded payload found: {obj_name} at offset {abs_pos:#x} ({region_name}).")

        # Check PE Executable with full DOS stub verification
        mz_pos = data.find(b"MZ", 16 if base_offset == 0 else 0)
        if mz_pos != -1 and "Windows PE Executable" not in found_types:
            abs_mz = base_offset + mz_pos
            if _verify_pe_executable(file_bytes, abs_mz):
                found_types.add("Windows PE Executable")
                embedded_objects.append({
                    "type": "Windows PE Executable",
                    "offset": abs_mz,
                    "location": region_name,
                    "suspicion": "HIGH",
                })
                anomalies.append(f"Verified PE executable binary header found at offset {abs_mz:#x}.")

    if extension_mismatch:
        anomalies.append(f"File extension '.{ext}' does not match detected magic bytes '{detected_format}'.")

    # Overall File Integrity Status
    if embedded_objects or trailing_data_detected:
        file_status = "SUSPICIOUS_CONTAINER"
    elif not structure_valid or extension_mismatch:
        file_status = "ANOMALOUS_STRUCTURE"
    else:
        file_status = "VALID"

    return {
        "file_status": file_status,
        "format": detected_format,
        "mime_type": mime_type,
        "file_size_bytes": file_size,
        "extension_mismatch": extension_mismatch,
        "structure_valid": structure_valid,
        "trailing_data_detected": trailing_data_detected,
        "trailing_bytes_count": trailing_bytes_count,
        "embedded_objects": embedded_objects,
        "anomalies": anomalies,
    }
