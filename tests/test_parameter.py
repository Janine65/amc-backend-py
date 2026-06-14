"""Tests for ``/parameter`` (full CRUD on a temporary key)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _unique_key() -> str:
    return f"PYTEST_TMP_{uuid.uuid4().hex[:8].upper()}"


def test_list_parameters(client: TestClient) -> None:
    response = client.get("/parameter")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["data"], list)


def test_find_one_requires_auth(client: TestClient) -> None:
    response = client.get("/parameter/1")
    assert response.status_code == 401


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/parameter/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_parameter_crud_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    key = _unique_key()
    payload = {"key": key, "value": "v1"}

    created = client.post("/parameter", json=payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["id"]
    assert new_id

    try:
        fetched = client.get(f"/parameter/{new_id}", headers=auth_headers)
        assert fetched.status_code == 200
        assert fetched.json()["data"]["key"] == key

        updated = client.patch(f"/parameter/{new_id}", json={"value": "v2"}, headers=auth_headers)
        assert updated.status_code == 200
        assert updated.json()["data"]["value"] == "v2"
    finally:
        deleted = client.delete(f"/parameter/{new_id}", headers=auth_headers)
        assert deleted.status_code == 200, deleted.text

    not_found = client.get(f"/parameter/{new_id}", headers=auth_headers)
    assert not_found.status_code == 404
