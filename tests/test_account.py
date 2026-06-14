"""Tests for ``/account``."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/account").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/account", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/account/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_account_jahr(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/account/getaccjahr",
        params={"jahr": clubjahr, "all": 0},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_one_by_order_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/account/getonedatabyorder", params={"order": -1}, headers=auth_headers)
    assert response.status_code == 404


def test_get_amount_one_acc(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/account/getamountoneacc",
        params={"order": -1, "date": date(clubjahr, 12, 31).isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["amount"] == "0.00"


def test_get_fk_data(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/account/getfkdata", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_account_summary(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get("/account/getaccountsummary", params={"jahr": clubjahr}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_writekontoauszug(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/account/writekontoauszug",
        params={"year": clubjahr, "all": False},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["filename"].endswith(".xlsx")
