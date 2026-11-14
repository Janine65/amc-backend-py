"""Tests for ``/auth`` and meta endpoints (``/about``, ``/health``)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.security import DEV_FALLBACK_SECRET, create_access_token, decode_access_token


@pytest.fixture
def jwt_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", DEV_FALLBACK_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRES_IN", "60")


def test_jwt_legacy_token_compatibility(jwt_config: None) -> None:
    # Generated with python-jose 3.5.0 and the public development key.
    token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJ1c2VySWQiOjQyLCJleHAiOjQxMDI0NDQ4MDB9."
        "b9q8RU8mTKq5O4_679gdJ7AVPN7jBMPgk5PwVuWTVvA"
    )
    assert decode_access_token(token) == {"userId": 42, "exp": 4102444800}


def test_jwt_create_and_decode(jwt_config: None) -> None:
    payload = {"userId": 42}
    before = int(datetime.now(UTC).timestamp())
    token = create_access_token(payload)
    claims = jwt.decode(token, DEV_FALLBACK_SECRET, algorithms=["HS256"])

    assert decode_access_token(token) == claims
    assert claims["userId"] == 42
    assert before + 60 <= claims["exp"] <= int(datetime.now(UTC).timestamp()) + 60
    assert payload == {"userId": 42}


@pytest.mark.parametrize(
    ("payload", "key", "algorithm"),
    [
        ({"userId": 42, "exp": 0}, DEV_FALLBACK_SECRET, "HS256"),
        ({"userId": 42}, "another-test-secret-that-is-at-least-32-characters", "HS256"),
        ({"userId": 42}, DEV_FALLBACK_SECRET, "HS384"),
    ],
    ids=["expired", "invalid-signature", "unexpected-algorithm"],
)
def test_jwt_rejects_invalid_tokens(jwt_config: None, payload: dict[str, Any], key: str, algorithm: str) -> None:
    token = jwt.encode(payload, key, algorithm=algorithm)
    with pytest.raises(ValueError):
        decode_access_token(token)


def test_jwt_rejects_malformed_token(jwt_config: None) -> None:
    with pytest.raises(ValueError):
        decode_access_token("not-a-jwt")


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_about(client: TestClient) -> None:
    response = client.get("/about")
    assert response.status_code == 200
    body = response.json()
    assert {"name", "version", "author"}.issubset(body.keys())


def test_login_success(client: TestClient, login_credentials: dict[str, str]) -> None:
    response = client.post("/auth/login", json=login_credentials)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cookie"]["accessToken"]
    assert body["data"]["email"] == login_credentials["email"]


def test_login_invalid(client: TestClient, login_credentials: dict[str, str]) -> None:
    response = client.post(
        "/auth/login",
        json={"email": login_credentials["email"], "password": "definitely-not-the-password"},
    )
    assert response.status_code == 401


def test_token_oauth2_success(client: TestClient, login_credentials: dict[str, str]) -> None:
    response = client.post(
        "/auth/token",
        data={
            "username": login_credentials["email"],
            "password": login_credentials["password"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_token_oauth2_invalid(client: TestClient, login_credentials: dict[str, str]) -> None:
    response = client.post(
        "/auth/token",
        data={"username": login_credentials["email"], "password": "wrong"},
    )
    assert response.status_code == 401


def test_refresh_token_requires_auth(client: TestClient) -> None:
    response = client.get("/auth/refreshToken")
    assert response.status_code == 401


def test_refresh_token_success(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/auth/refreshToken", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cookie"]["accessToken"]


def test_refresh_token_invalid_token(client: TestClient) -> None:
    response = client.get("/auth/refreshToken", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
