"""Tests for ``/journal-receipt``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/journal-receipt").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/journal-receipt", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_by_journal(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/journal-receipt/getbyjournalid",
        params={"journalid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_get_by_receipt(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/journal-receipt/getbyreceiptid",
        params={"receiptid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_delete_unknown_pair(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete(
        "/journal-receipt",
        params={"journalid": -1, "receiptid": -1},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["count"] == 0


def test_add2journal_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/journal-receipt/add2journal",
        params={"journalid": -1},
        json=[],
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["count"] == 0
