"""P5: security and privacy for public users.

1. A faked X-Forwarded-For / X-Real-IP cannot dodge the guest upload limit;
   X-Real-IP counts only from a trusted proxy.
3. Guest jobs older than RETENTION_HOURS are purged with every file.
4. "Delete scan" removes every file the job produced.
5. Signed, short-lived links replace ?token= for report download and WebSocket.
6. Login sets an httpOnly SameSite=Lax cookie; Bearer still works.
7. Audio and video longer than MAX_AUDIO_SECONDS / MAX_VIDEO_SECONDS are refused.
8. ENABLED_MEDIA_TYPES is enforced at upload.
"""

from __future__ import annotations

import io
import uuid
import wave
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest


def _peer(address: str):
    """A client whose requests arrive from ``address`` (its own rate-limit bucket)."""
    from app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app, client=(address, 50000))


def _wav(seconds: float, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    samples = (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(seconds * rate)) / rate) * 32767).astype("<i2")
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def _register(client) -> tuple[dict, str]:
    email = f"p5-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-battery"})
    assert response.status_code == 201, response.text
    client.cookies.clear()
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


# --------------------------------------------------------------------------- 1. client IP
class TestClientIp:
    def test_faked_forwarding_headers_do_not_dodge_the_guest_limit(self, client, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "guest_rate_limit_per_hour", 2)
        peer = _peer("198.51.100.23")
        statuses = []
        for i in range(4):
            fake = f"10.0.0.{i + 1}"
            statuses.append(
                peer.post(
                    "/api/upload",
                    files={"file": ("bad.exe", io.BytesIO(b"MZ\x00\x00"), "application/exe")},
                    headers={"X-Forwarded-For": fake, "X-Real-IP": fake},
                ).status_code
            )
        assert statuses == [400, 400, 429, 429], statuses

    @staticmethod
    def _request(peer: str, headers: dict[str, str]):
        from starlette.requests import Request

        return Request({
            "type": "http",
            "client": (peer, 1234),
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        })

    def test_x_real_ip_counts_only_from_a_trusted_proxy(self, monkeypatch):
        from app.config import settings
        from app.deps import client_ip

        monkeypatch.setattr(settings, "trusted_proxies", ["172.28.0.10"])
        headers = {"X-Real-IP": "203.0.113.9", "X-Forwarded-For": "192.0.2.1"}
        assert client_ip(self._request("172.28.0.10", headers)) == "203.0.113.9"
        assert client_ip(self._request("172.28.0.11", headers)) == "172.28.0.11"
        assert client_ip(self._request("172.28.0.10", {"X-Real-IP": "not-an-ip"})) == "172.28.0.10"

    def test_cidr_entries_and_default_trust_nobody(self, monkeypatch):
        from app.config import settings
        from app.deps import client_ip

        headers = {"X-Real-IP": "203.0.113.9"}
        monkeypatch.setattr(settings, "trusted_proxies", [])
        assert client_ip(self._request("127.0.0.1", headers)) == "127.0.0.1"
        monkeypatch.setattr(settings, "trusted_proxies", ["10.1.0.0/16"])
        assert client_ip(self._request("10.1.200.3", headers)) == "203.0.113.9"


# --------------------------------------------------------------------------- 3 and 4. files
def _make_job_with_files(db, *, user_id: str | None, age_hours: float) -> tuple[object, list[Path]]:
    """A finished job with an upload, evidence images, a report and a report chart on disk."""
    from app.config import settings
    from app.models import Job, JobStatus, MediaType, Report

    job_id = uuid.uuid4().hex
    case = f"DF-TEST-{job_id[:6].upper()}"
    storage, evidence, reports = Path(settings.storage_dir), Path(settings.evidence_dir), Path(settings.report_dir)
    for folder in (storage, evidence, reports, evidence / "report_charts"):
        folder.mkdir(parents=True, exist_ok=True)

    files = [
        storage / f"{job_id}.png",
        evidence / f"{job_id}_heatmap.png",
        evidence / f"{job_id}_ela.png",               # named with the job id, not in evidence keys
        evidence / f"plate-{job_id[:8]}.png",         # only reachable through a nested *_file key
        reports / f"DFR-{case}.pdf",
        evidence / "report_charts" / f"DFR-{case}_gauge.png",
    ]
    for path in files:
        path.write_bytes(b"x")
    when = datetime.now(UTC) - timedelta(hours=age_hours)
    job = Job(
        id=job_id, case_reference=case, user_id=user_id, original_filename="x.png",
        stored_path=str(files[0]), media_type=MediaType.IMAGE, content_type="image/png",
        file_size_bytes=1, sha256="0" * 64, status=JobStatus.DONE, uploaded_at=when,
        evidence={"heatmap_file": files[1].name, "forensics": {"visual_evidence": {"multi_file": files[3].name}}},
    )
    job.reports.append(Report(report_reference=f"DFR-{case}", file_path=str(files[4]), sha256="0" * 64))
    db.add(job)
    db.commit()
    return job, files


class TestRetention:
    def test_purges_old_guest_jobs_with_every_file(self, client, monkeypatch):
        from app.config import settings
        from app.database import SessionLocal
        from app.models import Job, Report, UploadEvent
        from app.retention import purge_expired_guest_jobs

        monkeypatch.setattr(settings, "retention_hours", 48)
        _, owner_id = _register(client)
        db = SessionLocal()
        try:
            old_guest, old_files = _make_job_with_files(db, user_id=None, age_hours=60)
            new_guest, new_files = _make_job_with_files(db, user_id=None, age_hours=2)
            old_owned, owned_files = _make_job_with_files(db, user_id=owner_id, age_hours=60)
            old_id, new_id, owned_id = old_guest.id, new_guest.id, old_owned.id
            db.add(UploadEvent(client_ip="192.0.2.50", created_at=datetime.now(UTC) - timedelta(hours=60)))
            db.commit()

            summary = purge_expired_guest_jobs(db)
            db.expire_all()

            assert summary["jobs"] >= 1 and summary["files"] >= len(old_files) and summary["upload_events"] >= 1
            assert all(not path.exists() for path in old_files), [p for p in old_files if p.exists()]
            assert db.get(Job, old_id) is None
            assert db.query(Report).filter(Report.job_id == old_id).count() == 0
            # Recent guest jobs and accounts' jobs are kept.
            assert db.get(Job, new_id) is not None and all(p.exists() for p in new_files)
            assert db.get(Job, owned_id) is not None and all(p.exists() for p in owned_files)
            assert db.query(UploadEvent).filter(UploadEvent.client_ip == "192.0.2.50").count() == 0
        finally:
            db.close()

    def test_beat_runs_the_purge_task(self):
        from app.worker import tasks  # noqa: F401  (registers the task)
        from app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule["purge-expired-guest-jobs"]
        assert schedule["task"] == "maintenance.purge_expired_guest_jobs"
        assert schedule["task"] in celery_app.tasks


class TestDeleteScan:
    def test_removes_every_file_the_job_produced(self, client):
        from app.config import settings
        from app.database import SessionLocal

        headers, user_id = _register(client)
        db = SessionLocal()
        try:
            job, files = _make_job_with_files(db, user_id=user_id, age_hours=0)
            job_id = job.id
        finally:
            db.close()
        outside = Path(settings.storage_dir).parent / f"outside-{job_id}.txt"
        outside.write_bytes(b"keep me")

        assert client.delete(f"/api/history/{job_id}", headers=headers).status_code == 204
        assert [p for p in files if p.exists()] == []
        assert not list(Path(settings.evidence_dir).rglob(f"*{job_id}*"))
        assert outside.exists(), "files outside the storage folders are never touched"

    def test_a_crafted_evidence_name_cannot_escape_the_evidence_folder(self, tmp_path):
        from app.config import settings
        from app.models import Job
        from app.retention import job_files

        victim = Path(settings.storage_dir).parent / "victim.txt"
        victim.write_bytes(b"keep me")
        job = Job(id=uuid.uuid4().hex, case_reference="DF-X", evidence={"heatmap_file": "../victim.txt"})
        assert victim not in job_files(job)


# --------------------------------------------------------------------------- 5. signed links
@pytest.fixture
def owned_done_job(client):
    from app.database import SessionLocal

    headers, user_id = _register(client)
    db = SessionLocal()
    try:
        job, _ = _make_job_with_files(db, user_id=user_id, age_hours=0)
        job.fake_probability, job.model_name, job.model_version, job.weights_status = 0.2, "m", "v", "trained"
        db.commit()
        return headers, job.id
    finally:
        db.close()


class TestSignedLinks:
    def test_signed_report_link_works_without_credentials(self, client, owned_done_job):
        headers, job_id = owned_done_job
        assert client.get(f"/api/jobs/{job_id}/report").status_code == 404  # anonymous
        links = client.post(f"/api/jobs/{job_id}/links", headers=headers).json()
        response = client.get(links["report_url"])
        assert response.status_code == 200 and response.content == b"x"  # the job's stored report file
        assert "token=" not in links["report_url"] and "token=" not in links["ws_url"]

    def test_tampered_expired_or_other_job_signatures_are_refused(self, client, owned_done_job):
        from app import signing

        headers, job_id = owned_done_job
        good = signing.sign(job_id, "report")
        tampered = {**good, "sig": ("0" if good["sig"][0] != "0" else "1") + good["sig"][1:]}
        expired = signing.sign(job_id, "report", now=0)
        wrong_purpose = signing.sign(job_id, "ws")
        for params in (tampered, expired, wrong_purpose):
            assert client.get(f"/api/jobs/{job_id}/report", params=params).status_code == 404, params
        assert not signing.verify(uuid.uuid4().hex, "report", good["exp"], good["sig"])
        assert not signing.verify(job_id, "report", int(good["exp"]) + 3600, good["sig"])

    def test_login_token_in_the_query_string_is_ignored(self, client, owned_done_job):
        headers, job_id = owned_done_job
        token = headers["Authorization"].split()[1]
        assert client.get(f"/api/jobs/{job_id}/report", params={"token": token}).status_code == 404
        assert client.get(f"/api/jobs/{job_id}/result", params={"token": token}).status_code == 404

    def test_websocket_accepts_a_signed_link_and_refuses_anonymous(self, client, owned_done_job):
        headers, job_id = owned_done_job
        with client.websocket_connect(f"/api/jobs/{job_id}/ws") as ws:
            assert ws.receive_json()["message"] == "Job not found."
        url = client.post(f"/api/jobs/{job_id}/links", headers=headers).json()["ws_url"]
        with client.websocket_connect(url) as ws:
            assert ws.receive_json()["status"] == "done"


# --------------------------------------------------------------------------- 6. cookie
class TestCookieLogin:
    def test_login_sets_an_httponly_lax_cookie_that_authenticates(self, client):
        from app.config import settings

        email = f"cookie-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/auth/register", json={"email": email, "password": "correct-horse-battery"})
        client.cookies.clear()
        response = client.post("/api/auth/login", json={"email": email, "password": "correct-horse-battery"})
        assert response.status_code == 200 and response.json()["access_token"]  # Bearer for API clients
        set_cookie = response.headers["set-cookie"].lower()
        assert settings.auth_cookie_name in set_cookie
        assert "httponly" in set_cookie and "samesite=lax" in set_cookie and "path=/api" in set_cookie

        assert client.get("/api/auth/me").json()["email"] == email  # cookie only, no header
        assert client.post("/api/auth/logout").status_code == 204
        client.cookies.clear()  # the test client keeps a deleted cookie's jar entry; a browser drops it
        assert client.get("/api/auth/me").status_code == 401

    def test_cookie_is_secure_in_production(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "auth_cookie_secure", None)
        assert settings.cookie_secure is True
        monkeypatch.setattr(settings, "environment", "development")
        assert settings.cookie_secure is False


# --------------------------------------------------------------------------- 7 and 8. uploads
class TestUploadLimits:
    def test_audio_longer_than_the_limit_is_refused(self, client, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "max_audio_seconds", 2.0)
        before = set(Path(settings.storage_dir).glob("*"))
        response = _peer("198.51.100.71").post("/api/upload", files={"file": ("long.wav", _wav(3.0), "audio/wav")})
        assert response.status_code == 400 and "at most 2 s of audio" in response.json()["detail"]
        assert set(Path(settings.storage_dir).glob("*")) == before, "a refused upload is not kept"

    def test_video_longer_than_the_limit_is_refused(self, client, monkeypatch, tmp_path):
        cv2 = pytest.importorskip("cv2")
        from app.config import settings

        path = tmp_path / "clip.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
        for i in range(30):  # 3 s at 10 fps
            writer.write(np.full((48, 64, 3), i * 8, dtype=np.uint8))
        writer.release()
        monkeypatch.setattr(settings, "max_video_seconds", 2.0)
        response = _peer("198.51.100.72").post("/api/upload", files={"file": ("clip.avi", path.read_bytes(), "video/x-msvideo")})
        assert response.status_code == 400 and "at most 2 s of video" in response.json()["detail"]

    def test_the_worker_refuses_an_over_long_file_too(self, monkeypatch, tmp_path):
        from app.config import settings
        from app.ml.pipeline import analyze
        from app.models import MediaType

        path = tmp_path / "long.wav"
        path.write_bytes(_wav(3.0))
        monkeypatch.setattr(settings, "max_audio_seconds", 2.0)
        with pytest.raises(ValueError, match="at most 2 s"):
            analyze(MediaType.AUDIO, path, tmp_path, "job")

    def test_disabled_media_types_are_refused_and_not_advertised(self, client, monkeypatch, png_bytes):
        from app.config import settings

        monkeypatch.setattr(settings, "enabled_media_types", ["image"])
        peer = _peer("198.51.100.73")
        response = peer.post("/api/upload", files={"file": ("a.wav", _wav(1.0), "audio/wav")})
        assert response.status_code == 403 and "not enabled" in response.json()["detail"]
        limits = client.get("/api/upload/limits").json()
        assert limits["enabled_media_types"] == ["image"] and set(limits["allowed_extensions"]) == {"image"}
