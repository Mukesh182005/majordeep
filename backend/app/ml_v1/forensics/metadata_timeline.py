"""Metadata security analysis, EXIF inspection, and digital timeline reconstruction (Modules 11 & 12)."""

from __future__ import annotations

import datetime
import io
import math
from pathlib import Path
from typing import Any
from PIL import Image, ExifTags, ImageCms

SUSPICIOUS_SOFTWARE = [
    "photoshop", "gimp", "canva", "midjourney", "stable diffusion",
    "dall-e", "comfyui", "automatic1111", "faceapp", "deepfacelab",
    "lightroom", "affinity", "pixelmator", "snapseed", "picsart", "vsco",
    "roop", "facefusion", "simswap", "insightface", "remaker", "swapface",
    "davinci", "premiere", "after effects", "lightcut", "capcut", "kinemaster",
    "inshot", "facetune", "b612", "retrica", "snow", "meitu"
]

AI_GENERATOR_KEYWORDS = [
    "midjourney", "stable diffusion", "dall-e", "dalle", "comfyui",
    "automatic1111", "novelai", "invokeai", "bing image creator", "firefly",
    "chatgpt", "openai", "gemini", "imagen", "flux", "ideogram", "runway",
    "pika", "sora", "kling", "luma", "adobe firefly", "deepfloyd", "wombo"
]


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def _format_exposure_time(val: Any) -> str:
    try:
        f = float(val)
        if f <= 0:
            return str(val)
        if f < 1.0:
            denom = round(1.0 / f)
            return f"1/{denom} sec"
        return f"{f:.2f} sec"
    except Exception:
        return str(val)


def _format_f_number(val: Any) -> str:
    try:
        f = float(val)
        return f"f/{f:.1f}"
    except Exception:
        return f"f/{val}"


def _format_focal_length(val: Any) -> str:
    try:
        f = float(val)
        return f"{f:.1f} mm"
    except Exception:
        return f"{val} mm"


def _convert_gps_coords(coord: tuple, ref: str) -> str:
    try:
        degrees = float(coord[0])
        minutes = float(coord[1])
        seconds = float(coord[2])
        dec = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            dec = -dec
        return f"{degrees:.0f}° {minutes:.0f}' {seconds:.1f}\" {ref} ({dec:.5f}°)"
    except Exception:
        return f"{coord} {ref}"


def analyze_metadata_and_timeline(file_path: str | Path, image: Image.Image | None = None) -> dict[str, Any]:
    file_path = Path(file_path)
    stat = file_path.stat() if file_path.exists() else None
    file_size_bytes = stat.st_size if stat else 0

    # Handle image loading safely
    pil_img = None
    if image is not None:
        pil_img = image
    elif file_path.exists():
        try:
            with Image.open(file_path) as opened:
                pil_img = opened.copy()
        except Exception:
            pil_img = None

    # Default file container values
    if pil_img is not None:
        file_format = pil_img.format or file_path.suffix.lstrip(".").upper() or "UNKNOWN"
        width, height = pil_img.size
        mp = round((width * height) / 1_000_000, 2)
        
        # Calculate aspect ratio
        gcd = math.gcd(width, height) if width > 0 and height > 0 else 1
        ar_w = width // gcd
        ar_h = height // gcd
        if ar_w > 50 or ar_h > 50:
            aspect_ratio_str = f"{width / max(1, height):.2f}:1"
        else:
            aspect_ratio_str = f"{ar_w}:{ar_h} ({width / max(1, height):.2f}:1)"

        mode_map = {
            "RGB": "RGB (24-bit True Color)",
            "RGBA": "RGBA (32-bit with Alpha Channel)",
            "L": "Grayscale (8-bit)",
            "1": "1-bit Monochrome",
            "CMYK": "CMYK (Color Printing)",
            "YCbCr": "YCbCr Color",
            "LAB": "CIE LAB Color",
            "HSV": "HSV Color",
        }
        color_mode = mode_map.get(pil_img.mode, f"{pil_img.mode} ({len(pil_img.getbands()) * 8}-bit)")

        # Inspect ICC Profile
        icc_profile_present = False
        icc_profile_name = "None (Uncalibrated / sRGB assumed)"
        raw_icc = pil_img.info.get("icc_profile")
        if raw_icc:
            icc_profile_present = True
            try:
                profile = ImageCms.getOpenProfile(io.BytesIO(raw_icc))
                desc = ImageCms.getProfileDescription(profile)
                if desc:
                    icc_profile_name = desc.strip()
                else:
                    icc_profile_name = "Embedded ICC Color Profile"
            except Exception:
                icc_profile_name = "Embedded Custom ICC Profile"
    else:
        file_format = file_path.suffix.lstrip(".").upper() or "BINARY"
        width, height = 0, 0
        mp = 0.0
        aspect_ratio_str = "N/A"
        color_mode = "Audio / Video / Non-Raster Stream"
        icc_profile_present = False
        icc_profile_name = "N/A"

    # 2. Extract Comprehensive EXIF Data
    raw_exif: dict[str, Any] = {}
    camera_make = None
    camera_model = None
    lens_make = None
    lens_model = None
    software = None
    exif_timestamp = None
    original_timestamp = None
    digitized_timestamp = None
    focal_length = None
    focal_length_35mm = None
    exposure_time = None
    f_number = None
    iso_val = None
    flash = None
    white_balance = None
    metering_mode = None
    exposure_program = None
    orientation = None
    color_space = "sRGB" if icc_profile_present else "Uncalibrated / Unknown"

    gps_present = False
    gps_latitude = None
    gps_longitude = None
    gps_altitude = None

    if pil_img is not None:
        try:
            exif = pil_img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
                    val_str = str(value).strip()
                    raw_exif[tag_name] = val_str
                    
                    if tag_name == "Make":
                        camera_make = val_str
                    elif tag_name == "Model":
                        camera_model = val_str
                    elif tag_name == "Software":
                        software = val_str
                    elif tag_name == "DateTime":
                        exif_timestamp = val_str
                    elif tag_name == "Orientation":
                        orientation_map = {
                            1: "Horizontal (normal)",
                            2: "Mirror horizontal",
                            3: "Rotate 180°",
                            4: "Mirror vertical",
                            5: "Mirror horizontal and rotate 270° CW",
                            6: "Rotate 90° CW",
                            7: "Mirror horizontal and rotate 90° CW",
                            8: "Rotate 270° CW",
                        }
                        orientation = orientation_map.get(value, val_str)

                # SubIFD: Exif specific tags (Exposure, ISO, Lens, Timestamps)
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    for tag_id, value in exif_ifd.items():
                        tag_name = ExifTags.TAGS.get(tag_id, f"Exif_{tag_id}")
                        val_str = str(value).strip()
                        raw_exif[tag_name] = val_str

                        if tag_name == "DateTimeOriginal":
                            original_timestamp = val_str
                        elif tag_name == "DateTimeDigitized":
                            digitized_timestamp = val_str
                        elif tag_name == "ExposureTime":
                            exposure_time = _format_exposure_time(value)
                        elif tag_name == "FNumber":
                            f_number = _format_f_number(value)
                        elif tag_name in ("ISOSpeedRatings", "PhotographicSensitivity"):
                            iso_val = f"ISO {value}"
                        elif tag_name == "FocalLength":
                            focal_length = _format_focal_length(value)
                        elif tag_name == "FocalLengthIn35mmFilm":
                            focal_length_35mm = f"{value} mm (35mm equiv)"
                        elif tag_name == "LensModel":
                            lens_model = val_str
                        elif tag_name == "LensMake":
                            lens_make = val_str
                        elif tag_name == "Flash":
                            flash = "Flash fired" if (int(value) & 1) else "Flash did not fire"
                        elif tag_name == "WhiteBalance":
                            white_balance = "Manual" if value == 1 else "Auto"
                        elif tag_name == "MeteringMode":
                            metering_map = {
                                1: "Average", 2: "Center-weighted average", 3: "Spot",
                                4: "Multi-spot", 5: "Pattern / Multi-segment", 6: "Partial"
                            }
                            metering_mode = metering_map.get(value, f"Mode {value}")
                        elif tag_name == "ExposureProgram":
                            exp_map = {
                                1: "Manual", 2: "Normal program", 3: "Aperture priority",
                                4: "Shutter priority", 5: "Creative program", 6: "Action program",
                                7: "Portrait mode", 8: "Landscape mode"
                            }
                            exposure_program = exp_map.get(value, f"Program {value}")
                        elif tag_name == "ColorSpace":
                            color_space = "sRGB" if value == 1 else ("Adobe RGB" if value == 2 else "Uncalibrated")
                except Exception:
                    pass

                # SubIFD: GPS Info
                try:
                    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                    if gps_ifd:
                        gps_present = True
                        lat = gps_ifd.get(2)
                        lat_ref = gps_ifd.get(1, "N")
                        lon = gps_ifd.get(4)
                        lon_ref = gps_ifd.get(3, "W")
                        alt = gps_ifd.get(6)
                        if lat and lat_ref:
                            gps_latitude = _convert_gps_coords(lat, lat_ref)
                        if lon and lon_ref:
                            gps_longitude = _convert_gps_coords(lon, lon_ref)
                        if alt:
                            try:
                                gps_altitude = f"{float(alt):.1f} m"
                            except Exception:
                                gps_altitude = str(alt)
                        raw_exif["GPS_Present"] = "True"
                except Exception:
                    pass
        except Exception:
            pass

        # 3. Check PNG / WebP Text Chunks for AI generation metadata
        ai_generation_parameters = None
        ai_generator_name = None
        for k in ("parameters", "prompt", "workflow", "Comment", "Description", "Software"):
            chunk_val = pil_img.info.get(k)
            if chunk_val and isinstance(chunk_val, str):
                raw_exif[f"Chunk_{k}"] = chunk_val[:300]
                val_lower = chunk_val.lower()
                for kw in AI_GENERATOR_KEYWORDS:
                    if kw in val_lower:
                        ai_generator_name = kw.title()
                        break
                if "steps:" in val_lower or "sampler:" in val_lower or "cfg scale:" in val_lower or "seed:" in val_lower:
                    ai_generation_parameters = chunk_val.strip()
                    if not ai_generator_name:
                        ai_generator_name = "Stable Diffusion / Automatic1111"

        if not software and pil_img.info.get("Software"):
            software = str(pil_img.info.get("Software")).strip()
    else:
        ai_generation_parameters = None
        ai_generator_name = None

    # 4. Anomaly and Footprint Evaluation
    anomalies: list[str] = []
    editing_detected = False
    ai_generation_metadata_detected = bool(ai_generator_name or ai_generation_parameters)

    detected_editors = []
    if software:
        sw_lower = software.lower()
        for kw in AI_GENERATOR_KEYWORDS:
            if kw in sw_lower:
                ai_generation_metadata_detected = True
                ai_generator_name = kw.title()
                anomalies.append(f"AI generator footprint recorded in software metadata: '{software}'")
                break
        for tool in SUSPICIOUS_SOFTWARE:
            if tool in sw_lower:
                editing_detected = True
                detected_editors.append(tool.title())
                anomalies.append(f"Post-processing editing software footprint identified: '{software}'")
                break

    exif_present = bool(camera_make or camera_model or exif_timestamp or original_timestamp or exposure_time)

    if not exif_present and pil_img is not None:
        anomalies.append("All camera hardware EXIF tags are completely absent (characteristic of AI generation, screenshotting, or web sanitization).")
    elif exif_present:
        if not original_timestamp and not exif_timestamp:
            anomalies.append("Camera hardware tags exist but capture timestamps were stripped or omitted.")

    # 5. Digital Timeline Reconstruction (Module 12)
    file_ctime = datetime.datetime.fromtimestamp(stat.st_ctime, tz=datetime.timezone.utc) if stat else datetime.datetime.now(datetime.timezone.utc)
    file_mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc) if stat else datetime.datetime.now(datetime.timezone.utc)

    timeline_events: list[dict[str, Any]] = []

    primary_capture_ts = original_timestamp or exif_timestamp
    if primary_capture_ts:
        timeline_events.append({
            "stage": "Original Camera Shutter Capture",
            "source": "EXIF DateTimeOriginal",
            "timestamp": primary_capture_ts,
            "status": "RECORDED"
        })
    else:
        timeline_events.append({
            "stage": "Original Camera Shutter Capture",
            "source": "EXIF DateTimeOriginal",
            "timestamp": "NOT EMBEDDED (Purged or Synthetic)",
            "status": "MISSING"
        })

    if digitized_timestamp and digitized_timestamp != primary_capture_ts:
        timeline_events.append({
            "stage": "Sensor Digital Encoding",
            "source": "EXIF DateTimeDigitized",
            "timestamp": digitized_timestamp,
            "status": "RECORDED"
        })

    if exif_timestamp and exif_timestamp != primary_capture_ts:
        timeline_events.append({
            "stage": "Camera / Editor Save Timestamp",
            "source": "EXIF DateTime",
            "timestamp": exif_timestamp,
            "status": "MODIFIED"
        })

    timeline_events.append({
        "stage": "Filesystem Archive Creation",
        "source": "File ctime",
        "timestamp": file_ctime.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": "VERIFIED"
    })
    timeline_events.append({
        "stage": "Filesystem Last Modification",
        "source": "File mtime",
        "timestamp": file_mtime.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": "VERIFIED"
    })

    # Timeline consistency evaluation
    timeline_consistency = "CONSISTENT"
    timeline_notes = "Timeline timestamps are chronologically consistent."

    if not exif_present:
        timeline_consistency = "PURGED_METADATA"
        timeline_notes = "No original capture timestamp is embedded; only system ingestion timestamps exist."
    elif primary_capture_ts:
        try:
            parsed_exif_dt = datetime.datetime.strptime(primary_capture_ts[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            if parsed_exif_dt > file_ctime + datetime.timedelta(days=1):
                timeline_consistency = "ANOMALOUS_FUTURE_TIMESTAMP"
                timeline_notes = "EXIF capture timestamp post-dates file creation date (future timestamp anomaly)."
                anomalies.append("EXIF capture timestamp indicates future date relative to system clock.")
            elif (file_mtime - parsed_exif_dt).total_seconds() > 3600 * 24 * 180 and editing_detected:
                timeline_consistency = "MODIFIED_BY_EDITOR"
                timeline_notes = f"Capture date ({primary_capture_ts[:10]}) precedes modification date by substantial margin with editing software footprint."
        except Exception:
            pass

    if editing_detected and timeline_consistency == "CONSISTENT":
        timeline_consistency = "MODIFIED_BY_EDITOR"
        timeline_notes = f"Edited with {', '.join(detected_editors) if detected_editors else software}."

    # Determine overall metadata security status
    if ai_generation_metadata_detected:
        metadata_status = "AI_GENERATION_SIGNATURE"
    elif not exif_present:
        metadata_status = "PURGED_OR_SYNTHETIC"
    elif editing_detected:
        metadata_status = "POST_PROCESSED_EDITED"
    else:
        metadata_status = "AUTHENTIC_ORIGINAL_EXIF"

    return {
        # File & Container Details
        "file_name": file_path.name,
        "file_format": file_format,
        "file_size_formatted": _format_bytes(file_size_bytes),
        "dimensions": f"{width} × {height} px" if width > 0 else "N/A",
        "width": width,
        "height": height,
        "megapixels": f"{mp} MP" if mp > 0 else "N/A",
        "aspect_ratio": aspect_ratio_str,
        "color_mode": color_mode,
        "icc_profile_present": icc_profile_present,
        "icc_profile_name": icc_profile_name,
        "color_space": color_space,
        
        # Camera & Optics
        "exif_present": exif_present,
        "camera_make": camera_make or "Unknown / Unspecified",
        "camera_model": camera_model or "Unknown / Unspecified",
        "lens_make": lens_make or "Standard / Integrated",
        "lens_model": lens_model or "Not specified",
        "exposure_time": exposure_time or "N/A",
        "f_number": f_number or "N/A",
        "iso": iso_val or "N/A",
        "focal_length": focal_length or "N/A",
        "focal_length_35mm": focal_length_35mm or "N/A",
        "flash": flash or "Not recorded",
        "white_balance": white_balance or "Not recorded",
        "metering_mode": metering_mode or "Not recorded",
        "exposure_program": exposure_program or "Not recorded",
        "orientation": orientation or "Normal (0°)",

        # Geolocation
        "gps_present": gps_present,
        "gps_latitude": gps_latitude or "No GPS geotags embedded",
        "gps_longitude": gps_longitude or "No GPS geotags embedded",
        "gps_altitude": gps_altitude or "N/A",

        # Software & Footprints
        "software": software or "None recorded",
        "editing_software_detected": editing_detected,
        "ai_metadata_detected": ai_generation_metadata_detected,
        "ai_generator_name": ai_generator_name or "None",
        "ai_generation_parameters": ai_generation_parameters,

        # Digital Timeline
        "timeline_events": timeline_events,
        "timeline_consistency": timeline_consistency,
        "timeline_notes": timeline_notes,
        "metadata_status": metadata_status,
        "anomalies": anomalies,

        # Backward compatibility field
        "exif_summary": {k: str(raw_exif[k])[:100] for k in list(raw_exif.keys())[:10]},

        # Full Raw Tags Map for Deep Forensic Inspection
        "all_tags": raw_exif,
    }
