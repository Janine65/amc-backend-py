"""Tests for ``/anlaesse`` (incl. small CRUD cycle on a temporary entry)."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def test_overview_public(client: TestClient) -> None:
    response = client.get("/anlaesse/overview")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_get_fk_data_requires_auth(client: TestClient) -> None:
    assert client.get("/anlaesse/getFkData", params={"jahr": "2000"}).status_code == 401


def test_get_fk_data(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/anlaesse/getFkData",
        params={"jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_all_requires_auth(client: TestClient, clubjahr: int) -> None:
    assert client.get("/anlaesse", params={"fromJahr": clubjahr, "toJahr": clubjahr}).status_code == 401


def test_find_all(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/anlaesse",
        params={"fromJahr": clubjahr, "toJahr": clubjahr},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_find_one_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/anlaesse/99999999", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_writestammblatt_template(client: TestClient, auth_headers: dict[str, str], clubjahr: int) -> None:
    response = client.get(
        "/anlaesse/writestammblatt",
        params={"type": 0, "jahr": str(clubjahr)},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["filename"].endswith(".xlsx")


def test_anlaesse_crud_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Erstellt – liest – aktualisiert – löscht einen temporären Anlass."""
    payload = {
        "datum": date(2099, 1, 1).isoformat(),
        "name": "PYTEST_TMP",
        "longname": "PYTEST_TMP placeholder",
        "punkte": 0,
        "istkegeln": False,
        "istsamanlass": False,
        "nachkegeln": False,
        "gaeste": 0,
        "status": 1,
    }
    created = client.post("/anlaesse", json=payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["id"]
    try:
        fetched = client.get(f"/anlaesse/{new_id}", headers=auth_headers)
        assert fetched.status_code == 200
        assert fetched.json()["data"]["id"] == new_id

        updated = client.patch(
            f"/anlaesse/{new_id}",
            json={"name": "PYTEST_TMP_UPDATED"},
            headers=auth_headers,
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["name"] == "PYTEST_TMP_UPDATED"
    finally:
        deleted = client.delete(f"/anlaesse/{new_id}", headers=auth_headers)
        assert deleted.status_code == 200


def test_update_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch("/anlaesse/99999999", json={"name": "x"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete("/anlaesse/99999999", headers=auth_headers)
    assert response.status_code == 404
