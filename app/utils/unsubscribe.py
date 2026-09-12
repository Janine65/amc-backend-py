"""Signed tokens for the public unsubscribe endpoint (HMAC-SHA256)."""

from __future__ import annotations

import hashlib
import hmac
import os

from app.core.config import get_config


def _secret() -> str:
    cfg = get_config()
    return str(cfg.raw.get("unsubscribe_secret") or os.environ.get("UNSUBSCRIBE_SECRET") or "")


def make_token(email: str) -> str:
    """Token für eine E-Mail-Adresse; leer, wenn kein Secret konfiguriert ist."""
    secret = _secret()
    if not secret:
        return ""
    normalized = email.strip().lower().encode()
    return hmac.new(secret.encode(), normalized, hashlib.sha256).hexdigest()


def verify_token(email: str, token: str) -> bool:
    expected = make_token(email)
    return bool(expected) and hmac.compare_digest(expected, token)
