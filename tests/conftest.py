"""Pytest fixtures – shared HTTP client and auth headers.

The tests run in-process via ``fastapi.testclient.TestClient`` against the
real database and credentials configured in ``.env``. Rate limiting is
disabled to avoid spurious 429s during the test run.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load .env *before* importing the app so DATABASE_URL etc. are picked up.
load_dotenv()

from app.main import app, limiter  # noqa: E402

# Disable slowapi default limits (10/sec, 100/min) for the whole test run.
limiter.enabled = False


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Shared ``TestClient`` with FastAPI lifespan executed exactly once."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def login_credentials() -> dict[str, str]:
    email = os.environ.get("LOGIN_EMAIL")
    password = os.environ.get("LOGIN_PASSWORD")
    if not email or not password:
        pytest.skip("LOGIN_EMAIL / LOGIN_PASSWORD not set in .env")
    return {"email": email, "password": password}


@pytest.fixture(scope="session")
def access_token(client: TestClient, login_credentials: dict[str, str]) -> str:
    response = client.post("/auth/login", json=login_credentials)
    assert response.status_code == 200, f"Login failed: {response.status_code} {response.text}"
    payload = response.json()
    token = payload.get("cookie", {}).get("accessToken")
    assert token, f"No accessToken in login response: {payload}"
    return token


@pytest.fixture(scope="session")
def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="session")
def clubjahr() -> int:
    """Aktuelles Geschäftsjahr aus der Parameter-Tabelle (CLUBJAHR), Fallback heute."""
    from datetime import datetime

    from app.core.config import get_config

    cfg = get_config()
    raw = cfg.params.get("CLUBJAHR") if cfg.params else None
    try:
        return int(raw) if raw else datetime.utcnow().year
    except (TypeError, ValueError):
        return datetime.utcnow().year
