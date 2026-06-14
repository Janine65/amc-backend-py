"""``meisterschaft`` router."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.adressen import Adressen
from app.models.anlaesse import Anlaesse
from app.models.clubmeister import Clubmeister
from app.models.kegelmeister import Kegelmeister
from app.models.meisterschaft import Meisterschaft
from app.schemas.meisterschaft import (
    MeisterEntity,
    MeisterschaftCreate,
    MeisterschaftEntity,
    MeisterschaftUpdate,
)
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/meisterschaft", tags=["Meisterschaft"])


@router.get("/listevent", response_model=RetData[list[MeisterschaftEntity]])
async def list_event(
    eventid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[MeisterschaftEntity]]:
    rows = (
        (
            await db.execute(
                select(Meisterschaft)
                .where(Meisterschaft.eventid == eventid)
                .join(Adressen, Adressen.id == Meisterschaft.mitgliedid)
                .order_by(Adressen.fullname.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(
        data=[MeisterschaftEntity.model_validate(r) for r in rows],
        message="Liste der Meisterschaften für Event",
    )


@router.get("/listmitglied", response_model=RetData[list[MeisterschaftEntity]])
async def list_mitglied(
    mitgliedid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[MeisterschaftEntity]]:
    rows = (
        (
            await db.execute(
                select(Meisterschaft)
                .where(Meisterschaft.mitgliedid == mitgliedid)
                .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
                .order_by(Anlaesse.datum.desc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(
        data=[MeisterschaftEntity.model_validate(r) for r in rows],
        message="Liste der Meisterschaften für Mitglied",
    )


@router.get("/listmitgliedmeister", response_model=RetData[list[MeisterEntity]])
async def list_mitglied_meister(
    mitgliedid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[MeisterEntity]]:
    adresse = await db.scalar(
        select(Adressen)
        .where(Adressen.id == mitgliedid)
        .options(
            selectinload(Adressen.clubmeister),
            selectinload(Adressen.kegelmeister),
        )
    )
    if adresse is None:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
    cm_first = (
        (await db.execute(select(Clubmeister).where(Clubmeister.rang == 1).order_by(Clubmeister.jahr.desc())))
        .scalars()
        .all()
    )
    km_first = (
        (await db.execute(select(Kegelmeister).where(Kegelmeister.rang == 1).order_by(Kegelmeister.jahr.desc())))
        .scalars()
        .all()
    )

    al: list[MeisterEntity] = []
    for cm in sorted(adresse.clubmeister, key=lambda c: c.jahr, reverse=True):
        diff = None
        first = next((c for c in cm_first if c.jahr == cm.jahr), None)
        if first:
            diff = (first.punkte or 0) - (cm.punkte or 0)
        al.append(
            MeisterEntity(
                jahr=cm.jahr,
                rang=cm.rang,
                vorname=cm.vorname,
                nachname=cm.nachname,
                mitgliedid=cm.mitgliedid,
                clubpunkte=cm.punkte,
                anlaesse=cm.anlaesse,
                werbungen=cm.werbungen,
                mitglieddauer=cm.mitglieddauer,
                diff_first=diff,
            )
        )
    for km in sorted(adresse.kegelmeister, key=lambda k: k.jahr, reverse=True):
        existing = next((m for m in al if m.jahr == km.jahr), None)
        diff = None
        first = next((k for k in km_first if k.jahr == km.jahr), None)
        if first:
            diff = (first.punkte or 0) - (km.punkte or 0)
        if existing is None:
            al.append(
                MeisterEntity(
                    jahr=km.jahr,
                    rang=km.rang,
                    vorname=km.vorname,
                    nachname=km.nachname,
                    mitgliedid=km.mitgliedid,
                    kegelpunkte=km.punkte,
                    anlaesse=km.anlaesse,
                    babeli=km.babeli,
                    diff_first=diff,
                )
            )
        else:
            existing.kegelpunkte = km.punkte
            existing.babeli = km.babeli
            if diff is not None and existing.diff_first is None:
                existing.diff_first = diff

    return RetData(data=al, message="Liste der Meisterschaften für Mitglied")


@router.get("/checkjahr", response_model=RetData[int])
async def check_jahr(jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[int]:
    start = date(int(jahr), 1, 1)
    end = date(int(jahr), 12, 31)
    cnt = await db.scalar(
        select(func.count(Meisterschaft.id))
        .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
        .where(
            and_(
                Meisterschaft.streichresultat.is_(True),
                Anlaesse.datum >= start,
                Anlaesse.datum <= end,
            )
        )
    )
    return RetData(data=int(cnt or 0), message="Jahr geprüft")


@router.get("/getchartdata", response_model=RetData[list[dict]])
async def get_chart_data(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[dict]]:
    start = date(int(jahr), 1, 1)
    end = date(int(jahr), 12, 31)
    rows = (
        (
            await db.execute(
                select(Anlaesse)
                .where(and_(Anlaesse.datum >= start, Anlaesse.datum <= end))
                .order_by(Anlaesse.datum.asc())
            )
        )
        .scalars()
        .all()
    )
    out: list[dict] = []
    for anl in rows:
        cnt = await db.scalar(select(func.count(Meisterschaft.id)).where(Meisterschaft.eventid == anl.id))
        out.append(
            {
                "id": anl.id,
                "datum": anl.datum.isoformat(),
                "name": anl.name,
                "longname": anl.longname,
                "_count": {"meisterschaft": int(cnt or 0)},
            }
        )
    return RetData(data=out, message="Chartdaten")


@router.post("", response_model=RetData[MeisterschaftEntity], status_code=201)
async def create(
    body: MeisterschaftCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[MeisterschaftEntity]:
    now = datetime.now(UTC)
    obj = Meisterschaft(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["anlaesse", "adressen"])
    return RetData(data=MeisterschaftEntity.model_validate(obj), message="create")


@router.get("", response_model=RetData[list[MeisterschaftEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[MeisterschaftEntity]]:
    params = await load_params()
    clubjahr = params.get("CLUBJAHR", "1900")
    start = date(int(clubjahr), 1, 1)
    rows = (
        (
            await db.execute(
                select(Meisterschaft)
                .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
                .where(Anlaesse.datum >= start)
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[MeisterschaftEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{m_id}", response_model=RetData[MeisterschaftEntity])
async def find_one(
    m_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[MeisterschaftEntity]:
    obj = await db.get(Meisterschaft, m_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=MeisterschaftEntity.model_validate(obj), message="findOne")


@router.patch("/{m_id}", response_model=RetData[MeisterschaftEntity])
async def update(
    m_id: int,
    body: MeisterschaftUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[MeisterschaftEntity]:
    obj = await db.get(Meisterschaft, m_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Meisterschaft nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["anlaesse", "adressen"])
    return RetData(data=MeisterschaftEntity.model_validate(obj), message="findOne")


@router.delete("/{m_id}", response_model=RetData[MeisterschaftEntity])
async def remove(
    m_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[MeisterschaftEntity]:
    obj = await db.get(Meisterschaft, m_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Meisterschaft nicht gefunden")
    await db.refresh(obj, ["anlaesse", "adressen"])
    entity = MeisterschaftEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="findOne")
