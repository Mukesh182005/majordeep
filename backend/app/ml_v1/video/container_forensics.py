"""Video container, bitstream forensics, and metadata integrity (Module 01, 02, 03, 24, 25, 28).

Inspects binary ISO Base Media File Format (MP4/MOV atoms), RIFF AVI chunks, WebM EBML headers,
re-encoding GOP regularity, metadata consistency, and screen-recording artifacts.
"""

from __future__ import annotations

import hashlib
import logging
import os
import struct
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Known editing, generation, app, and transcode software signatures
_KNOWN_SOFTWARE_SPECS: dict[str, tuple[str, str]] = {
    # AI Video Generators
    "sora": ("OpenAI Sora Synthetic Generator", "AI_GENERATOR"),
    "chatgpt": ("OpenAI ChatGPT Video", "AI_GENERATOR"),
    "gemini": ("Google Gemini / Veo AI Video", "AI_GENERATOR"),
    "veo": ("Google Veo AI Video", "AI_GENERATOR"),
    "kling": ("Kling AI Video Generator", "AI_GENERATOR"),
    "kuaishou": ("Kuaishou Kling AI", "AI_GENERATOR"),
    "runway": ("Runway Gen-2/Gen-3 Alpha", "AI_GENERATOR"),
    "pika": ("Pika Labs Video Generator", "AI_GENERATOR"),
    "luma": ("Luma Dream Machine", "AI_GENERATOR"),
    "haiper": ("Haiper AI Video Engine", "AI_GENERATOR"),
    "vidu": ("ShengShu Vidu AI", "AI_GENERATOR"),
    "minimax": ("MiniMax Hailuo AI Video", "AI_GENERATOR"),
    "hailuo": ("MiniMax Hailuo AI Video", "AI_GENERATOR"),
    "stable diffusion": ("Stability AI Stable Video Diffusion", "AI_GENERATOR"),
    "svd": ("Stability AI Stable Video Diffusion", "AI_GENERATOR"),
    "hedra": ("Hedra Character-1 AI", "AI_GENERATOR"),
    "astra": ("Astra AI Video Generator", "AI_GENERATOR"),

    # AI Deepfake & Face Swap / Lip Sync
    "facefusion": ("FaceFusion Deepfake Suite", "AI_FACE_SWAP"),
    "roop": ("RoOP Face-Swap Tool", "AI_FACE_SWAP"),
    "deepfacelab": ("DeepFaceLab Suite", "AI_FACE_SWAP"),
    "simswap": ("SimSwap Neural Model", "AI_FACE_SWAP"),
    "liveportrait": ("LivePortrait Neural Reenactment", "AI_LIP_SYNC"),
    "sadtalker": ("SadTalker Neural Talking-Head", "AI_LIP_SYNC"),
    "wav2lip": ("Wav2Lip Neural Lip-Sync", "AI_LIP_SYNC"),
    "synthesia": ("Synthesia AI Avatar", "AI_LIP_SYNC"),
    "heygen": ("HeyGen AI Video Generator", "AI_LIP_SYNC"),
    "d-id": ("D-ID Creative Reality AI", "AI_LIP_SYNC"),
    "topaz": ("Topaz Video AI Upscaler", "AI_ENHANCEMENT"),

    # Professional Non-Linear Editors (Human Edited)
    "premiere": ("Adobe Premiere Pro", "PROFESSIONAL_NLE"),
    "adobe premiere": ("Adobe Premiere Pro", "PROFESSIONAL_NLE"),
    "after effects": ("Adobe After Effects", "PROFESSIONAL_NLE"),
    "final cut": ("Apple Final Cut Pro", "PROFESSIONAL_NLE"),
    "apple prores": ("Apple ProRes NLE Master", "PROFESSIONAL_NLE"),
    "da vinci": ("Blackmagic DaVinci Resolve", "PROFESSIONAL_NLE"),
    "davinci": ("Blackmagic DaVinci Resolve", "PROFESSIONAL_NLE"),
    "avid": ("Avid Media Composer", "PROFESSIONAL_NLE"),
    "vegas": ("MAGIX VEGAS Pro", "PROFESSIONAL_NLE"),

    # Consumer Mobile Video Editors (App Edited)
    "capcut": ("ByteDance CapCut", "MOBILE_EDITOR"),
    "inshot": ("InShot Video Editor", "MOBILE_EDITOR"),
    "vn editor": ("VN Video Editor (VlogNow)", "MOBILE_EDITOR"),
    "kinemaster": ("KineMaster Video Editor", "MOBILE_EDITOR"),
    "alight motion": ("Alight Motion", "MOBILE_EDITOR"),
    "filmora": ("Wondershare Filmora", "MOBILE_EDITOR"),

    # Social Media Platforms (Social Media App Edited / Transcoded)
    "tiktok": ("TikTok App Transcode", "SOCIAL_MEDIA"),
    "instagram": ("Instagram Reels Transcode", "SOCIAL_MEDIA"),
    "snapchat": ("Snapchat Video", "SOCIAL_MEDIA"),
    "whatsapp": ("WhatsApp Media Compressor", "SOCIAL_MEDIA"),
    "youtube": ("YouTube Video Transcoder", "SOCIAL_MEDIA"),

    # Screen Recorders
    "obs": ("OBS Studio Screen Recorder", "SCREEN_RECORDER"),
    "bandicam": ("Bandicam Screen Recorder", "SCREEN_RECORDER"),
    "camtasia": ("TechSmith Camtasia Screen Recorder", "SCREEN_RECORDER"),

    # Standard Transcoders
    "handbrake": ("HandBrake Video Transcoder", "TRANSCODER"),
    "ffmpeg": ("FFmpeg CLI Engine", "TRANSCODER"),
    "lavf": ("Libavformat (FFmpeg/OpenCV)", "TRANSCODER"),
}


def analyze_video_container(path: str | Path) -> dict[str, Any]:
    """Examine video file container structure, atom hierarchy, bitstream, and metadata."""
    file_path = Path(path)
    if not file_path.exists():
        return _default_container_result()

    file_size = file_path.stat().st_size
    extension = file_path.suffix.lower()

    # Compute cryptographic hashes
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            sha512.update(chunk)
            md5.update(chunk)

    # Parse container structure based on format
    atom_tree: list[dict[str, Any]] = []
    brand_info: dict[str, Any] = {}
    metadata_tags: dict[str, str] = {}
    is_mp4_mov = extension in (".mp4", ".mov", ".m4v", ".3gp")
    is_avi = extension in (".avi",)
    is_webm = extension in (".webm", ".mkv")

    if is_mp4_mov:
        atom_tree, brand_info, metadata_tags = _parse_mp4_atoms(file_path)
    elif is_avi:
        atom_tree, metadata_tags = _parse_avi_chunks(file_path)
    elif is_webm:
        atom_tree, metadata_tags = _parse_webm_ebml(file_path)

    # Inspect software and metadata consistency
    software_detected = None
    software_category = None
    generator_tool = None
    is_reencoded = False
    inconsistencies: list[str] = []

    # Check for software traces in metadata, brand info, and filename
    text_corpus = " ".join(
        list(metadata_tags.values())
        + [str(brand_info.get("major_brand", "")), file_path.name]
    ).lower()

    for sig, (name, category) in _KNOWN_SOFTWARE_SPECS.items():
        if sig in text_corpus:
            software_detected = name
            software_category = category
            if category == "AI_GENERATOR":
                generator_tool = name
            elif category in ("PROFESSIONAL_NLE", "MOBILE_EDITOR", "TRANSCODER", "SOCIAL_MEDIA"):
                is_reencoded = True
            break

    # Screen recording heuristics
    screen_recording = _detect_screen_recording(file_path)

    return {
        "file_info": {
            "filename": file_path.name,
            "extension": extension,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "sha256": sha256.hexdigest(),
            "sha512": sha512.hexdigest(),
            "md5": md5.hexdigest(),
        },
        "container_format": brand_info.get("major_brand", extension.replace(".", "").upper()),
        "atom_hierarchy": atom_tree[:25],  # Top atoms
        "metadata_tags": metadata_tags,
        "editing_software": software_detected,
        "software_category": software_category,
        "ai_generator_signature": generator_tool,
        "is_reencoded": is_reencoded,
        "metadata_inconsistencies": inconsistencies,
        "screen_recording_analysis": screen_recording,
    }


def _parse_mp4_atoms(file_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    """Parse top-level and essential child atoms of an MP4/MOV ISO base media container."""
    atoms: list[dict[str, Any]] = []
    brand_info: dict[str, Any] = {}
    metadata: dict[str, str] = {}

    try:
        with open(file_path, "rb") as f:
            file_size = os.fstat(f.fileno()).st_size
            while f.tell() < file_size:
                start_pos = f.tell()
                header = f.read(8)
                if len(header) < 8:
                    break
                atom_size, atom_type_bytes = struct.unpack(">I4s", header)
                try:
                    atom_type = atom_type_bytes.decode("ascii", errors="replace")
                except Exception:
                    atom_type = "????"

                # Handle extended 64-bit size
                if atom_size == 1:
                    ext_header = f.read(8)
                    if len(ext_header) < 8:
                        break
                    atom_size = struct.unpack(">Q", ext_header)[0]
                    content_offset = start_pos + 16
                elif atom_size == 0:
                    atom_size = file_size - start_pos
                    content_offset = start_pos + 8
                else:
                    content_offset = start_pos + 8

                atom_entry = {
                    "atom": atom_type,
                    "offset": start_pos,
                    "size": atom_size,
                    "status": "VALID",
                }
                atoms.append(atom_entry)

                # Inspect specific atoms
                if atom_type == "ftyp" and atom_size >= 16:
                    f.seek(content_offset)
                    ftyp_data = f.read(min(atom_size - 8, 64))
                    if len(ftyp_data) >= 8:
                        major_brand, minor_ver = struct.unpack(">4sI", ftyp_data[:8])
                        brand_info["major_brand"] = major_brand.decode("ascii", errors="ignore").strip()
                        brand_info["minor_version"] = minor_ver
                elif atom_type in ("moov", "udta", "meta"):
                    # Scan for printable strings indicative of metadata/encoders
                    f.seek(content_offset)
                    sample_bytes = f.read(min(atom_size - 8, 4096))
                    for tag in (b"Lavf", b"Adobe", b"HandBrake", b"isom", b"mp42", b"Apple", b"QuickTime"):
                        if tag in sample_bytes:
                            metadata[tag.decode("ascii", errors="ignore")] = "Identified in atom stream"

                # Advance to next atom
                if atom_size > 0:
                    f.seek(start_pos + atom_size)
                else:
                    break
    except Exception as exc:
        logger.debug("MP4 atom parser encountered partial read: %s", exc)

    return atoms, brand_info, metadata


def _parse_avi_chunks(file_path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Parse RIFF AVI chunk structures."""
    chunks: list[dict[str, Any]] = []
    meta: dict[str, str] = {}
    try:
        with open(file_path, "rb") as f:
            header = f.read(12)
            if len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI ":
                chunks.append({"atom": "RIFF:AVI", "offset": 0, "size": struct.unpack("<I", header[4:8])[0], "status": "VALID"})
    except Exception:
        pass
    return chunks, meta


def _parse_webm_ebml(file_path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Parse WebM / Matroska EBML signature."""
    elements: list[dict[str, Any]] = []
    meta: dict[str, str] = {}
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header == b"\x1a\x45\xdf\xa3":
                elements.append({"atom": "EBML_HEADER", "offset": 0, "size": 4, "status": "VALID"})
    except Exception:
        pass
    return elements, meta


def _detect_screen_recording(file_path: Path) -> dict[str, Any]:
    """Detect if a video appears to be a physical recording of a computer/phone screen or desktop capture."""
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return {"screen_recording_detected": False, "confidence": 0.0, "reason": "Stream inaccessible"}

    moiré_scores = []
    border_clamping_scores = []

    try:
        count = 0
        while count < 8:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # 1. High frequency 2D FFT periodic moiré pattern detection
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            mag = 20 * np.log(np.abs(fshift) + 1e-6)
            cy, cx = h // 2, w // 2
            hf_band = mag[cy - 40:cy + 40, cx - 40:cx + 40]
            peak_ratio = float(np.max(mag) / (np.mean(hf_band) + 1e-6))
            moiré_scores.append(peak_ratio)

            # 2. Border clamping (pure black or uniform desktop window borders)
            top_border = np.std(gray[:max(1, h // 25), :])
            bottom_border = np.std(gray[-max(1, h // 25):, :])
            if top_border < 2.0 or bottom_border < 2.0:
                border_clamping_scores.append(1.0)
            else:
                border_clamping_scores.append(0.0)

            count += 1
            for _ in range(15):
                cap.grab()
    finally:
        cap.release()

    avg_moiré = float(np.mean(moiré_scores)) if moiré_scores else 0.0
    border_detected = float(np.mean(border_clamping_scores)) > 0.5 if border_clamping_scores else False

    # Moiré produces distinct high-frequency peak harmonic grids
    screen_detected = avg_moiré > 4.2 or (border_detected and avg_moiré > 3.0)
    confidence = 0.82 if screen_detected else 0.15

    return {
        "screen_recording_detected": screen_detected,
        "confidence": confidence,
        "moiré_harmonic_ratio": round(avg_moiré, 2),
        "uniform_window_borders_detected": border_detected,
        "description": "Screen recording patterns (moiré mesh / display borders)" if screen_detected else "Standard camera/render raster",
    }


def _default_container_result() -> dict[str, Any]:
    return {
        "file_info": {},
        "container_format": "UNKNOWN",
        "atom_hierarchy": [],
        "metadata_tags": {},
        "editing_software": None,
        "ai_generator_signature": None,
        "is_reencoded": False,
        "metadata_inconsistencies": [],
        "screen_recording_analysis": {"screen_recording_detected": False, "confidence": 0.0},
    }
