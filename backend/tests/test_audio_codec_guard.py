"""AUDIO_CODEC_GUARD: the codec is read from the file, and guarded audio gets no audio verdict."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from app.config import Settings, settings
from app.ml.audio import codec_guard
from app.models import Verdict

imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")


def _tone(path: Path, seconds: float = 2.0) -> Path:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * i / 16000)))
                                    for i in range(int(seconds * 16000))))
    return path


def _encode(source: Path, target: Path, *args: str) -> Path:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(source), *args, str(target)],
                   check=True, capture_output=True)
    return target


def test_codec_is_read_from_the_stream_not_the_name(tmp_path):
    wav = _tone(tmp_path / "a.wav")
    mp3 = _encode(wav, tmp_path / "a.mp3", "-c:a", "libmp3lame", "-b:a", "64k")
    disguised = tmp_path / "looks_like.wav"
    shutil.copy(mp3, disguised)
    assert codec_guard.codec_family(codec_guard.audio_codec(mp3)) == "mp3"
    assert codec_guard.codec_family(codec_guard.audio_codec(disguised)) == "mp3"
    assert codec_guard.codec_family(codec_guard.audio_codec(wav)) is None  # PCM is not a guarded family
    assert codec_guard.audio_codec(tmp_path / "missing.mp3") is None


def test_guard_applies_only_to_listed_families(tmp_path, monkeypatch):
    mp3 = _encode(_tone(tmp_path / "a.wav"), tmp_path / "a.mp3", "-c:a", "libmp3lame", "-b:a", "64k")
    monkeypatch.setattr(settings, "audio_codec_guard", [])
    assert codec_guard.guarded_family(mp3) is None
    monkeypatch.setattr(settings, "audio_codec_guard", ["aac"])
    assert codec_guard.guarded_family(mp3) is None
    monkeypatch.setattr(settings, "audio_codec_guard", ["mp3"])
    assert codec_guard.guarded_family(mp3) == "mp3"


def test_setting_accepts_the_comma_form_and_rejects_unknown_families():
    assert Settings(audio_codec_guard="MP3, aac").audio_codec_guard == ["mp3", "aac"]
    with pytest.raises(ValueError, match="unknown codec families"):
        Settings(audio_codec_guard="mp3,flac")


def test_guarded_mp3_gets_an_inconclusive_audio_verdict(tmp_path, monkeypatch):
    from app.ml.audio_pipeline import analyze_audio

    wav = _tone(tmp_path / "speech.wav", seconds=3.0)
    mp3 = _encode(wav, tmp_path / "speech.mp3", "-c:a", "libmp3lame", "-b:a", "64k")
    monkeypatch.setattr(settings, "audio_codec_guard", ["mp3"])
    guarded = analyze_audio(mp3, tmp_path / "ev1", "guard-mp3")
    assert guarded.verdict is Verdict.INCONCLUSIVE
    assert guarded.evidence["codec_guard"] == {"codec_family": "mp3", "setting": "AUDIO_CODEC_GUARD"}
    assert guarded.evidence["notes"][0].startswith("Audio encoded with MP3")

    plain = analyze_audio(wav, tmp_path / "ev2", "guard-wav")
    assert plain.evidence["codec_guard"] is None
    assert not any(n.startswith("Audio encoded with") for n in plain.evidence["notes"])


def _video_with_aac(tmp_path: Path) -> Path:
    import cv2
    import numpy as np

    silent = tmp_path / "frames.avi"
    out = cv2.VideoWriter(str(silent), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (128, 128))
    for _ in range(20):
        frame = np.full((128, 128, 3), 128, dtype=np.uint8)
        cv2.circle(frame, (64, 64), 32, (220, 180, 150), -1)
        out.write(frame)
    out.release()
    tone = _tone(tmp_path / "track.wav", seconds=2.0)
    target = tmp_path / "clip.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(silent), "-i", str(tone),
                    "-c:v", "mpeg4", "-c:a", "aac", "-b:a", "64k", "-shortest", str(target)],
                   check=True, capture_output=True)
    return target


@pytest.mark.parametrize("guard", [["aac"], []])
def test_guarded_audio_track_is_left_out_of_the_video_score(tmp_path, monkeypatch, guard):
    import app.ml.video as video

    clip = _video_with_aac(tmp_path)
    seen = {}
    original = video.fuse_video_forensics

    def spy(*args, **kwargs):
        seen["audio_forensics"] = kwargs.get("audio_forensics")
        return original(*args, **kwargs)

    monkeypatch.setattr(video, "fuse_video_forensics", spy)
    monkeypatch.setattr(settings, "audio_codec_guard", guard)
    result = video.analyze_video(clip, tmp_path / "ev", f"guard-video-{bool(guard)}")
    assert result.evidence["audio_forensics"] is not None  # the track was still analysed and is shown
    if guard:
        assert seen["audio_forensics"] is None
        assert result.evidence["audio_codec_guard"]["codec_family"] == "aac"
        assert any("left out of the video score" in n for n in result.evidence["notes"])
    else:
        assert seen["audio_forensics"] is not None
        assert result.evidence["audio_codec_guard"] is None


def test_resample_family_covers_audio_not_at_16k(tmp_path, monkeypatch):
    wav16 = _tone(tmp_path / "a16.wav")
    wav48 = _encode(wav16, tmp_path / "a48.wav", "-ar", "48000")
    assert codec_guard.audio_stream(wav48) == ("pcm_s16le", 48000)
    monkeypatch.setattr(settings, "audio_codec_guard", ["resample"])
    assert codec_guard.guarded_family(wav48) == "resample"
    assert codec_guard.guarded_family(wav16) is None
    assert "sample rate other than 16 kHz" in codec_guard.guard_note("resample")
    assert Settings(audio_codec_guard="mp3,resample").audio_codec_guard == ["mp3", "resample"]
