"""Shared slowapi rate limiter (importierbar ohne Zirkular-Import auf ``app.main``)."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Echte Client-IP: erster Eintrag aus X-Forwarded-For (SSR-Homepage/Proxy), sonst Remote-Adresse."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100/minute", "10/second"],
)
