"""Nur grobe Merkmale speichern; URLs, IPs und User-Agents bleiben fluechtig."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import maxminddb
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.besucher import BesucherSitzung

logger = get_logger(__name__)
_geoip: maxminddb.Reader | None = None
_geoip_notices: set[str] = set()
RETENTION_DAYS = 365
SESSION_TIMEOUT = timedelta(minutes=30)
BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|healthcheck|^node$|^$", re.I)
_PATH_RE = re.compile(r"^/(?:news|berichte|agenda|meisterschaft|kontakt|datenschutz)?/?$")


def normalized_path(path: str) -> str:
    if _PATH_RE.fullmatch(path):
        return path.rstrip("/") or "/"
    if re.fullmatch(r"/anmeldung/\d+/?", path):
        return "/anmeldung/:id"
    raise ValueError("Nicht unterstuetzter Seitenpfad")


def referrer_details(referrer: str | None) -> tuple[str, str | None]:
    if not referrer:
        return "direct", None
    try:
        parsed = urlsplit(referrer)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not host:
            raise ValueError("Invalid referrer")
        host = host.encode("idna").decode("ascii").lower().rstrip(".")
        if len(host) > 253:
            raise ValueError("Invalid hostname")
    except (ValueError, UnicodeError):
        logger.warning("Ungueltiger Statistik-Referrer verworfen")
        return "unknown", None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return "link", None
    # Keine Suchbegriffe, URL-Pfade, Zugangstokens oder Query-Parameter speichern.
    search = re.fullmatch(r"(?:www\.)?google\.(?:[a-z]{2,3}|co\.[a-z]{2}|com\.[a-z]{2})", host) or any(
        host == domain or host.endswith("." + domain)
        for domain in (
            "bing.com",
            "duckduckgo.com",
            "search.yahoo.com",
            "ecosia.org",
            "search.brave.com",
            "yandex.com",
            "baidu.com",
        )
    )
    return ("search" if search else "link"), host


def agent_details(agent: str) -> tuple[str, str]:
    device = (
        "tablet"
        if re.search(r"ipad|tablet|android(?!.*mobile)", agent, re.I)
        else ("mobile" if re.search(r"mobile|iphone|ipod", agent, re.I) else "desktop")
    )
    for pattern, browser in (
        (r"Edg(?:e|A|iOS)?/", "Edge"),
        (r"OPR/|Opera", "Opera"),
        (r"Firefox/|FxiOS/", "Firefox"),
        (r"Chrome/|CriOS/", "Chrome"),
        (r"Safari/", "Safari"),
    ):
        if re.search(pattern, agent):
            return device, browser
    return device, "Unbekannt"


def open_geoip() -> None:
    global _geoip
    _geoip_notices.clear()
    path = os.environ.get("GEOIP_COUNTRY_DB")
    if path:
        reader = maxminddb.open_database(path)
        database_type = reader.metadata().database_type
        if not database_type.endswith("-Country"):
            reader.close()
            raise RuntimeError(
                f"GEOIP_COUNTRY_DB verweist auf {database_type}; eine GeoIP-/GeoLite2-Country-MMDB ist erforderlich."
            )
        _geoip = reader
        logger.info("GeoIP-Laenderdatenbank geladen: %s (%s)", path, database_type)
    else:
        logger.warning("GEOIP_COUNTRY_DB fehlt: Besucherland wird als unbekannt erfasst")


def close_geoip() -> None:
    global _geoip
    if _geoip is not None:
        _geoip.close()
        _geoip = None
    _geoip_notices.clear()


def _geoip_notice(message: str) -> None:
    if message not in _geoip_notices:
        _geoip_notices.add(message)
        logger.info(message)


def country_for_ip(value: str | None) -> str | None:
    if _geoip is None:
        _geoip_notice("GeoIP: keine Laenderdatenbank geladen; Besucherland bleibt unbekannt.")
        return None
    if not value:
        _geoip_notice("GeoIP: keine Besucher-IP uebermittelt; Besucherland bleibt unbekannt.")
        return None
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        logger.warning("Ungueltige Statistik-IP verworfen")
        return None
    if not address.is_global:
        _geoip_notice(
            "GeoIP: lokale/private oder andere nichtoeffentliche Besucher-IP; kein Land bestimmbar. "
            "Bei localhost-/Docker-Zugriffen ist dies erwartbar. Fuer externe Besucher die IP-Weitergabe pruefen."
        )
        return None
    result = _geoip.get(str(address))
    if not isinstance(result, dict):
        _geoip_notice("GeoIP: oeffentliche Besucher-IP ist nicht in der Datenbank enthalten; Land bleibt unbekannt.")
        return None
    country = result.get("country")
    if not isinstance(country, dict):
        _geoip_notice("GeoIP: Datensatz enthaelt keine geografische Laenderzuordnung; Land bleibt unbekannt.")
        return None
    code = country.get("iso_code")
    if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code):
        _geoip_notice("GeoIP: Datensatz enthaelt keinen gueltigen Laendercode; Land bleibt unbekannt.")
        return None
    return code


async def purge_visits(db: AsyncSession, now: datetime) -> None:
    await db.execute(delete(BesucherSitzung).where(BesucherSitzung.started_at < now - timedelta(days=RETENTION_DAYS)))


async def retention_worker() -> None:
    while True:
        try:
            async with async_session_maker() as db:
                await purge_visits(db, datetime.now(UTC))
                await db.commit()
        except Exception:
            logger.exception("Loeschen abgelaufener Besuchsdaten fehlgeschlagen; erneuter Versuch in einer Stunde")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(86400)
