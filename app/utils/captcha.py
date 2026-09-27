"""Stateless Rechen-Captcha: Frage plus HMAC-signiertes Token mit Ablaufzeit."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from app.core.security import get_jwt_secret

TTL_SECONDS = 600


def _sign(answer: int, expiry: int, nonce: str) -> str:
    payload = f"captcha:{answer}:{expiry}:{nonce}".encode()
    return hmac.new(get_jwt_secret().encode(), payload, hashlib.sha256).hexdigest()


def create_captcha() -> tuple[str, str]:
    """Liefert (frage, token), z. B. ("3 + 4", "<expiry>:<nonce>:<signatur>")."""
    a = secrets.randbelow(9) + 1
    b = secrets.randbelow(9) + 1
    expiry = int(time.time()) + TTL_SECONDS
    nonce = secrets.token_hex(8)
    return f"{a} + {b}", f"{expiry}:{nonce}:{_sign(a + b, expiry, nonce)}"


def verify_captcha(token: str | None, antwort: str | None) -> bool:
    if not token or not antwort:
        return False
    try:
        expiry_str, nonce, sig = token.split(":")
        expiry = int(expiry_str)
        answer = int(str(antwort).strip())
    except ValueError:
        return False
    if expiry < time.time():
        return False
    return hmac.compare_digest(sig, _sign(answer, expiry, nonce))
