"""Tests for ``/kegelmeister``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_public(client: TestClient) -> None:
    response = client.get("/kegelmeister/overview")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/kegelmeister").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/kegelmeister", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_byjahr(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/kegelmeister/byjahr",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/kegelmeister/99999999", headers=auth_headers)
    assert response.status_code in (200, 404)


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/kegelmeister/99999999", json={"rang": 1}, headers=auth_headers)
    assert response.status_code == 404
