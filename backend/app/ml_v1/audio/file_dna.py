"""Engine 2: Audio File DNA & Container Cybersecurity Forensics.

Combines container architecture, codec signatures, encoder fingerprinting,
trailing data attack detection, chunk-level anomaly parsing (RIFF/MP4/ID3/FLAC),
and inferred multi-generation transcoding history into a machine-readable DNA profile.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Any
import numpy as np


def analyze_audio_dna(file_path: str | Path, raw_audio_data: np.ndarray | None = None, sample_rate: int = 16000) -> dict[str, Any]:
    """Extract exhaustive Audio File DNA, container structural audit, and inferred transcoding history."""
    path = Path(file_path)
    file_bytes = path.read_bytes()
    file_size = len(file_bytes)

    dna: dict[str, Any] = {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "file_size_bytes": file_size,
        "container_format": "UNKNOWN",
        "codec": "UNKNOWN",
        "sample_rate_hz": None,
        "bit_depth": None,
        "channels": None,
        "bitrate_kbps": None,
        "bitrate_mode": "UNKNOWN",  # CBR, VBR
        "encoder_signature": "UNKNOWN",
        "container_structure_valid": True,
        "trailing_data_detected": False,
        "trailing_bytes_count": 0,
        "chunks_or_atoms": [],
        "inferred_transcoding_history": [],
        "metadata_consistency": "CONSISTENT",
        "security_flags": [],
    }

    # ------------------------------------------------------------- 1. RIFF / WAV Parsing
    if file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WAVE":
        dna["container_format"] = "RIFF/WAV"
        _parse_riff_wav(file_bytes, dna)

    # ------------------------------------------------------------- 2. MP4 / M4A / AAC ISO-BMFF
    elif len(file_bytes) >= 8 and file_bytes[4:8] in (b"ftyp", b"moov", b"mdat"):
        dna["container_format"] = "ISO-BMFF (MP4/M4A)"
        _parse_mp4_boxes(file_bytes, dna)

    # ------------------------------------------------------------- 3. FLAC
    elif file_bytes.startswith(b"fLaC"):
        dna["container_format"] = "FLAC"
        dna["codec"] = "FLAC Lossless"
        _parse_flac(file_bytes, dna)

    # ------------------------------------------------------------- 4. Ogg
    elif file_bytes.startswith(b"OggS"):
        dna["container_format"] = "Ogg Container"
        dna["codec"] = "Vorbis or Opus"
        dna["chunks_or_atoms"].append({"name": "OggS", "offset": 0, "size": file_size})

    # ------------------------------------------------------------- 5. MP3 (ID3v2 or Sync)
    elif file_bytes.startswith(b"ID3") or (len(file_bytes) >= 2 and file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0):
        dna["container_format"] = "MPEG Audio (MP3)"
        dna["codec"] = "MPEG Layer 3 (MP3)"
        _parse_id3_mp3(file_bytes, dna)

    # ------------------------------------------------------------- 6. Codec Cutoff & Transcoding History
    cutoff_khz = None
    if raw_audio_data is not None and len(raw_audio_data) > 0:
        cutoff_khz = _estimate_spectral_cutoff(raw_audio_data, sample_rate)

    _reconstruct_transcoding_history(dna, cutoff_khz, sample_rate)

    return dna


def _parse_riff_wav(data: bytes, dna: dict[str, Any]) -> None:
    """Parse RIFF/WAV chunks, headers, and check for appended trailing payloads."""
    file_size = len(data)
    try:
        riff_size = struct.unpack("<I", data[4:8])[0] + 8
        dna["expected_container_size"] = riff_size

        if file_size > riff_size:
            diff = file_size - riff_size
            dna["trailing_data_detected"] = True
            dna["trailing_bytes_count"] = diff
            dna["security_flags"].append(f"Suspicious trailing data: {diff} bytes appended after WAV EOF.")
        elif file_size < riff_size:
            dna["container_structure_valid"] = False
            dna["security_flags"].append("Truncated RIFF container: file is smaller than header specification.")

        offset = 12
        while offset + 8 <= file_size:
            chunk_id = data[offset:offset+4].decode("ascii", errors="replace")
            chunk_size = struct.unpack("<I", data[offset+4:offset+8])[0]
            dna["chunks_or_atoms"].append({"name": chunk_id, "offset": offset, "size": chunk_size})

            if chunk_id == "fmt " and chunk_size >= 16 and offset + 8 + chunk_size <= file_size:
                fmt_data = data[offset+8:offset+8+chunk_size]
                audio_format, channels, sr, byte_rate, block_align, bits_per_sample = struct.unpack(
                    "<HHIIHH", fmt_data[:16]
                )
                codec_names = {1: "PCM (Uncompressed)", 3: "IEEE Float", 6: "A-law", 7: "mu-law", 0xFFFE: "Extensible"}
                dna["codec"] = codec_names.get(audio_format, f"Format 0x{audio_format:04X}")
                dna["channels"] = channels
                dna["sample_rate_hz"] = sr
                dna["bit_depth"] = bits_per_sample
                dna["bitrate_kbps"] = round((byte_rate * 8) / 1000, 1)
                dna["bitrate_mode"] = "CBR"

            elif chunk_id == "bext":
                dna["security_flags"].append("Broadcast Wave Format (BWF) bext chunk present.")

            elif chunk_id == "iXML":
                dna["security_flags"].append("iXML production metadata present.")

            # Chunks are word-aligned (padded to 2 bytes)
            padded_size = chunk_size + (chunk_size % 2)
            offset += 8 + padded_size

    except Exception as exc:
        dna["container_structure_valid"] = False
        dna["security_flags"].append(f"RIFF parser exception: {exc}")


def _parse_mp4_boxes(data: bytes, dna: dict[str, Any]) -> None:
    """Parse ISO-BMFF box atoms for MP4/M4A."""
    file_size = len(data)
    offset = 0
    box_names = []
    try:
        while offset + 8 <= file_size:
            box_size = struct.unpack(">I", data[offset:offset+4])[0]
            box_type = data[offset+4:offset+8].decode("ascii", errors="replace")
            if box_size == 1 and offset + 16 <= file_size:
                box_size = struct.unpack(">Q", data[offset+8:offset+16])[0]
            elif box_size == 0:
                box_size = file_size - offset

            dna["chunks_or_atoms"].append({"name": box_type, "offset": offset, "size": box_size})
            box_names.append(box_type)
            if box_size <= 0:
                break
            offset += box_size

        dna["codec"] = "AAC-LC / ALAC"
        if "ftyp" in box_names and "moov" in box_names and "mdat" in box_names:
            dna["encoder_signature"] = "Standard ISO-BMFF Muxer (e.g., Apple QuickTime / FFmpeg)"
    except Exception as exc:
        dna["container_structure_valid"] = False
        dna["security_flags"].append(f"MP4 parser anomaly: {exc}")


def _parse_flac(data: bytes, dna: dict[str, Any]) -> None:
    """Parse FLAC streaminfo block."""
    try:
        if len(data) >= 42:
            # Streaminfo is first metadata block after fLaC header (offset 4)
            si = data[8:42]
            # sr is 20 bits, channels is 3 bits, bits_per_sample is 5 bits
            sr = (si[10] << 12) | (si[11] << 4) | (si[12] >> 4)
            channels = ((si[12] >> 1) & 0x07) + 1
            bits = (((si[12] & 0x01) << 4) | (si[13] >> 4)) + 1
            dna["sample_rate_hz"] = sr
            dna["channels"] = channels
            dna["bit_depth"] = bits
            dna["bitrate_mode"] = "VBR"
            dna["chunks_or_atoms"].append({"name": "STREAMINFO", "offset": 4, "size": 34})
    except Exception as exc:
        dna["security_flags"].append(f"FLAC parse error: {exc}")


def _parse_id3_mp3(data: bytes, dna: dict[str, Any]) -> None:
    """Parse ID3 tags and MP3 sync frames."""
    if data.startswith(b"ID3") and len(data) >= 10:
        major = data[3]
        tag_size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        dna["chunks_or_atoms"].append({"name": f"ID3v2.{major}", "offset": 0, "size": tag_size + 10})
        dna["encoder_signature"] = "MPEG-1/2 Audio with ID3v2 metadata"


def _estimate_spectral_cutoff(waveform: np.ndarray, sample_rate: int) -> float:
    """Estimate the effective high-frequency brickwall cutoff in kHz."""
    if len(waveform) < 1024:
        return sample_rate / 2 / 1000.0
    fft = np.abs(np.fft.rfft(waveform[:min(len(waveform), 65536)]))
    freqs = np.fft.rfftfreq(min(len(waveform), 65536), d=1.0/sample_rate) / 1000.0

    total_energy = np.sum(fft)
    if total_energy == 0:
        return sample_rate / 2 / 1000.0

    # 99.5% cumulative energy frequency
    cum = np.cumsum(fft) / total_energy
    idx = np.searchsorted(cum, 0.995)
    cutoff = freqs[min(idx, len(freqs)-1)]
    return float(cutoff)


def _reconstruct_transcoding_history(dna: dict[str, Any], cutoff_khz: float | None, sample_rate: int) -> None:
    """Reconstruct inferred multi-generation compression and transcoding history."""
    history = []
    
    # Capture stage
    history.append({
        "stage": 1,
        "type": "CAPTURE_OR_SYNTHESIS",
        "description": "Original raw capture or digital neural waveform rendering.",
        "inferred": True,
    })

    # Codec cutoff evaluation
    if cutoff_khz is not None:
        dna["high_frequency_cutoff_khz"] = round(cutoff_khz, 2)
        if cutoff_khz <= 8.5:
            history.append({
                "stage": 2,
                "type": "NARROWBAND_TRANSCODING",
                "description": f"Brickwall cutoff at {cutoff_khz:.1f} kHz indicates telephony compression (AMR-NB / G.711).",
                "inferred": True,
            })
        elif cutoff_khz <= 12.0:
            history.append({
                "stage": 2,
                "type": "LOW_BITRATE_LOSSY_ENCODING",
                "description": f"High cutoff at {cutoff_khz:.1f} kHz indicates historical transcode to low-bitrate MP3 (64-96 kbps).",
                "inferred": True,
            })
        elif cutoff_khz <= 16.5:
            history.append({
                "stage": 2,
                "type": "MESSAGING_APP_TRANSCODING",
                "description": f"Spectral cutoff at {cutoff_khz:.1f} kHz characteristic of Opus/AAC voice note transcoding (WhatsApp, Telegram).",
                "inferred": True,
            })
        else:
            history.append({
                "stage": 2,
                "type": "FULL_BAND_PRESERVATION",
                "description": f"High-frequency retention up to {cutoff_khz:.1f} kHz indicates uncompressed PCM or high-fidelity lossy encoding (>256 kbps).",
                "inferred": True,
            })

    # Current container stage
    history.append({
        "stage": len(history) + 1,
        "type": "CURRENT_CONTAINER",
        "description": f"Current encapsulation in {dna['container_format']} container using {dna['codec']}.",
        "inferred": False,
    })

    dna["inferred_transcoding_history"] = history
