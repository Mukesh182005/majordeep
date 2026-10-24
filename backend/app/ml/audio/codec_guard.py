"""Which lossy codec a file's audio uses, and whether the audio verdict must abstain on it.

The served LCNN was measured on ASVspoof 2019 LA dev speech re-encoded with
MP3, AAC and Opus (``ml/evaluation/audio_codec_dev.py``). A codec family on
which it flagged more than 5 % of bona fide utterances is listed in
``AUDIO_CODEC_GUARD``: audio in that codec gets an INCONCLUSIVE verdict, and
a video's audio track in it is left out of the video score.

The codec is read from the file's first audio stream with ffmpeg, never from
the file name. If it cannot be read, no guard applies.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ffmpeg stream codec names -> the families measured on dev
_FAMILIES = {"mp3": "mp3", "mp3float": "mp3", "aac": "aac", "aac_latm": "aac", "opus": "opus"}
_STREAM = re.compile(r"Stream #\S+.*?: Audio: ([A-Za-z0-9_]+)")


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # the Docker image has a system ffmpeg
        return "ffmpeg"


def audio_codec(path: str | Path) -> str | None:
    """The ffmpeg codec name of the first audio stream, lower case, or None."""
    try:
        probe = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-i", str(path)],
                               capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("Could not read the audio codec of %s: %s", path, exc)
        return None
    match = _STREAM.search(probe.stderr)
    return match.group(1).lower() if match else None


def codec_family(codec: str | None) -> str | None:
    return _FAMILIES.get(codec or "")


def guarded_family(path: str | Path) -> str | None:
    """The codec family of ``path`` if AUDIO_CODEC_GUARD lists it, else None."""
    from app.config import settings

    if not settings.audio_codec_guard:
        return None
    family = codec_family(audio_codec(path))
    return family if family in settings.audio_codec_guard else None


def guard_note(family: str) -> str:
    return (f"Audio encoded with {family.upper()}: on development speech re-encoded this way the audio model "
            "flagged more than 5% of genuine recordings, so no audio verdict is given for this file.")
