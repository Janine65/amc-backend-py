"""Turnstile verification tests without network, database or mail access."""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers import public
from app.utils.turnstile import SITEVERIFY_URL, verify_turnstile


@pytest.fixture(autouse=True)
def turnstile_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_TURNSPIKE_SECRET", "test-secret")
    monkeypatch.setenv("CLOUDFLARE_TURNSPIKE_SITEKEY", "test-site-key")


def _mock_siteverify(monkeypatch: pytest.MonkeyPatch, result: httpx.Response | httpx.HTTPError) -> list[httpx.Request]:
    requests: list[httpx.Request] = []
    original_client = httpx.AsyncClient

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if isinstance(result, httpx.HTTPError):
            raise result
        return result

    monkeypatch.setattr(
        "app.utils.turnstile.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    return requests


@pytest.fixture
def contact_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, AsyncMock, AsyncMock]]:
    db = AsyncMock(spec=AsyncSession)
    mail = AsyncMock()
    monkeypatch.setattr(public, "send_mail", mail)
    monkeypatch.setattr(
        public,
        "get_config",
        lambda: SimpleNamespace(raw={"JanineFranken": {"email_from": "club@example.com"}}),
    )
    app = FastAPI()
    app.include_router(public.router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db, mail


@pytest.mark.parametrize("token", [None, "", "   "])
async def test_missing_token(token: str | None) -> None:
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile(token)
    assert exc.value.status_code == 400


async def test_verification_posts_token_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = _mock_siteverify(monkeypatch, httpx.Response(200, json={"success": True, "action": "kontakt"}))
    await verify_turnstile("test-token")
    assert len(requests) == 1
    assert str(requests[0].url) == SITEVERIFY_URL
    assert requests[0].method == "POST"
    assert parse_qs(requests[0].content.decode()) == {
        "secret": ["test-secret"],
        "response": ["test-token"],
    }


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"success": False, "error-codes": ["invalid-input-response"]}, 400),
        ({"success": False, "error-codes": ["timeout-or-duplicate"]}, 400),
        ({"success": True, "action": "anmeldung"}, 400),
        ({"success": True}, 400),
        ({"success": False, "error-codes": ["invalid-input-secret"]}, 503),
        ({"success": False, "error-codes": ["internal-error"]}, 503),
        ({"success": "true", "action": "kontakt"}, 503),
        ({"success": True, "action": "kontakt", "error-codes": None}, 503),
        ({"success": False, "error-codes": [{}]}, 503),
        ([], 503),
    ],
)
async def test_rejects_unsuccessful_or_malformed_verification(
    monkeypatch: pytest.MonkeyPatch, payload: object, status: int
) -> None:
    _mock_siteverify(monkeypatch, httpx.Response(200, json=payload))
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("test-token")
    assert exc.value.status_code == status


@pytest.mark.parametrize(
    "result",
    [
        httpx.Response(503),
        httpx.Response(200, content=b"not-json"),
        httpx.ReadTimeout("timeout"),
        httpx.ConnectError("unavailable"),
    ],
)
async def test_verification_outage(monkeypatch: pytest.MonkeyPatch, result: httpx.Response | httpx.HTTPError) -> None:
    _mock_siteverify(monkeypatch, result)
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("test-token")
    assert exc.value.status_code == 503


async def test_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_TURNSPIKE_SECRET")
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("test-token")
    assert exc.value.status_code == 503


def test_public_configuration_contains_only_site_key(
    contact_client: tuple[TestClient, AsyncMock, AsyncMock],
) -> None:
    client, _, _ = contact_client
    response = client.get("/public/turnstile")
    assert response.status_code == 200
    assert response.json()["data"] == {"site_key": "test-site-key"}
    assert "test-secret" not in response.text


@pytest.mark.parametrize("name", ["CLOUDFLARE_TURNSPIKE_SECRET", "CLOUDFLARE_TURNSPIKE_SITEKEY"])
def test_public_configuration_unavailable(
    monkeypatch: pytest.MonkeyPatch, contact_client: tuple[TestClient, AsyncMock, AsyncMock], name: str
) -> None:
    monkeypatch.delenv(name)
    client, _, _ = contact_client
    assert client.get("/public/turnstile").status_code == 503


@pytest.mark.parametrize(
    ("token", "verification", "status"),
    [
        (None, {"success": True, "action": "kontakt"}, 400),
        ("", {"success": True, "action": "kontakt"}, 400),
        ("x" * 2049, {"success": True, "action": "kontakt"}, 422),
        ("test-token", {"success": False, "error-codes": ["timeout-or-duplicate"]}, 400),
        ("test-token", {"success": True, "action": "anmeldung"}, 400),
        ("test-token", {"success": False, "error-codes": ["internal-error"]}, 503),
        ("x" * 2048, {"success": True, "action": "kontakt"}, 201),
    ],
)
def test_contact_verifies_before_insert_and_mail(
    monkeypatch: pytest.MonkeyPatch,
    contact_client: tuple[TestClient, AsyncMock, AsyncMock],
    token: str | None,
    verification: dict[str, object],
    status: int,
) -> None:
    client, db, mail = contact_client
    requests = _mock_siteverify(monkeypatch, httpx.Response(200, json=verification))
    response = client.post(
        "/public/kontakt",
        json={
            "name": "Muster",
            "vorname": "Max",
            "email": "max@example.com",
            "betreff": "Frage",
            "nachricht": "Hallo",
            "turnstile_token": token,
            # A correct arithmetic captcha must not bypass Turnstile.
            "captcha": "2",
            "captcha_token": "old-token",
        },
    )
    assert response.status_code == status, response.text
    if status == 201:
        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        mail.assert_awaited_once()
    else:
        db.add.assert_not_called()
        db.flush.assert_not_awaited()
        mail.assert_not_awaited()
    assert len(requests) == (1 if token and len(token) <= 2048 else 0)


def test_contact_honeypot_still_discards(
    monkeypatch: pytest.MonkeyPatch, contact_client: tuple[TestClient, AsyncMock, AsyncMock]
) -> None:
    client, db, mail = contact_client
    requests = _mock_siteverify(monkeypatch, httpx.Response(200, json={"success": True, "action": "kontakt"}))
    response = client.post(
        "/public/kontakt",
        json={
            "name": "Bot",
            "vorname": "Spam",
            "email": "bot@example.com",
            "betreff": "Spam",
            "nachricht": "Spam",
            "website": "https://spam.example.com",
        },
    )
    assert response.status_code == 201
    assert not requests
    db.add.assert_not_called()
    mail.assert_not_awaited()
