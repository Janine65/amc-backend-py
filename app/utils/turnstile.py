"""Server-side Cloudflare Turnstile verification for public forms."""

from __future__ import annotations

import os
from typing import Literal

import httpx
from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
UNAVAILABLE = "Spam-Schutz derzeit nicht verfügbar. Bitte später erneut versuchen."


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        logger.error("Turnstile configuration missing: %s", name)
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    return value


def get_turnstile_site_key() -> str:
    _required_env("CLOUDFLARE_TURNSPIKE_SECRET")
    return _required_env("CLOUDFLARE_TURNSPIKE_SITEKEY")


async def verify_turnstile(token: str | None, *, action: Literal["kontakt", "anmeldung"]) -> None:
    if not token or not token.strip():
        raise HTTPException(status_code=400, detail="Bitte die Sicherheitsprüfung abschliessen.")

    secret = _required_env("CLOUDFLARE_TURNSPIKE_SECRET")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(SITEVERIFY_URL, data={"secret": secret, "response": token})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Turnstile verification request failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from exc

    try:
        result = response.json()
    except ValueError as exc:
        logger.error("Turnstile returned invalid JSON")
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from exc

    if not isinstance(result, dict) or type(result.get("success")) is not bool:
        logger.error("Turnstile returned an invalid verification response")
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    errors = result.get("error-codes", [])
    if not isinstance(errors, list) or not all(isinstance(code, str) for code in errors):
        logger.error("Turnstile returned invalid error codes")
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    if {"missing-input-secret", "invalid-input-secret", "internal-error"} & set(errors):
        logger.error("Turnstile service or secret configuration error")
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    if result["success"] is not True or result.get("action") != action:
        raise HTTPException(
            status_code=400,
            detail="Sicherheitsprüfung fehlgeschlagen oder abgelaufen. Bitte erneut versuchen.",
        )
