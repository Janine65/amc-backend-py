"""Tests for ``/fiscalyear``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/fiscalyear").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/fiscalyear", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/fiscalyear/99999999", headers=auth_headers)
    assert response.status_code in (200, 404)


def test_get_fk(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/fiscalyear/getfiscalyearfk", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_by_year_unknown(client: TestClient) -> None:
    response = client.get("/fiscalyear/getbyyear", params={"year": 1900})
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_close_year_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/fiscalyear/closeyear",
        params={"year": 1900, "state": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "error"


def test_writebilanz(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get("/fiscalyear/writebilanz", params={"year": clubjahr}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["filename"].endswith(".xlsx")
