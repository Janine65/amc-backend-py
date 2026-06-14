"""JWT signing/verification and password hashing helpers."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

ROUNDS_OF_HASHING = 10
DEV_FALLBACK_SECRET = "dev-only-secret-do-not-use-in-production-environment"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=ROUNDS_OF_HASHING)


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret or len(secret) < 32:
        if (os.environ.get("APP_ENV") or os.environ.get("NODE_ENV")) == "production":
            raise RuntimeError(
                "JWT_SECRET environment variable is required in production and must be at least 32 characters."
            )
        return DEV_FALLBACK_SECRET
    return secret


def get_jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")


def get_jwt_expires_in_seconds() -> int:
    raw = os.environ.get("JWT_EXPIRES_IN", "3600")
    try:
        return int(raw)
    except ValueError:
        # Allow values like "1h", "30m", "60s" similar to NestJS.
        unit = raw[-1]
        try:
            value = int(raw[:-1])
        except ValueError as exc:
            raise RuntimeError(f"Invalid JWT_EXPIRES_IN: {raw}") from exc
        return {"s": value, "m": value * 60, "h": value * 3600, "d": value * 86400}.get(unit, 3600)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(payload: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(seconds=get_jwt_expires_in_seconds())
    to_encode: dict[str, Any] = {**payload, "exp": expire}
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=get_jwt_algorithm())


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
    except JWTError as exc:  # pragma: no cover
        raise ValueError(str(exc)) from exc
