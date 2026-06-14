"""Tests for ``/clubmeister``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_public(client: TestClient) -> None:
    response = client.get("/clubmeister/overview")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/clubmeister").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/clubmeister", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_byjahr(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/clubmeister/byjahr",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/clubmeister/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/clubmeister/99999999", json={"rang": 1}, headers=auth_headers)
    assert response.status_code == 404
