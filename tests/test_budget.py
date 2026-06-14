"""Tests for ``/budget``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/budget", params={"year": 2000}).status_code == 401


def test_find_all_by_year(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get("/budget", params={"year": clubjahr}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/budget/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_copyyear_alias_disabled(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.put(
        "/budget/copyyear",
        params={"from_": clubjahr, "to": clubjahr + 100},
        headers=auth_headers,
    )
    # alias route always raises 501 (use canonical /budget/copy instead)
    assert response.status_code == 501


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/budget/99999999", json={"amount": 1.0}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/budget/99999999", headers=auth_headers)
    assert response.status_code == 404
