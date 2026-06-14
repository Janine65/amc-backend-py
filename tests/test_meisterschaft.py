"""Tests for ``/meisterschaft``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/meisterschaft").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/meisterschaft", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_list_event_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/meisterschaft/listevent",
        params={"eventid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_list_mitglied_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/meisterschaft/listmitglied",
        params={"mitgliedid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_list_mitglied_meister_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/meisterschaft/listmitgliedmeister",
        params={"mitgliedid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_check_jahr(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/meisterschaft/checkjahr",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], int)


def test_get_chart_data(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/meisterschaft/getchartdata",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/meisterschaft/99999999", headers=auth_headers)
    assert response.status_code in (200, 404)


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/meisterschaft/99999999",
        json={"punkte": 5},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/meisterschaft/99999999", headers=auth_headers)
    assert response.status_code == 404
