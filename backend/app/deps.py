"""Shared FastAPI dependencies: authentication and rate limiting."""

from __future__ import annotations

import ipaddress
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UploadEvent, User
from app.security import decode_access_token

# auto_error=False so guest access stays possible on endpoints that allow it.
bearer_scheme = HTTPBearer(auto_error=False)


def user_from_token(token: str | None, db: Session) -> User | None:
    """The active user a session token belongs to, or ``None``."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        return None
    return user


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the Bearer token (API clients) or the httpOnly session cookie (browser).

    Tokens are never read from the query string: URLs end up in proxy logs and
    browser history. Links that must work without headers (report download,
    WebSocket) use short-lived signed URLs instead (app/signing.py).
    """
    token = credentials.credentials if credentials else request.cookies.get(settings.auth_cookie_name)
    return user_from_token(token, db)


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    """Require an authenticated, active user."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@lru_cache(maxsize=8)
def _trusted_networks(entries: tuple[str, ...]) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(entry, strict=False) for entry in entries)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """The address a request is counted under for rate limiting.

    X-Real-IP is used only when the connection itself comes from a trusted
    reverse proxy (``TRUSTED_PROXIES``; the nginx in frontend/ sets it from
    $remote_addr). Any other client can write whatever headers it likes, so
    X-Forwarded-For is never used and X-Real-IP from an untrusted peer is ignored.
    """
    peer = request.client.host if request.client else "unknown"
    peer_ip = _parse_ip(peer)
    if peer_ip is not None and any(peer_ip in net for net in _trusted_networks(tuple(settings.trusted_proxies))):
        real = _parse_ip(request.headers.get("x-real-ip"))
        if real is not None:
            return str(real)
    return peer


def enforce_upload_rate_limit(db: Session, user: User | None, ip: str) -> None:
    """Cap uploads per hour so inference resources cannot be trivially drained.

    Registered users are counted by account; guests by IP address.
    """
    window_start = datetime.now(UTC) - timedelta(hours=1)
    limit = settings.upload_rate_limit_per_hour if user else settings.guest_rate_limit_per_hour

    condition = (UploadEvent.user_id == user.id) if user else (UploadEvent.client_ip == ip)
    recent = (
        db.scalar(
            select(func.count())
            .select_from(UploadEvent)
            .where(UploadEvent.created_at >= window_start, condition)
        )
        or 0
    )

    if recent >= limit:
        scope = "account" if user else "guest (unauthenticated)"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Upload limit reached for this {scope}: {limit} uploads per hour. "
                + ("Sign in for a higher limit." if not user else "Try again later.")
            ),
            headers={"Retry-After": "3600"},
        )

    # Commit the attempt now, not with the job. A rejected upload still consumed
    # bandwidth, disk and validation work; if the event only landed alongside a
    # successfully created job, an attacker could send unlimited malformed files
    # and never be counted.
    db.add(UploadEvent(user_id=user.id if user else None, client_ip=ip))
    db.commit()
