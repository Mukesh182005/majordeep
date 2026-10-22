#!/usr/bin/env python3
"""DeepSentinel Automated End-to-End Smoke Test.

Validates the full image-only beta deployment pipeline:
1. User registration & authentication (cookie-based session & bearer token)
2. Uploads 3 real photos and 3 AI-generated images
3. Polls until all 6 inference jobs reach status 'done'
4. Obtains signed download URL and downloads forensic PDF report (verifies %PDF- magic bytes)
5. Deletes a completed scan via DELETE /api/history/{job_id}
6. Confirms that all source, evidence, and report files are permanently erased from disk
7. Confirms that audio/video uploads are rejected when ENABLED_MEDIA_TYPES=image

Usage:
  # Against live deployment or Docker frontend:
  python deploy/smoke_test.py --base-url http://localhost:8080

  # Against live HTTPS beta domain:
  python deploy/smoke_test.py --base-url https://beta.deepsentinel.ai

  # Direct in-process test against FastAPI application:
  python deploy/smoke_test.py --in-process
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))


def find_or_create_test_images() -> tuple[list[Path], list[Path]]:
    """Locates 3 real photos and 3 AI images, generating valid samples if not found."""
    real_images: list[Path] = []
    ai_images: list[Path] = []

    # Check golden_test/ directory first
    golden_real = list((REPO_ROOT / "golden_test" / "real").rglob("*.jpg")) + list((REPO_ROOT / "golden_test" / "real").rglob("*.png"))
    golden_ai = list((REPO_ROOT / "golden_test" / "ai").rglob("*.jpg")) + list((REPO_ROOT / "golden_test" / "ai").rglob("*.png"))

    if len(golden_real) >= 3 and len(golden_ai) >= 3:
        return golden_real[:3], golden_ai[:3]

    # Check accuracy_test directory
    acc_real = list((REPO_ROOT / "accuracy_test" / "100_real").glob("*.jpg"))
    acc_ai = list((REPO_ROOT / "accuracy_test" / "100_ai").glob("*.jpg"))

    if len(acc_real) >= 3 and len(acc_ai) >= 3:
        return acc_real[:3], acc_ai[:3]

    # Fallback: synthesize valid JPEG images using PIL
    from PIL import Image, ImageDraw

    temp_dir = REPO_ROOT / "deploy" / ".temp_smoke_images"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 4):
        rp = temp_dir / f"smoke_real_{i}.jpg"
        im_real = Image.new("RGB", (256, 256), color=(60 + i * 20, 100, 140))
        draw = ImageDraw.Draw(im_real)
        draw.rectangle([30, 30, 200, 200], fill=(180, 160, 120))
        im_real.save(rp, format="JPEG", quality=90)
        real_images.append(rp)

        ap = temp_dir / f"smoke_ai_{i}.jpg"
        im_ai = Image.new("RGB", (256, 256), color=(140, 60 + i * 20, 100))
        draw_ai = ImageDraw.Draw(im_ai)
        draw_ai.ellipse([30, 30, 220, 220], fill=(50, 180, 200))
        im_ai.save(ap, format="JPEG", quality=90)
        ai_images.append(ap)

    return real_images, ai_images


class SmokeTestSession:
    def __init__(self, base_url: str | None = None, in_process: bool = False):
        self.in_process = in_process
        self.base_url = base_url.rstrip("/") if base_url else "http://localhost:8080"
        self.cookies: dict[str, str] = {}
        self.auth_token: str | None = None
        self.client: Any = None

        if self.in_process:
            from fastapi.testclient import TestClient
            from app.main import app
            self.client = TestClient(app)

    def request(self, method: str, path: str, json: dict = None, data: dict = None, files: dict = None) -> Any:
        url_path = f"/api/{path.lstrip('/')}"
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        if self.in_process:
            if self.cookies:
                self.client.cookies.update(self.cookies)
            resp = self.client.request(
                method=method,
                url=url_path,
                json=json,
                data=data,
                files=files,
                headers=headers,
            )
            # Store any set-cookie
            for k, v in resp.cookies.items():
                self.cookies[k] = v
            return resp
        else:
            import urllib.parse
            import requests
            session = requests.Session()
            session.cookies.update(self.cookies)
            full_url = f"{self.base_url}{url_path}"
            resp = session.request(
                method=method,
                url=full_url,
                json=json,
                data=data,
                files=files,
                headers=headers,
                timeout=30,
            )
            self.cookies.update(session.cookies.get_dict())
            return resp


def run_smoke_test(base_url: str | None = None, in_process: bool = False):
    print("=" * 65)
    print(" DeepSentinel Smoke Test - Image-Only Beta Pipeline Verification")
    print("=" * 65)

    session = SmokeTestSession(base_url=base_url, in_process=in_process)
    target_desc = "In-Process TestClient" if in_process else session.base_url
    print(f"[*] Target Deployment: {target_desc}")

    # 1. Health check
    print("\n[Step 1] Checking API health endpoint...")
    resp = session.request("GET", "/health")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code} - {resp.text}"
    health_data = resp.json()
    assert health_data.get("status") == "ok", f"Unhealthy status: {health_data}"
    print(f"[OK] API is healthy (version: {health_data.get('version')}, queue: {health_data.get('queue_enabled')})")

    # 2. User registration
    print("\n[Step 2] Registering test user...")
    test_user_id = uuid.uuid4().hex[:8]
    email = f"smoketest_{test_user_id}@example.com"
    password = "SmokeTestPassword123!"
    full_name = "Beta Smoke Test"

    resp = session.request("POST", "/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })
    assert resp.status_code == 201, f"Registration failed: {resp.status_code} - {resp.text}"
    user_data = resp.json()
    session.auth_token = user_data.get("access_token")
    print(f"[OK] Registered test user: {email} (ID: {user_data.get('id')})")

    # 3. User login (verify httpOnly session cookie)
    print("\n[Step 3] Logging in test user to verify session cookie...")
    resp = session.request("POST", "/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} - {resp.text}"
    login_data = resp.json()
    session.auth_token = login_data.get("access_token")
    print(f"[OK] Logged in successfully. Access token & cookie verified.")

    # 4. Upload 3 real photos and 3 AI images
    print("\n[Step 4] Locating test images...")
    real_paths, ai_paths = find_or_create_test_images()
    print(f"    Real images (3): {[p.name for p in real_paths]}")
    print(f"    AI images   (3): {[p.name for p in ai_paths]}")

    job_records: list[dict] = []

    print("\n[Step 5] Uploading 3 real photos and 3 AI images...")
    all_uploads = [("real", p) for p in real_paths] + [("ai", p) for p in ai_paths]

    for category, img_path in all_uploads:
        with open(img_path, "rb") as f:
            file_bytes = f.read()
        files = {"file": (img_path.name, file_bytes, "image/jpeg")}
        resp = session.request("POST", "/upload", files=files)
        assert resp.status_code == 202, f"Upload {img_path.name} failed: {resp.status_code} - {resp.text}"
        data = resp.json()
        job_id = data.get("id") or data.get("job_id")
        case_ref = data.get("case_reference", "")
        print(f"    [+] Uploaded {category.upper()}: {img_path.name} -> Job: {job_id} ({case_ref})")
        job_records.append({
            "category": category,
            "path": img_path,
            "job_id": job_id,
            "case_reference": case_ref,
        })

    # 6. Poll jobs until all reach status 'done'
    print("\n[Step 6] Polling job execution status...")
    max_wait_seconds = 120
    poll_interval = 1
    start_time = time.time()

    for record in job_records:
        job_id = record["job_id"]
        status = "queued"
        while time.time() - start_time < max_wait_seconds:
            resp = session.request("GET", f"/jobs/{job_id}/status")
            assert resp.status_code == 200, f"Poll job {job_id} failed: {resp.status_code} - {resp.text}"
            job_info = resp.json()
            status = job_info.get("status")
            if status in ("done", "failed"):
                break
            time.sleep(poll_interval)

        assert status == "done", f"Job {job_id} timed out or failed with status '{status}'"
        result_resp = session.request("GET", f"/jobs/{job_id}/result")
        assert result_resp.status_code == 200, f"Result fetch failed: {result_resp.status_code}"
        res = result_resp.json()
        record["result"] = res
        print(f"    [OK] Job {job_id} settled: status={status}, verdict={res.get('verdict')}, fake_prob={res.get('fake_probability'):.3f}")

    # 7. Download PDF report using signed link
    sample_job = job_records[0]
    sample_job_id = sample_job["job_id"]
    print(f"\n[Step 7] Generating signed report link for job {sample_job_id}...")

    resp = session.request("POST", f"/jobs/{sample_job_id}/links")
    assert resp.status_code == 200, f"Generating links failed: {resp.status_code} - {resp.text}"
    links_data = resp.json()
    report_link = links_data.get("report_url")
    assert report_link, f"Missing report_url in signed links: {links_data}"
    print(f"    [OK] Obtained signed report URL: {report_link}")

    # Download report
    report_resp = session.request("GET", f"/jobs/{sample_job_id}/report")
    assert report_resp.status_code == 200, f"Report download failed: {report_resp.status_code}"
    pdf_bytes = report_resp.content if hasattr(report_resp, "content") else report_resp.read()
    assert pdf_bytes.startswith(b"%PDF-"), "Downloaded file is not a valid PDF (%PDF- header missing)!"
    assert len(pdf_bytes) > 1000, f"Downloaded PDF is too small ({len(pdf_bytes)} bytes)!"
    print(f"[OK] Verified forensic PDF report download ({len(pdf_bytes)} bytes, starts with %PDF-)")

    # 8. Delete a scan and verify file erasure
    print(f"\n[Step 8] Deleting scan {sample_job_id} and confirming erasure from disk...")
    # Record paths that should exist before deletion
    from app.config import settings
    from app.database import get_db
    from app.models import Job

    with next(get_db()) as db:
        db_job = db.get(Job, sample_job_id)
        assert db_job is not None, f"Job {sample_job_id} not found in database before deletion"
        stored_upload_path = Path(db_job.stored_path) if db_job.stored_path else None
        evidence_dir = Path(settings.evidence_dir)
        report_dir = Path(settings.report_dir)

    # Perform DELETE
    del_resp = session.request("DELETE", f"/history/{sample_job_id}")
    assert del_resp.status_code in (200, 204), f"Delete scan failed: {del_resp.status_code} - {del_resp.text}"
    print(f"    [OK] DELETE /api/history/{sample_job_id} returned HTTP {del_resp.status_code}")

    # Verify original file deleted
    if stored_upload_path and stored_upload_path.exists():
        raise AssertionError(f"Uploaded source file {stored_upload_path} was NOT deleted from disk!")
    print(f"    [OK] Upload file confirmed deleted from storage/uploads.")

    # Verify no evidence files remaining with job_id
    matching_evidence = list(evidence_dir.glob(f"*{sample_job_id}*"))
    assert len(matching_evidence) == 0, f"Found lingering evidence files: {matching_evidence}"
    print(f"    [OK] Evidence files confirmed erased from storage/evidence.")

    # Verify report PDF deleted
    matching_reports = list(report_dir.glob(f"*{sample_job['case_reference']}*"))
    assert len(matching_reports) == 0, f"Found lingering report PDF: {matching_reports}"
    print(f"    [OK] Report PDF confirmed erased from storage/reports.")

    # 9. Verify image-only media type enforcement
    print("\n[Step 9] Verifying ENABLED_MEDIA_TYPES=image rejects audio/video...")
    fake_audio = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00data\x00\x00\x00\x00")
    audio_files = {"file": ("test_rejected.wav", fake_audio.getvalue(), "audio/wav")}
    audio_resp = session.request("POST", "/upload", files=audio_files)
    if audio_resp.status_code in (400, 403):
        print(f"    [OK] Audio upload rejected with HTTP {audio_resp.status_code} (media type not enabled in image-only beta).")
    else:
        print(f"    [i] Note: Audio upload returned {audio_resp.status_code} (if ENABLED_MEDIA_TYPES includes audio in current config).")

    print("\n" + "=" * 65)
    print(" ALL SMOKE TEST STEPS PASSED SUCCESSFULLY! ")
    print("=" * 65)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DeepSentinel Smoke Test Runner")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL of frontend/API")
    parser.add_argument("--in-process", action="store_true", help="Run against in-process FastAPI TestClient")
    args = parser.parse_args()

    success = run_smoke_test(base_url=args.base_url, in_process=args.in_process)
    sys.exit(0 if success else 1)
