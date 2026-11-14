"""Statistiktests verwenden ausschliesslich ein eigenes temporaeres PostgreSQL-Schema."""

import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import get_config
from app.core.database import _split_schema
from app.models.besucher import BesucherSeite, BesucherSitzung
from app.routers import besucher as router
from app.schemas.besucher import BesucherAktivitaet, BesucherAufruf
from app.utils import besucher as utils


@pytest.fixture
async def db():
    url, _ = _split_schema(get_config().database_url)
    schema = "test_besucher_" + uuid4().hex
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    async with engine.begin() as connection:
        await connection.execute(CreateSchema(schema))
        await connection.run_sync(BesucherSitzung.__table__.create)
        await connection.run_sync(BesucherSeite.__table__.create)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        async with engine.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True))
        await engine.dispose()


def freeze_now(monkeypatch, now):
    clock = Mock(wraps=datetime)
    clock.now.return_value = now
    monkeypatch.setattr(router, "datetime", clock)


@pytest.mark.parametrize(
    ("url", "source", "host"),
    [
        (None, "direct", None),
        ("https://www.google.ch/search?q=private", "search", "www.google.ch"),
        ("https://duckduckgo.com/?q=private", "search", "duckduckgo.com"),
        ("https://google.com.evil.example/?token=private", "link", "google.com.evil.example"),
        ("https://example.org/private?token=private#name", "link", "example.org"),
        ("https://8.8.8.8/private", "link", None),
        ("javascript:alert(1)", "unknown", None),
    ],
)
def test_referrer_does_not_store_sensitive_url_parts(url, source, host):
    assert utils.referrer_details(url) == (source, host)


def test_coarse_paths_agents_and_local_geoip(monkeypatch):
    assert utils.normalized_path("/anmeldung/123/") == "/anmeldung/:id"
    with pytest.raises(ValueError):
        utils.normalized_path("/kontakt?email=private")
    assert utils.agent_details("Mozilla/5.0 (iPhone) CriOS/120 Safari/600") == ("mobile", "Chrome")
    assert utils.agent_details("Mozilla/5.0 (iPad) Safari/600") == ("tablet", "Safari")
    geoip = Mock()
    geoip.get.return_value = {"country": {"iso_code": "CH"}}
    monkeypatch.setattr(utils, "_geoip", geoip)
    assert utils.country_for_ip("8.8.8.8") == "CH"
    assert utils.country_for_ip("192.168.1.1") is None
    assert utils.country_for_ip("invalid") is None
    geoip.get.assert_called_once_with("8.8.8.8")


def test_geoip_startup_reports_loaded_database_and_rejects_asn(monkeypatch, caplog):
    reader = Mock()
    reader.metadata.return_value.database_type = "GeoLite2-Country"
    monkeypatch.setenv("GEOIP_COUNTRY_DB", "/geoip/country.mmdb")
    monkeypatch.setattr(utils.maxminddb, "open_database", Mock(return_value=reader))
    monkeypatch.setattr(utils, "_geoip", None)
    with caplog.at_level(logging.INFO, logger=utils.__name__):
        utils.open_geoip()
    assert utils._geoip is reader
    assert "GeoIP-Laenderdatenbank geladen" in caplog.text
    utils.close_geoip()
    reader.close.assert_called_once()
    reader.reset_mock()
    reader.metadata.return_value.database_type = "GeoLite2-ASN"
    with pytest.raises(RuntimeError, match="GeoLite2-ASN"):
        utils.open_geoip()
    reader.close.assert_called_once()
    assert utils._geoip is None


def test_geoip_logs_private_addresses_once_without_disclosing_them(monkeypatch, caplog):
    reader = Mock()
    monkeypatch.setattr(utils, "_geoip", reader)
    monkeypatch.setattr(utils, "_geoip_notices", set())
    with caplog.at_level(logging.INFO, logger=utils.__name__):
        assert utils.country_for_ip("127.0.0.1") is None
        assert utils.country_for_ip("192.168.1.1") is None
    assert caplog.text.count("lokale/private") == 1
    assert "127.0.0.1" not in caplog.text and "192.168.1.1" not in caplog.text
    reader.get.assert_not_called()


def test_collection_requires_shared_secret(monkeypatch):
    monkeypatch.delenv("ANALYTICS_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        router.require_homepage("wrong")
    assert exc.value.status_code == 503
    monkeypatch.setenv("ANALYTICS_SECRET", "a" * 32)
    with pytest.raises(HTTPException) as exc:
        router.require_homepage("wrong")
    assert exc.value.status_code == 403
    router.require_homepage("a" * 32)


async def test_page_idempotency_activity_and_expiry(db, monkeypatch):
    now = datetime.now(UTC)
    freeze_now(monkeypatch, now)
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
    session_id, page_id = uuid4(), uuid4()
    body = BesucherAufruf(
        session_id=session_id,
        page_id=page_id,
        path="/news",
        referrer="https://bing.com/search?q=private",
        user_agent="Mozilla Firefox/120",
    )
    await router.record_page(request=request, body=body, db=db)
    await router.record_page(request=request, body=body, db=db)
    assert await db.scalar(select(func.count()).select_from(BesucherSeite)) == 1
    session = await db.get(BesucherSitzung, session_id)
    assert session is not None and session.duration_observed is False
    freeze_now(monkeypatch, now + timedelta(seconds=45))
    await router.record_activity(
        request=request,
        body=BesucherAktivitaet(session_id=session_id, page_id=page_id),
        db=db,
    )
    await db.refresh(session)
    assert session.duration_observed is True
    assert (session.last_seen_at - session.started_at).total_seconds() == 45
    await router.record_page(
        request=request,
        body=body.model_copy(update={"page_id": uuid4(), "path": "/kontakt", "referrer": None}),
        db=db,
    )
    assert session.source == "search" and session.referrer_host == "bing.com"
    assert session.entry_path == "/news"
    with pytest.raises(HTTPException) as exc:
        await router.record_activity(
            request=request,
            body=BesucherAktivitaet(session_id=session_id, page_id=uuid4()),
            db=db,
        )
    assert exc.value.status_code == 410
    freeze_now(monkeypatch, now + timedelta(minutes=31))
    with pytest.raises(HTTPException) as exc:
        await router.record_page(request=request, body=body, db=db)
    assert exc.value.status_code == 409


async def test_statistics_zurich_boundaries_unknown_duration_and_retention(db, monkeypatch):
    now = datetime(2026, 11, 14, 12, tzinfo=UTC)
    freeze_now(monkeypatch, now)
    started = datetime(2026, 11, 13, 23, 30, tzinfo=UTC)
    measured_id, unknown_id, old_id = uuid4(), uuid4(), uuid4()
    for id_, start, measured, country in [
        (measured_id, started, True, "CH"),
        (unknown_id, started + timedelta(hours=1), False, None),
        (old_id, now - timedelta(days=366), True, "DE"),
    ]:
        db.add(
            BesucherSitzung(
                id=id_,
                started_at=start,
                last_seen_at=start + timedelta(seconds=90) if measured else start,
                duration_observed=measured,
                country=country,
                source="search" if measured else "direct",
                referrer_host="bing.com" if measured else None,
                entry_path="/news",
                device="mobile",
                browser="Firefox",
            )
        )
    await db.flush()
    for id_ in [measured_id, unknown_id, old_id]:
        db.add(BesucherSeite(id=uuid4(), session_id=id_, path="/news", created_at=started))
    await db.flush()
    result = await router.statistics(
        user=SimpleNamespace(role="user"),
        db=db,
        von=now.date(),
        bis=now.date(),
    )
    data = result.data
    assert data is not None
    assert (data.visits, data.pageviews, data.measured_visits, data.average_duration_seconds) == (2, 2, 1, 90)
    assert {row.label: row.count for row in data.countries} == {"CH": 1, "Unbekannt": 1}
    assert {row.label: row.count for row in data.durations} == {"1–4 Minuten": 1, "Nicht messbar": 1}
    assert len(data.weekdays) == 7 and data.weekdays[5].count == 2
    assert len(data.hours) == 24 and data.hours[0].count == data.hours[1].count == 1
    assert data.days[0].label == "2026-11-14" and data.days[0].count == 2
    await utils.purge_visits(db, now)
    assert await db.get(BesucherSitzung, old_id, populate_existing=True) is None
    assert await db.scalar(select(func.count()).select_from(BesucherSeite)) == 2
    with pytest.raises(HTTPException) as exc:
        await router.statistics(user=SimpleNamespace(role="revisor"), db=db)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        await router.statistics(
            user=SimpleNamespace(role="user"),
            db=db,
            von=now.date(),
            bis=now.date() - timedelta(days=1),
        )
    assert exc.value.status_code == 422


async def test_duration_bucket_boundaries(db, monkeypatch):
    now = datetime(2026, 11, 14, 12, tzinfo=UTC)
    freeze_now(monkeypatch, now)
    for seconds in [0, 9, 10, 59, 60, 299, 300, 899, 900]:
        db.add(
            BesucherSitzung(
                id=uuid4(),
                started_at=now - timedelta(hours=1),
                last_seen_at=now - timedelta(hours=1) + timedelta(seconds=seconds),
                duration_observed=True,
                country=None,
                source="direct",
                referrer_host=None,
                entry_path="/",
                device="desktop",
                browser="Safari",
            )
        )
    await db.flush()
    result = await router.statistics(user=SimpleNamespace(role="user"), db=db, von=now.date(), bis=now.date())
    assert result.data is not None
    assert {row.label: row.count for row in result.data.durations} == {
        "< 10 Sekunden": 2,
        "10–59 Sekunden": 2,
        "1–4 Minuten": 2,
        "5–14 Minuten": 2,
        "Ab 15 Minuten": 1,
    }
