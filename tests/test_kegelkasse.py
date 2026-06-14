"""Tests for ``/kegelkasse``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/kegelkasse").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/kegelkasse", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_kasse_by_datum(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/kegelkasse/kassebydatum",
        params={"monat": 1, "jahr": clubjahr},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "data" in body


def test_kasse_by_jahr(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/kegelkasse/kassebyjahr",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_genreceipt_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/kegelkasse/genreceipt",
        params={"kegelkasseId": 99999999},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "error"


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/kegelkasse/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/kegelkasse/99999999", json={"kasse": 0.0}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/kegelkasse/99999999", headers=auth_headers)
    assert response.status_code == 404
