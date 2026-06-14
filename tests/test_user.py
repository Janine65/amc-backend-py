"""Tests for ``/user`` (read-only — destructive actions skipped to keep DB intact)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    response = client.get("/user")
    assert response.status_code == 401


def test_list_users(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/user", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["data"], list)
    emails = {row["email"] for row in body["data"]}
    assert os.environ["LOGIN_EMAIL"] in emails


def test_find_one_requires_auth(client: TestClient) -> None:
    response = client.get("/user/1")
    assert response.status_code == 401


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/user/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_find_one_login_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    list_resp = client.get("/user", headers=auth_headers)
    assert list_resp.status_code == 200
    me = next(u for u in list_resp.json()["data"] if u["email"] == os.environ["LOGIN_EMAIL"])
    response = client.get(f"/user/{me['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == me["id"]
