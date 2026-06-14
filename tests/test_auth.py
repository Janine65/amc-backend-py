"""Tests for ``/auth`` and meta endpoints (``/about``, ``/health``)."""

from __future__ import annotations

from fastapi.testclient import TestClient


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
