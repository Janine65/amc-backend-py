"""``clubmeister`` router (port of NestJS ``ClubmeisterService``)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config, load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.adressen import Adressen
from app.models.anlaesse import Anlaesse
from app.models.clubmeister import Clubmeister
from app.models.meisterschaft import Meisterschaft
from app.schemas.clubmeister import ClubmeisterCreate, ClubmeisterEntity, ClubmeisterUpdate
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/clubmeister", tags=["Clubmeister"])


@router.get("/byjahr", response_model=RetData[list[ClubmeisterEntity]])
async def find_all_by_jahr(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[ClubmeisterEntity]]:
    rows = (
        (
            await db.execute(
                select(Clubmeister)
                .where(Clubmeister.jahr == jahr)
                .order_by(Clubmeister.jahr.asc(), Clubmeister.rang.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[ClubmeisterEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/overview", response_model=RetData[list[dict]])
async def overview(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[dict]]:
    params = await load_params()
    year = params.get("CLUBJAHR", "")
    count = await db.scalar(select(func.count(Clubmeister.id)).where(Clubmeister.jahr == year))
    return RetData(
        data=[{"label": "Clubmeisterschaft", "value": int(count or 0)}],
        message="Übersicht Clubmeister",
    )


@router.get("/calcMeister", response_model=RetData[list[ClubmeisterCreate]])
async def calc_meister(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[ClubmeisterCreate]]:
    """Recalculate club meister ranking (port of ``calcMeister``)."""
    start = date(int(jahr), 1, 1)
    end = date(int(jahr), 12, 31)

    # Adressen with at least one Meisterschaft entry that year (punkte >= 0)
    adresses = (
        (
            await db.execute(
                select(Adressen)
                .join(Meisterschaft, Meisterschaft.mitgliedid == Adressen.id)
                .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
                .where(
                    and_(
                        Anlaesse.datum >= start,
                        Anlaesse.datum <= end,
                        Anlaesse.punkte >= 0,
                    )
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )

    await db.execute(delete(Clubmeister).where(Clubmeister.jahr == jahr))

    rec_list: list[ClubmeisterCreate] = []
    for adr in adresses:
        meister_rows = (
            (
                await db.execute(
                    select(Meisterschaft)
                    .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
                    .where(
                        and_(
                            Meisterschaft.mitgliedid == adr.id,
                            Anlaesse.datum >= start,
                            Anlaesse.datum <= end,
                            Anlaesse.punkte >= 0,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        werbungen = await db.scalar(
            select(func.count(Adressen.id)).where(
                and_(
                    Adressen.adressenid == adr.id,
                    Adressen.eintritt >= start,
                    Adressen.eintritt <= end,
                )
            )
        )
        sum_punkte = sum(int(m.punkte or 0) for m in meister_rows)
        mitglied_dauer = datetime.now(UTC).year - adr.eintritt.year if adr.eintritt else 0
        rec_list.append(
            ClubmeisterCreate(
                jahr=jahr,
                mitgliedid=adr.id,
                nachname=adr.name,
                vorname=adr.vorname,
                anlaesse=len(meister_rows),
                punkte=sum_punkte,
                werbungen=int(werbungen or 0),
                mitglieddauer=mitglied_dauer,
                status=True,
            )
        )

    rec_list.sort(
        key=lambda c: (
            -(c.punkte or 0),
            -(c.anlaesse or 0),
            -(c.werbungen or 0),
            -(c.mitglieddauer or 0),
        )
    )

    punkte_min = (rec_list[0].punkte or 0) * 0.4 if rec_list else 0
    now = datetime.now(UTC)
    for i, rec in enumerate(rec_list, start=1):
        rec.rang = i
        if (rec.punkte or 0) < punkte_min:
            rec.status = False
        db.add(Clubmeister(**rec.model_dump(), createdAt=now, updatedAt=now))
    await db.flush()
    return RetData(data=rec_list, message="Berechnung Clubmeister")


@router.post("", response_model=RetData[ClubmeisterEntity], status_code=201)
async def create(
    body: ClubmeisterCreate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[ClubmeisterEntity]:
    now = datetime.now(UTC)
    obj = Clubmeister(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=ClubmeisterEntity.model_validate(obj), message="create")


@router.get("", response_model=RetData[list[ClubmeisterEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[ClubmeisterEntity]]:
    rows = (
        (await db.execute(select(Clubmeister).order_by(Clubmeister.jahr.asc(), Clubmeister.rang.asc()))).scalars().all()
    )
    return RetData(data=[ClubmeisterEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{cm_id}", response_model=RetData[ClubmeisterEntity])
async def find_one(
    cm_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[ClubmeisterEntity]:
    obj = await db.get(Clubmeister, cm_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=ClubmeisterEntity.model_validate(obj), message="findOne")


@router.patch("/{cm_id}", response_model=RetData[ClubmeisterEntity])
async def update(
    cm_id: int,
    body: ClubmeisterUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[ClubmeisterEntity]:
    obj = await db.get(Clubmeister, cm_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Clubmeister nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=ClubmeisterEntity.model_validate(obj), message="update")


@router.delete("/{cm_id}", response_model=RetData[ClubmeisterEntity])
async def remove(
    cm_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[ClubmeisterEntity]:
    obj = await db.get(Clubmeister, cm_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Clubmeister nicht gefunden")
    await db.refresh(obj, ["adressen"])
    entity = ClubmeisterEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="remove")


# Silence unused-import warning for ``get_config`` that future logic may use.
_ = get_config
