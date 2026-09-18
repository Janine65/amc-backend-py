"""Tests für die Homepage-Module (``/public``, ``/news``, ``/berichte``,
``/anmeldungen``, ``/jahrfreigabe``)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# /public – ohne Login erreichbar
# ---------------------------------------------------------------------------


def test_public_news(client: TestClient) -> None:
    response = client.get("/public/news")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_public_berichte(client: TestClient) -> None:
    response = client.get("/public/berichte")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_public_agenda(client: TestClient) -> None:
    response = client.get("/public/agenda")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_public_jahre(client: TestClient) -> None:
    response = client.get("/public/jahre")
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["data"], list)


def test_public_meister_nicht_freigegeben(client: TestClient) -> None:
    """Jahr 1900 ist sicher nicht freigegeben → 404."""
    assert client.get("/public/clubmeister", params={"jahr": "1900"}).status_code == 404
    assert client.get("/public/kegelmeister", params={"jahr": "1900"}).status_code == 404


def test_public_anmeldung_honeypot(client: TestClient) -> None:
    """Honeypot-Feld ausgefüllt → stillschweigend 201, kein Insert."""
    response = client.post(
        "/public/anmeldung",
        json={
            "anlassid": 1,
            "name": "Bot",
            "vorname": "Spam",
            "email": "bot@example.com",
            "website": "http://spam.example.com",
        },
    )
    assert response.status_code == 201, response.text


def test_public_anmeldung_unbekannter_anlass(client: TestClient) -> None:
    response = client.post(
        "/public/anmeldung",
        json={
            "anlassid": 99999999,
            "name": "Muster",
            "vorname": "Max",
            "email": "max@example.com",
        },
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Admin-Router benötigen Login
# ---------------------------------------------------------------------------


def test_admin_requires_auth(client: TestClient) -> None:
    assert client.get("/news").status_code == 401
    assert client.get("/berichte").status_code == 401
    assert client.get("/anmeldungen").status_code == 401
    assert client.get("/jahrfreigabe").status_code == 401


def test_news_crud_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "titel": "PYTEST_NEWS",
        "text": "Testinhalt",
        "datum": date.today().isoformat(),
        "publiziert": False,
    }
    created = client.post("/news", json=payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["id"]
    try:
        fetched = client.get(f"/news/{new_id}", headers=auth_headers)
        assert fetched.status_code == 200
        assert fetched.json()["data"]["titel"] == "PYTEST_NEWS"

        updated = client.patch(f"/news/{new_id}", json={"publiziert": True}, headers=auth_headers)
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["publiziert"] is True

        # jetzt öffentlich sichtbar
        public = client.get("/public/news")
        assert any(n["id"] == new_id for n in public.json()["data"])
    finally:
        deleted = client.delete(f"/news/{new_id}", headers=auth_headers)
        assert deleted.status_code == 200


def test_bericht_crud_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "titel": "PYTEST_BERICHT",
        "text": "Testinhalt",
        "datum": date.today().isoformat(),
        "publiziert": False,
    }
    created = client.post("/berichte", json=payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["id"]
    try:
        updated = client.patch(f"/berichte/{new_id}", json={"titel": "PYTEST_BERICHT_2"}, headers=auth_headers)
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["titel"] == "PYTEST_BERICHT_2"
        # nicht publiziert → nicht öffentlich
        public = client.get("/public/berichte")
        assert not any(b["id"] == new_id for b in public.json()["data"])
    finally:
        deleted = client.delete(f"/berichte/{new_id}", headers=auth_headers)
        assert deleted.status_code == 200


def test_jahrfreigabe_und_public_meister(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Freigabe für Jahr 1901 setzen, öffentliche Sichtbarkeit prüfen, wieder sperren."""
    upserted = client.put(
        "/jahrfreigabe",
        json={"jahr": "1901", "clubmeister": True, "kegelmeister": False},
        headers=auth_headers,
    )
    assert upserted.status_code == 200, upserted.text
    try:
        response = client.get("/public/clubmeister", params={"jahr": "1901"})
        assert response.status_code == 200
        for eintrag in response.json()["data"]:
            # Nachname wird öffentlich nur abgekürzt ausgeliefert
            assert eintrag["nachname"] is None or len(eintrag["nachname"]) <= 2
        assert client.get("/public/kegelmeister", params={"jahr": "1901"}).status_code == 404
        jahre = client.get("/public/jahre").json()["data"]
        assert any(j["jahr"] == "1901" for j in jahre)
    finally:
        locked = client.put(
            "/jahrfreigabe",
            json={"jahr": "1901", "clubmeister": False, "kegelmeister": False},
            headers=auth_headers,
        )
        assert locked.status_code == 200
        assert client.get("/public/clubmeister", params={"jahr": "1901"}).status_code == 404


def test_anmeldung_kegeln_abgelehnt(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Kegel-Anlässe benötigen keine Anmeldung → 400."""
    anlass_payload = {
        "datum": (date.today() + timedelta(days=30)).isoformat(),
        "name": "PYTEST_KEGEL_ANLASS",
        "longname": "PYTEST_KEGEL_ANLASS",
        "punkte": 0,
        "istkegeln": True,
        "istsamanlass": False,
        "nachkegeln": False,
        "gaeste": 0,
        "status": 1,
    }
    created = client.post("/anlaesse", json=anlass_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    anlass_id = created.json()["data"]["id"]
    try:
        anmeldung = client.post(
            "/public/anmeldung",
            json={
                "anlassid": anlass_id,
                "name": "Muster",
                "vorname": "Max",
                "email": "kegel@example.com",
            },
        )
        assert anmeldung.status_code == 400
    finally:
        client.delete(f"/anlaesse/{anlass_id}", headers=auth_headers)


def test_anmeldung_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Temporären Anlass erstellen, öffentlich anmelden, verwalten, aufräumen."""
    anlass_payload = {
        "datum": (date.today() + timedelta(days=30)).isoformat(),
        "name": "PYTEST_HOMEPAGE_ANLASS",
        "longname": "PYTEST_HOMEPAGE_ANLASS",
        "punkte": 0,
        "istkegeln": False,
        "istsamanlass": False,
        "nachkegeln": False,
        "gaeste": 0,
        "status": 1,
    }
    created = client.post("/anlaesse", json=anlass_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    anlass_id = created.json()["data"]["id"]
    anmeldung_id: int | None = None
    try:
        anmeldung = client.post(
            "/public/anmeldung",
            json={
                "anlassid": anlass_id,
                "name": "Muster",
                "vorname": "Max",
                "email": "pytest@example.com",
                "bemerkung": "Testanmeldung",
            },
        )
        assert anmeldung.status_code == 201, anmeldung.text

        # Doppelte Anmeldung → 409
        doppelt = client.post(
            "/public/anmeldung",
            json={
                "anlassid": anlass_id,
                "name": "Muster",
                "vorname": "Max",
                "email": "pytest@example.com",
            },
        )
        assert doppelt.status_code == 409

        rows = client.get("/anmeldungen", params={"anlassid": anlass_id}, headers=auth_headers).json()["data"]
        assert len(rows) == 1
        anmeldung_id = rows[0]["id"]

        updated = client.patch(f"/anmeldungen/{anmeldung_id}", json={"status": 2}, headers=auth_headers)
        assert updated.status_code == 200
        assert updated.json()["data"]["status"] == 2
    finally:
        if anmeldung_id is not None:
            client.delete(f"/anmeldungen/{anmeldung_id}", headers=auth_headers)
        deleted = client.delete(f"/anlaesse/{anlass_id}", headers=auth_headers)
        assert deleted.status_code == 200
