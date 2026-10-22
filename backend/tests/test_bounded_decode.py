"""Length limits hold even when a file's headers are missing or false (P5 follow-up).

Upload and worker check MAX_AUDIO_SECONDS / MAX_VIDEO_SECONDS against the
duration in the file's own headers (``app.storage.probe_duration_seconds``),
which the uploader writes. These tests switch that probe off and check that
decoding itself stops one second past the limit and refuses the job, while
code that passes no limit (training, evaluation) still decodes exactly as before.
"""

from __future__ import annotations

import io
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

from app.ml import preprocessing
from app.ml.preprocessing import MediaTooLongError, extract_audio_waveform, load_audio

RATE = 16000


def _wav_bytes(seconds: float, rate: int = RATE) -> bytes:
    buffer = io.BytesIO()
    samples = (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(seconds * rate)) / rate) * 32767).astype("<i2")
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def _wav(path: Path, seconds: float) -> Path:
    path.write_bytes(_wav_bytes(seconds))
    return path


@pytest.fixture
def librosa_calls(monkeypatch) -> list[dict]:
    """Keyword arguments of every librosa.load call (the real loader still runs)."""
    librosa = pytest.importorskip("librosa")
    calls: list[dict] = []
    real_load = librosa.load

    def recording_load(*args, **kwargs):
        calls.append(kwargs)
        return real_load(*args, **kwargs)

    monkeypatch.setattr(librosa, "load", recording_load)
    return calls


@pytest.fixture
def no_header_probe(monkeypatch):
    """Upload and worker checks see no duration, as for a file without (or with false) headers."""
    from app import storage

    monkeypatch.setattr(storage, "probe_duration_seconds", lambda *args, **kwargs: None)


# --------------------------------------------------------------------------- load_audio
class TestLoadAudio:
    def test_without_a_limit_nothing_changes(self, tmp_path, librosa_calls):
        import librosa

        path = _wav(tmp_path / "a.wav", 5.0)
        waveform, rate = load_audio(path, RATE)
        assert "duration" not in librosa_calls[0], "training and evaluation paths must stay uncapped"
        reference, _ = librosa.load(str(path), sr=RATE, mono=True)
        assert rate == RATE and np.array_equal(waveform, reference.astype(np.float32))

    def test_a_file_within_the_limit_decodes_bit_identically(self, tmp_path):
        path = _wav(tmp_path / "a.wav", 1.5)
        capped, _ = load_audio(path, RATE, max_seconds=2.0)
        full, _ = load_audio(path, RATE)
        assert len(capped) == int(1.5 * RATE) and np.array_equal(capped, full)

    def test_a_longer_file_is_refused_after_one_second_past_the_limit(self, tmp_path, librosa_calls):
        path = _wav(tmp_path / "a.wav", 5.0)
        with pytest.raises(MediaTooLongError, match="at most 2 s of audio"):
            load_audio(path, RATE, max_seconds=2.0)
        assert librosa_calls[-1]["duration"] == pytest.approx(3.0)

    @pytest.mark.parametrize("missing", [("librosa",), ("librosa", "soundfile")], ids=["soundfile", "wave"])
    def test_the_fallback_decoders_are_capped_too(self, tmp_path, monkeypatch, missing):
        for name in missing:
            monkeypatch.setitem(sys.modules, name, None)  # "import name" now raises ImportError
        with pytest.raises(MediaTooLongError):
            load_audio(_wav(tmp_path / "long.wav", 5.0), RATE, max_seconds=2.0)
        waveform, rate = load_audio(_wav(tmp_path / "short.wav", 1.5), RATE, max_seconds=2.0)
        assert rate == RATE and len(waveform) == int(1.5 * RATE)


# --------------------------------------------------------------------------- video audio track
class TestVideoAudioTrack:
    @staticmethod
    def _ffmpeg_demuxes(monkeypatch, seconds: float) -> list[tuple[list, dict]]:
        """load_audio cannot read the container; ffmpeg 'demuxes' ``seconds`` of audio."""
        imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")
        imageio_ffmpeg.get_ffmpeg_exe()  # resolve (and cache) the binary before run() is replaced
        calls: list[tuple[list, dict]] = []
        real_run = subprocess.run

        def cannot_read(*args, **kwargs):
            raise RuntimeError("not a plain audio file")

        def fake_run(cmd, *args, **kwargs):
            if not (isinstance(cmd, list) and str(cmd[-1]).endswith(".wav")):
                return real_run(cmd, *args, **kwargs)
            calls.append((cmd, kwargs))
            Path(cmd[-1]).write_bytes(_wav_bytes(seconds))
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        monkeypatch.setattr(preprocessing, "load_audio", cannot_read)
        monkeypatch.setattr(subprocess, "run", fake_run)
        return calls

    def test_ffmpeg_stops_one_second_past_the_limit_and_has_a_timeout(self, tmp_path, monkeypatch):
        calls = self._ffmpeg_demuxes(monkeypatch, seconds=1.5)
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"\x00" * 64)
        waveform, rate = extract_audio_waveform(video, max_seconds=2.0)
        cmd, options = calls[-1]
        assert cmd[cmd.index("-t") + 1] == "3" and options.get("timeout")
        assert rate == RATE and len(waveform) == int(1.5 * RATE)

    def test_a_longer_track_refuses_the_video(self, tmp_path, monkeypatch):
        self._ffmpeg_demuxes(monkeypatch, seconds=3.0)  # what ffmpeg returns when cut at limit + 1 s
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"\x00" * 64)
        with pytest.raises(MediaTooLongError, match="at most 2 s of video"):
            extract_audio_waveform(video, max_seconds=2.0)

    def test_without_a_limit_the_ffmpeg_call_is_unchanged(self, tmp_path, monkeypatch):
        calls = self._ffmpeg_demuxes(monkeypatch, seconds=1.0)
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"\x00" * 64)
        extract_audio_waveform(video)
        cmd, options = calls[-1]
        assert "-t" not in cmd and "timeout" not in options

    def test_a_long_file_read_directly_is_refused_as_video(self, tmp_path):
        with pytest.raises(MediaTooLongError, match="at most 2 s of video"):
            extract_audio_waveform(_wav(tmp_path / "long.wav", 5.0), max_seconds=2.0)

    def test_the_lip_sync_stage_does_not_swallow_the_refusal(self, tmp_path, monkeypatch):
        from app.ml.video.audio_crossmodal import analyze_crossmodal_lipsync

        def too_long(*args, **kwargs):
            raise MediaTooLongError("The video's audio track is longer than 2 s; this server analyses at most 2 s of video.")

        monkeypatch.setattr(preprocessing, "extract_audio_waveform", too_long)
        with pytest.raises(MediaTooLongError):
            analyze_crossmodal_lipsync(tmp_path / "clip.mp4", [], [])


# --------------------------------------------------------------------------- end to end
class TestRefusedWithoutHeaders:
    def test_the_worker_refuses_long_audio_the_probe_could_not_measure(self, tmp_path, monkeypatch, no_header_probe):
        from app.config import settings
        from app.ml.pipeline import analyze
        from app.models import MediaType

        monkeypatch.setattr(settings, "max_audio_seconds", 2.0)
        with pytest.raises(ValueError, match="at most 2 s of audio"):
            analyze(MediaType.AUDIO, _wav(tmp_path / "long.wav", 3.0), tmp_path / "evidence", "job")

    def test_the_upload_is_accepted_and_the_job_fails_with_a_message(self, client, monkeypatch, no_header_probe):
        from fastapi.testclient import TestClient

        from app.config import settings
        from app.main import app

        monkeypatch.setattr(settings, "max_audio_seconds", 2.0)
        peer = TestClient(app, client=("198.51.100.91", 50000))  # its own guest rate-limit bucket
        response = peer.post("/api/upload", files={"file": ("long.wav", _wav_bytes(3.0), "audio/wav")})
        assert response.status_code == 202, response.text
        status = peer.get(f"/api/jobs/{response.json()['id']}/status").json()
        assert status["status"] == "failed"
        assert "at most 2 s of audio" in (status["error_message"] or "")
