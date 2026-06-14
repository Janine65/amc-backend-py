"""Tests for ``/journal``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/journal").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/journal", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_by_year(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get("/journal/getbyyear", params={"year": clubjahr}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_by_account(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/journal/getaccdata",
        params={"account": -1, "year": clubjahr},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/journal/99999999", headers=auth_headers)
    assert response.status_code in (200, 404)


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/journal/99999999", json={"memo": "x"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/journal/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_write_journal(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/journal/write",
        params={"year": clubjahr, "receipt": 0},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["filename"]
