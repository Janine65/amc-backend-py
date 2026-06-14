"""Tests for ``/adressen``."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_public(client: TestClient) -> None:
    """``/adressen/overview`` ist absichtlich ohne Auth."""
    response = client.get("/adressen/overview")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["data"], list)
    labels = {row["label"] for row in body["data"]}
    assert "Aktive Mitglieder" in labels


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/adressen").status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/adressen", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_fk_data(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/adressen/getFkData", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/adressen/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/adressen/99999999", json={"name": "x"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/adressen/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_export_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/adressen/export", json=[], headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["filename"].endswith(".xlsx")


def test_sendmail_no_recipients(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/adressen/sendmail",
        json={"email_subject": "Test", "email_body": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "error"
    assert "recipients" in body["message"].lower()


def test_sendmail_no_body(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/adressen/sendmail",
        json={"email_subject": "Test", "email_body": "", "email_an": "noone@example.invalid"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "error"
    assert "message" in body["message"].lower()


def test_qrbill_unknown_address(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/adressen/qrbill", params={"id": 99999999}, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "error"
