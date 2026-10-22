"""Deleting a job's files: on request ("Delete scan") and automatically for guests.

Every file a job produces is named so it can be found again:

* the upload: ``STORAGE_DIR/<job id><ext>`` (``job.stored_path``);
* evidence images: ``EVIDENCE_DIR/<job id>_*.png``, plus any other file named
  by a ``*_file`` key anywhere in ``job.evidence``;
* reports: ``REPORT_DIR/DFR-<case reference>.pdf`` (and each report's
  ``file_path``), with their charts in ``EVIDENCE_DIR/report_charts/DFR-<case reference>_*``.

Nothing outside STORAGE_DIR, EVIDENCE_DIR and REPORT_DIR is ever deleted, so a
crafted evidence value cannot point the deleter elsewhere.

Guest jobs (no account) older than ``RETENTION_HOURS`` are purged by the Celery
beat task ``maintenance.purge_expired_guest_jobs`` (hourly), or by hand with
``python -m app.retention`` when running without Celery.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, UploadEvent

logger = logging.getLogger(__name__)


def _roots() -> list[Path]:
    return [Path(settings.storage_dir).resolve(), Path(settings.evidence_dir).resolve(), Path(settings.report_dir).resolve()]


def _inside_roots(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in _roots())


def _evidence_file_names(value: Any) -> set[str]:
    """Every string stored under a key ending in ``_file``, at any depth."""
    names: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.endswith("_file") and isinstance(item, str) and item:
                names.add(item)
            else:
                names |= _evidence_file_names(item)
    elif isinstance(value, list):
        for item in value:
            names |= _evidence_file_names(item)
    return names


def job_files(job: Job) -> list[Path]:
    """Every file on disk that belongs to ``job``."""
    evidence_dir = Path(settings.evidence_dir)
    report_dir = Path(settings.report_dir)
    candidates: set[Path] = set()

    if job.stored_path:
        candidates.add(Path(job.stored_path))
    for name in _evidence_file_names(job.evidence or {}):
        candidates.add(evidence_dir / Path(name).name)  # bare name only: no directory escapes
    if evidence_dir.is_dir():
        candidates.update(evidence_dir.glob(f"{job.id}_*"))

    references = {f"DFR-{job.case_reference}"} | {r.report_reference for r in job.reports}
    for report in job.reports:
        if report.file_path:
            candidates.add(Path(report.file_path))
    for reference in references:
        candidates.add(report_dir / f"{reference}.pdf")
        charts = evidence_dir / "report_charts"
        if charts.is_dir():
            candidates.update(charts.glob(f"{reference}_*"))

    return sorted(path for path in candidates if path.is_file() and _inside_roots(path))


def delete_job_files(job: Job) -> list[Path]:
    """Delete every file of ``job``; returns what was removed."""
    removed = []
    for path in job_files(job):
        try:
            path.unlink()
            removed.append(path)
        except FileNotFoundError:
            pass
        except OSError as exc:  # pragma: no cover - permissions, locked files on Windows
            logger.warning("Could not delete %s: %s", path, exc)
    return removed


def purge_expired_guest_jobs(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Delete guest jobs older than RETENTION_HOURS, with all their files and reports.

    Also drops upload-audit rows (they hold IP addresses) older than the same
    window, but never younger than the one hour the rate limiter looks at.
    """
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.retention_hours)
    jobs = db.scalars(select(Job).where(Job.user_id.is_(None), Job.uploaded_at < cutoff)).all()
    files = 0
    for job in jobs:
        files += len(delete_job_files(job))
        db.delete(job)  # reports cascade
    event_cutoff = now - timedelta(hours=max(settings.retention_hours, 1))
    events = db.execute(delete(UploadEvent).where(UploadEvent.created_at < event_cutoff)).rowcount or 0
    db.commit()
    summary = {"jobs": len(jobs), "files": files, "upload_events": int(events)}
    if jobs or events:
        logger.info("Retention purge (%d h): %s", settings.retention_hours, summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - manual use without Celery beat
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        print(purge_expired_guest_jobs(session))
    finally:
        session.close()
