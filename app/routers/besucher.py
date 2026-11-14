"""Erfassung nur durch die Homepage; aggregierte Auswertung nur mit Login."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import Integer, case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import get_db
from app.core.ratelimit import limiter
from app.dependencies import CurrentUser
from app.models.besucher import BesucherSeite, BesucherSitzung
from app.schemas.besucher import BesucherAktivitaet, BesucherAufruf, BesucherGruppe, BesucherStatistik
from app.schemas.ret_data import RetData
from app.utils.besucher import (
    BOT_RE,
    RETENTION_DAYS,
    SESSION_TIMEOUT,
    agent_details,
    country_for_ip,
    normalized_path,
    referrer_details,
)

router = APIRouter(prefix="/besucher", tags=["Besucher"])


def require_homepage(x_analytics_key: Annotated[str | None, Header()] = None) -> None:
    key = os.environ.get("ANALYTICS_SECRET", "")
    if len(key) < 32:
        raise HTTPException(status_code=503, detail="Besucherstatistik ist nicht konfiguriert")
    if not x_analytics_key or not secrets.compare_digest(x_analytics_key.encode(), key.encode()):
        raise HTTPException(status_code=403, detail="Nur fuer die Homepage freigegeben")


@router.post("/aufruf", response_model=RetData[None], dependencies=[Depends(require_homepage)])
@limiter.limit("120/minute")
async def record_page(
    request: Request,
    body: BesucherAufruf,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[None]:
    if BOT_RE.search(body.user_agent):
        raise HTTPException(status_code=422, detail="Bots werden nicht erfasst")
    try:
        path = normalized_path(body.path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = datetime.now(UTC)
    source, host = referrer_details(body.referrer)
    device, browser = agent_details(body.user_agent)
    await db.execute(
        insert(BesucherSitzung)
        .values(
            id=body.session_id,
            started_at=now,
            last_seen_at=now,
            duration_observed=False,
            country=country_for_ip(body.client_ip),
            source=source,
            referrer_host=host,
            entry_path=path,
            device=device,
            browser=browser,
        )
        .on_conflict_do_nothing(index_elements=[BesucherSitzung.id])
    )
    session = await db.scalar(select(BesucherSitzung).where(BesucherSitzung.id == body.session_id).with_for_update())
    if session is None:
        raise RuntimeError("Besuchersitzung konnte nicht angelegt werden")
    if session.last_seen_at < now - SESSION_TIMEOUT or session.started_at < now - timedelta(days=RETENTION_DAYS):
        raise HTTPException(status_code=409, detail="Besuchersitzung abgelaufen")
    page = await db.get(BesucherSeite, body.page_id)
    if page is not None:
        if page.session_id != body.session_id or page.path != path:
            raise HTTPException(status_code=409, detail="Seitenaufruf gehoert zu einer anderen Sitzung")
        return RetData(data=None, message="Seitenaufruf bereits erfasst")
    db.add(BesucherSeite(id=body.page_id, session_id=body.session_id, path=path, created_at=now))
    if now > session.started_at:
        session.duration_observed = True
    session.last_seen_at = max(session.last_seen_at, now)
    await db.flush()
    return RetData(data=None, message="Seitenaufruf erfasst")


@router.post("/aktivitaet", response_model=RetData[None], dependencies=[Depends(require_homepage)])
@limiter.limit("120/minute")
async def record_activity(
    request: Request,
    body: BesucherAktivitaet,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[None]:
    now = datetime.now(UTC)
    page_exists = (
        select(BesucherSeite.id)
        .where(BesucherSeite.id == body.page_id, BesucherSeite.session_id == body.session_id)
        .exists()
    )
    result = await db.scalar(
        update(BesucherSitzung)
        .where(
            BesucherSitzung.id == body.session_id,
            BesucherSitzung.last_seen_at >= now - SESSION_TIMEOUT,
            BesucherSitzung.started_at >= now - timedelta(days=RETENTION_DAYS),
            page_exists,
        )
        .values(last_seen_at=func.greatest(BesucherSitzung.last_seen_at, now), duration_observed=True)
        .returning(BesucherSitzung.id)
    )
    if result is None:
        raise HTTPException(status_code=410, detail="Besuchersitzung abgelaufen oder nicht gefunden")
    return RetData(data=None, message="Aktivitaet erfasst")


@router.get("/statistik", response_model=RetData[BesucherStatistik])
async def statistics(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    von: date | None = None,
    bis: date | None = None,
) -> RetData[BesucherStatistik]:
    if user.role not in {"admin", "user"}:
        raise HTTPException(status_code=403, detail="Keine Berechtigung fuer Besucherstatistik")
    now = datetime.now(UTC)
    zone = ZoneInfo("Europe/Zurich")
    today = now.astimezone(zone).date()
    end_date = bis or today
    start_date = von or end_date - timedelta(days=29)
    if end_date > today or start_date < today - timedelta(days=RETENTION_DAYS):
        raise HTTPException(status_code=422, detail="Nur Zeitraeume innerhalb der vergangenen 365 Tage sind verfuegbar")
    if start_date > end_date or (end_date - start_date).days >= RETENTION_DAYS:
        raise HTTPException(status_code=422, detail="Zeitraum muss 1 bis 365 Tage umfassen")
    start = datetime.combine(start_date, time.min, zone).astimezone(UTC)
    end = datetime.combine(end_date + timedelta(days=1), time.min, zone).astimezone(UTC)
    filters = (
        BesucherSitzung.started_at >= max(start, now - timedelta(days=RETENTION_DAYS)),
        BesucherSitzung.started_at < end,
    )
    duration = func.extract("epoch", BesucherSitzung.last_seen_at - BesucherSitzung.started_at)
    totals = (
        await db.execute(
            select(
                func.count(BesucherSitzung.id),
                func.count(BesucherSitzung.id).filter(BesucherSitzung.duration_observed),
                func.avg(duration).filter(BesucherSitzung.duration_observed),
            ).where(*filters)
        )
    ).one()

    async def groups(expression: ColumnElement | InstrumentedAttribute, *, pages: bool = False) -> list[BesucherGruppe]:
        query = select(expression.label("label"), func.count().label("count"))
        if pages:
            query = (
                query.select_from(BesucherSeite)
                .join(BesucherSitzung, BesucherSitzung.id == BesucherSeite.session_id)
                .where(BesucherSeite.created_at < end)
            )
        else:
            query = query.select_from(BesucherSitzung)
        rows = (
            await db.execute(query.where(*filters).group_by(expression).order_by(func.count().desc(), expression))
        ).all()
        return [BesucherGruppe(label=str(label), count=count) for label, count in rows]

    local_start = func.timezone("Europe/Zurich", BesucherSitzung.started_at)
    weekdays = await groups(func.extract("isodow", local_start).cast(Integer))
    hours = await groups(func.extract("hour", local_start).cast(Integer))
    weekday_counts = {int(row.label): row.count for row in weekdays}
    hour_counts = {int(row.label): row.count for row in hours}
    duration_bucket = case(
        (~BesucherSitzung.duration_observed, "Nicht messbar"),
        (duration < 10, "< 10 Sekunden"),
        (duration < 60, "10–59 Sekunden"),
        (duration < 300, "1–4 Minuten"),
        (duration < 900, "5–14 Minuten"),
        else_="Ab 15 Minuten",
    )
    page_groups = await groups(BesucherSeite.path, pages=True)
    data = BesucherStatistik(
        von=start_date,
        bis=end_date,
        visits=totals[0],
        measured_visits=totals[1],
        average_duration_seconds=float(totals[2]) if totals[2] is not None else None,
        pageviews=sum(row.count for row in page_groups),
        countries=await groups(func.coalesce(BesucherSitzung.country, "Unbekannt")),
        sources=await groups(
            case(
                (BesucherSitzung.source == "direct", "Direkt / unbekannt"),
                (BesucherSitzung.source == "search", "Suchmaschine"),
                (BesucherSitzung.source == "link", "Externer Link"),
                else_="Unbekannt",
            )
        ),
        referrers=await groups(func.coalesce(BesucherSitzung.referrer_host, "Ohne Referrer")),
        weekdays=[
            BesucherGruppe(label=label, count=weekday_counts.get(i, 0))
            for i, label in enumerate(
                ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], 1
            )
        ],
        hours=[BesucherGruppe(label=f"{i:02d}:00", count=hour_counts.get(i, 0)) for i in range(24)],
        days=sorted(await groups(func.to_char(local_start, "YYYY-MM-DD")), key=lambda row: row.label),
        durations=await groups(duration_bucket),
        pages=page_groups,
        entry_pages=await groups(BesucherSitzung.entry_path),
        devices=await groups(
            case(
                (BesucherSitzung.device == "mobile", "Mobil"),
                (BesucherSitzung.device == "tablet", "Tablet"),
                else_="Desktop",
            )
        ),
        browsers=await groups(BesucherSitzung.browser),
    )
    return RetData(data=data, message="Besucherstatistik")
