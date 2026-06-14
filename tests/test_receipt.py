"""Tests for ``/receipt``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/receipt", params={"year": "2000"}).status_code == 401


def test_find_all_year(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get("/receipt", params={"year": str(clubjahr)}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/receipt/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_find_all_attachments(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/receipt/findallatt",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_attachments_for_journal(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/receipt/findatt",
        params={"journalid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_uploadatt_missing(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/receipt/uploadatt",
        params={"filename": "does-not-exist.pdf", "year": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/receipt/99999999",
        json={"bezeichnung": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/receipt/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_create_no_files(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.post(
        "/receipt",
        json={"year": str(clubjahr), "uploadfiles": ""},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["files"] == []


def test_att2journal_empty(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.post(
        "/receipt/att2journal",
        json={"year": str(clubjahr), "uploadfiles": "", "journalId": 1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["files"] == []
