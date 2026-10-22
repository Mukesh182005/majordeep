"""Short-lived signed URLs for the report download and the job WebSocket.

A browser cannot attach an Authorization header to a plain link or to a
WebSocket handshake, so these two endpoints used to accept the login token as
``?token=``, which put long-lived credentials into proxy logs and browser
history. Instead, an authorised client asks ``POST /api/jobs/{id}/links`` for
URLs carrying ``exp`` (Unix time) and ``sig``, an HMAC-SHA256 over the
purpose, the job id and the expiry. A signature opens one job, for one
purpose, for ``SIGNED_URL_TTL_SECONDS`` (default 5 minutes).

The HMAC key is derived from JWT_SECRET_KEY, so rotating that secret also
invalidates outstanding links.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from app.config import settings

PURPOSES = ("report", "ws")


def _key() -> bytes:
    return hmac.new(settings.jwt_secret_key.encode(), b"deepsentinel-signed-url-v1", hashlib.sha256).digest()


def _signature(job_id: str, purpose: str, expires: int) -> str:
    message = f"{purpose}:{job_id}:{expires}".encode()
    return hmac.new(_key(), message, hashlib.sha256).hexdigest()


def sign(job_id: str, purpose: str, now: float | None = None) -> dict[str, str]:
    """Query parameters that open ``job_id`` for ``purpose`` until the expiry."""
    if purpose not in PURPOSES:
        raise ValueError(f"unknown signed-URL purpose {purpose!r}")
    expires = int(now if now is not None else time.time()) + settings.signed_url_ttl_seconds
    return {"exp": str(expires), "sig": _signature(job_id, purpose, expires)}


def signed_query(job_id: str, purpose: str, now: float | None = None) -> str:
    return urlencode(sign(job_id, purpose, now))


def verify(job_id: str, purpose: str, exp: str | int | None, sig: str | None, now: float | None = None) -> bool:
    """True when ``sig`` is a valid, unexpired signature for this job and purpose."""
    if not exp or not sig or purpose not in PURPOSES:
        return False
    try:
        expires = int(exp)
    except (TypeError, ValueError):
        return False
    current = now if now is not None else time.time()
    # Expired, or further in the future than this server ever issues: refuse.
    if expires < current or expires > current + settings.signed_url_ttl_seconds + 5:
        return False
    return hmac.compare_digest(_signature(job_id, purpose, expires), sig)
