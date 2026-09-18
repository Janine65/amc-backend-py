"""Shared slowapi rate limiter (importierbar ohne Zirkular-Import auf ``app.main``)."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "10/second"],
)
