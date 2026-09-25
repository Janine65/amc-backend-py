"""Öffentliche Endpunkte für die Homepage (kein Login erforderlich).

Alle Endpunkte sind read-only, ausser der Anlass-Anmeldung. Die
Meisterschafts-Daten werden nur ausgeliefert, wenn das Jahr in
``jahr_freigabe`` freigegeben wurde.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.models.anlaesse import Anlaesse
from app.models.anlass_anmeldung import AnlassAnmeldung
from app.models.bericht import Bericht
from app.models.clubmeister import Clubmeister
from app.models.jahr_freigabe import JahrFreigabe
from app.models.kegelmeister import Kegelmeister
from app.models.news import News
from app.schemas.anlass_anmeldung import AnmeldungPublicCreate
from app.schemas.bericht import BerichtPublic
from app.schemas.news import NewsPublic
from app.schemas.public import AgendaPublic, JahrFreigabePublic, MeisterPublic
from app.schemas.ret_data import RetData
from app.utils.mail import send_mail

logger = get_logger(__name__)

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/news", response_model=RetData[list[NewsPublic]])
async def get_news(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> RetData[list[NewsPublic]]:
    rows = (
        (await db.execute(select(News).where(News.publiziert.is_(True)).order_by(News.datum.desc()).limit(limit)))
        .scalars()
        .all()
    )
    return RetData(data=[NewsPublic.model_validate(r) for r in rows], message="News")


@router.get("/berichte", response_model=RetData[list[BerichtPublic]])
async def get_berichte(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> RetData[list[BerichtPublic]]:
    rows = (
        (
            await db.execute(
                select(Bericht).where(Bericht.publiziert.is_(True)).order_by(Bericht.datum.desc()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[BerichtPublic.model_validate(r) for r in rows], message="Berichte")


@router.get("/agenda", response_model=RetData[list[AgendaPublic]])
async def get_agenda(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[AgendaPublic]]:
    today = datetime.now(UTC).date()
    rows = (
        (
            await db.execute(
                select(Anlaesse)
                .where(
                    and_(
                        Anlaesse.datum >= today,
                        Anlaesse.status == 1,
                        Anlaesse.nachkegeln.is_(False),
                    )
                )
                .order_by(Anlaesse.datum.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[AgendaPublic.model_validate(r) for r in rows], message="Agenda")


@router.post("/anmeldung", response_model=RetData[None], status_code=201)
@limiter.limit("5/minute")
async def create_anmeldung(
    request: Request,
    body: AnmeldungPublicCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[None]:
    # Honeypot ausgefüllt → Bot; stillschweigend "Erfolg" melden
    if body.website:
        logger.warning("Anmeldung honeypot triggered from %s", request.client.host if request.client else "?")
        return RetData(data=None, message="Anmeldung erhalten")

    anlass = await db.get(Anlaesse, body.anlassid)
    today = datetime.now(UTC).date()
    if anlass is None or anlass.status != 1 or anlass.datum < today:
        raise HTTPException(status_code=404, detail="Anlass nicht gefunden oder bereits vorbei.")
    if anlass.istkegeln:
        raise HTTPException(status_code=400, detail="Für Kegel-Anlässe ist keine Anmeldung nötig.")
    if anlass.istmotorrad:
        raise HTTPException(status_code=400, detail="Für Motorrad-Anlässe ist keine Anmeldung nötig.")

    existing = await db.scalar(
        select(AnlassAnmeldung).where(
            and_(
                AnlassAnmeldung.anlassid == body.anlassid,
                AnlassAnmeldung.email == str(body.email).lower(),
            )
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Für diese E-Mail-Adresse existiert bereits eine Anmeldung.")

    now = datetime.now(UTC)
    db.add(
        AnlassAnmeldung(
            anlassid=body.anlassid,
            name=body.name.strip(),
            vorname=body.vorname.strip(),
            email=str(body.email).lower(),
            bemerkung=body.bemerkung,
            status=1,
            createdAt=now,
            updatedAt=now,
        )
    )
    await db.flush()

    # Mail senden an default Signatur
    cfg = get_config()
    signature = cfg.raw.get("defaultEmail", "JanineFranken")
    smtp_cfg = (cfg.raw or {}).get(signature)

    message = f"<p>{body.vorname} {body.name} hat sich für den Anlass {anlass.name} am {anlass.datum} angemeldet.</p>"
    await send_mail(
        subject="Neue Anmeldung",
        to=smtp_cfg.get("smtp_user", "janine@automoto-sr.info") if smtp_cfg else "janine@automoto-sr.info",
        sender_signature=signature,
        html=message,
    )
    return RetData(data=None, message="Anmeldung erhalten")


@router.get("/jahre", response_model=RetData[list[JahrFreigabePublic]])
async def get_jahre(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[JahrFreigabePublic]]:
    rows = (
        (
            await db.execute(
                select(JahrFreigabe)
                .where(or_(JahrFreigabe.clubmeister.is_(True), JahrFreigabe.kegelmeister.is_(True)))
                .order_by(JahrFreigabe.jahr.desc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[JahrFreigabePublic.model_validate(r) for r in rows], message="Freigegebene Jahre")


async def _check_freigabe(db: AsyncSession, jahr: str, art: str) -> None:
    freigabe = await db.scalar(select(JahrFreigabe).where(JahrFreigabe.jahr == jahr))
    if freigabe is None or not getattr(freigabe, art):
        raise HTTPException(status_code=404, detail="Dieses Jahr ist nicht freigegeben.")


def _to_public(row: Clubmeister | Kegelmeister) -> MeisterPublic:
    """Nachname aus Datenschutzgründen auf den ersten Buchstaben kürzen."""
    return MeisterPublic(
        rang=row.rang,
        vorname=row.vorname,
        nachname=f"{row.nachname[0]}." if row.nachname else None,
        punkte=row.punkte,
        anlaesse=row.anlaesse,
    )


@router.get("/clubmeister", response_model=RetData[list[MeisterPublic]])
async def get_clubmeister(jahr: str, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[MeisterPublic]]:
    await _check_freigabe(db, jahr, "clubmeister")
    rows = (
        (
            await db.execute(
                select(Clubmeister)
                .where(and_(Clubmeister.jahr == jahr, Clubmeister.status.is_(True)))
                .order_by(Clubmeister.rang.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[_to_public(r) for r in rows], message="Clubmeisterschaft")


@router.get("/kegelmeister", response_model=RetData[list[MeisterPublic]])
async def get_kegelmeister(jahr: str, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[MeisterPublic]]:
    await _check_freigabe(db, jahr, "kegelmeister")
    rows = (
        (
            await db.execute(
                select(Kegelmeister)
                .where(and_(Kegelmeister.jahr == jahr, Kegelmeister.status.is_(True)))
                .order_by(Kegelmeister.rang.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[_to_public(r) for r in rows], message="Kegelmeisterschaft")
