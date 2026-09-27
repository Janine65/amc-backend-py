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


def test_public_besucher(client: TestClient) -> None:
    before = client.get("/public/besucher")
    assert before.status_code == 200, before.text
    counted = client.post("/public/besucher")
    assert counted.status_code == 200, counted.text
    assert counted.json()["data"] == before.json()["data"] + 1


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


def _solve_captcha(client: TestClient) -> dict[str, str]:
    """Holt ein Captcha und löst die Rechenaufgabe (z. B. "3 + 4")."""
    data = client.get("/public/captcha").json()["data"]
    a, _, b = data["frage"].partition(" + ")
    return {"captcha": str(int(a) + int(b)), "captcha_token": data["token"]}


def test_public_captcha(client: TestClient) -> None:
    response = client.get("/public/captcha")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert " + " in data["frage"]
    assert data["token"].count(":") == 2


def test_public_anmeldung_unbekannter_anlass(client: TestClient) -> None:
    response = client.post(
        "/public/anmeldung",
        json={
            "anlassid": 99999999,
            "name": "Muster",
            "vorname": "Max",
            "email": "max@example.com",
            **_solve_captcha(client),
        },
    )
    assert response.status_code == 404


def test_public_anmeldung_falsches_captcha(client: TestClient) -> None:
    data = client.get("/public/captcha").json()["data"]
    response = client.post(
        "/public/anmeldung",
        json={
            "anlassid": 1,
            "name": "Muster",
            "vorname": "Max",
            "email": "max@example.com",
            "captcha": "999",
            "captcha_token": data["token"],
        },
    )
    assert response.status_code == 400


def test_public_kontakt_ohne_captcha(client: TestClient) -> None:
    response = client.post(
        "/public/kontakt",
        json={
            "name": "Muster",
            "vorname": "Max",
            "email": "max@example.com",
            "betreff": "Frage",
            "nachricht": "Hallo",
        },
    )
    assert response.status_code == 400


def test_kontakt_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Kontaktanfrage öffentlich erstellen, mit Login auflisten und löschen."""
    created = client.post(
        "/public/kontakt",
        json={
            "name": "PYTEST_KONTAKT",
            "vorname": "Max",
            "email": "pytest@example.com",
            "betreff": "PYTEST Betreff",
            "nachricht": "PYTEST Nachricht",
            **_solve_captcha(client),
        },
    )
    assert created.status_code == 201, created.text

    rows = client.get("/kontakte", headers=auth_headers).json()["data"]
    entry = next((r for r in rows if r["name"] == "PYTEST_KONTAKT"), None)
    assert entry is not None
    assert entry["nachricht"] == "PYTEST Nachricht"

    deleted = client.delete(f"/kontakte/{entry['id']}", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text
    rows = client.get("/kontakte", headers=auth_headers).json()["data"]
    assert all(r["id"] != entry["id"] for r in rows)


def test_public_kontakt_honeypot(client: TestClient) -> None:
    """Honeypot-Feld ausgefüllt → stillschweigend 201, kein Insert/Mail."""
    response = client.post(
        "/public/kontakt",
        json={
            "name": "Bot",
            "vorname": "Spam",
            "email": "bot@example.com",
            "betreff": "Spam",
            "nachricht": "Spam",
            "website": "http://spam.example.com",
        },
    )
    assert response.status_code == 201, response.text


def test_public_kontakt_validierung(client: TestClient) -> None:
    """Fehlende Pflichtfelder → 422."""
    response = client.post(
        "/public/kontakt",
        json={"name": "Muster", "email": "max@example.com"},
    )
    assert response.status_code == 422


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
                **_solve_captcha(client),
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
                **_solve_captcha(client),
            },
        )
        assert doppelt.status_code == 409

        rows = client.get("/anmeldungen", params={"anlassid": anlass_id}, headers=auth_headers).json()["data"]
        assert len(rows) == 1
        assert rows[0]["anlass_longname"].endswith("PYTEST_HOMEPAGE_ANLASS")
        anmeldung_id = rows[0]["id"]

        anmeldbar = client.get("/anlaesse/anmeldbar", headers=auth_headers)
        assert anmeldbar.status_code == 200, anmeldbar.text
        assert any(a["id"] == anlass_id for a in anmeldbar.json()["data"])

        updated = client.patch(f"/anmeldungen/{anmeldung_id}", json={"status": 2}, headers=auth_headers)
        assert updated.status_code == 200
        assert updated.json()["data"]["status"] == 2

        # Status 3 ohne passende Adresse → 400, Status bleibt 2
        rejected = client.patch(f"/anmeldungen/{anmeldung_id}", json={"status": 3}, headers=auth_headers)
        assert rejected.status_code == 400

        # Sammel-Bestätigung: keine neuen Einträge mehr → 0
        confirmed = client.post("/anmeldungen/bestaetigen", params={"anlassid": anlass_id}, headers=auth_headers)
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["data"] == 0

        # Sammel-Anwesend: Adresse fehlt → 0 gebucht, Person in Meldung
        attended = client.post("/anmeldungen/anwesend", params={"anlassid": anlass_id}, headers=auth_headers)
        assert attended.status_code == 200, attended.text
        assert attended.json()["data"] == 0
        assert "Max Muster" in attended.json()["message"]

        # Export der Teilnehmerliste
        exported = client.get("/anmeldungen/export", params={"anlassid": anlass_id}, headers=auth_headers)
        assert exported.status_code == 200, exported.text
        assert exported.json()["data"]["filename"].endswith(".xlsx")
    finally:
        if anmeldung_id is not None:
            client.delete(f"/anmeldungen/{anmeldung_id}", headers=auth_headers)
        deleted = client.delete(f"/anlaesse/{anlass_id}", headers=auth_headers)
        assert deleted.status_code == 200
