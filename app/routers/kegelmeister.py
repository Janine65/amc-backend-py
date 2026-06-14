"""``kegelmeister`` router (port of NestJS ``KegelmeisterService``)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.adressen import Adressen
from app.models.anlaesse import Anlaesse
from app.models.kegelmeister import Kegelmeister
from app.models.meisterschaft import Meisterschaft
from app.schemas.kegelmeister import KegelmeisterCreate, KegelmeisterEntity, KegelmeisterUpdate
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/kegelmeister", tags=["Kegelmeister"])


@router.get("/byjahr", response_model=RetData[list[KegelmeisterEntity]])
async def find_all_by_jahr(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[KegelmeisterEntity]]:
    rows = (
        (
            await db.execute(
                select(Kegelmeister)
                .where(Kegelmeister.jahr == jahr)
                .order_by(Kegelmeister.jahr.asc(), Kegelmeister.rang.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[KegelmeisterEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/overview", response_model=RetData[list[dict]])
async def overview(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[dict]]:
    params = await load_params()
    year = params.get("CLUBJAHR", "")
    count = await db.scalar(select(func.count(Kegelmeister.id)).where(Kegelmeister.jahr == year))
    return RetData(
        data=[{"label": "Kegelmeisterschaft", "value": int(count or 0)}],
        message="Übersicht Kegelmeister",
    )


@router.get("/calcMeister", response_model=RetData[list[KegelmeisterCreate]])
async def calc_meister(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[KegelmeisterCreate]]:
    start = date(int(jahr), 1, 1)
    end = date(int(jahr), 12, 31)

    # reset previous streichresultat
    await db.execute(
        sa_update(Meisterschaft)
        .where(
            Meisterschaft.eventid.in_(
                select(Anlaesse.id).where(
                    and_(
                        Anlaesse.datum >= start,
                        Anlaesse.datum <= end,
                        Anlaesse.istkegeln.is_(True),
                    )
                )
            )
        )
        .values(streichresultat=False, updatedAt=datetime.now(UTC))
    )
    await db.execute(delete(Kegelmeister).where(Kegelmeister.jahr == jahr))

    # Adressen with at least one Kegel-Meisterschaft this year
    adr_ids_subq = (
        select(Meisterschaft.mitgliedid)
        .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
        .where(
            and_(
                Meisterschaft.total_kegel > 0,
                Anlaesse.datum >= start,
                Anlaesse.datum <= end,
                Anlaesse.istkegeln.is_(True),
            )
        )
        .distinct()
    )
    adr_rows = (await db.execute(select(Adressen).where(Adressen.id.in_(adr_ids_subq)))).scalars().all()

    params = await load_params()
    act_jahr = jahr == params.get("CLUBJAHR")
    if act_jahr:
        cnt_anl = await db.scalar(
            select(func.count(Anlaesse.id)).where(
                and_(
                    Anlaesse.datum >= datetime.now(UTC).date(),
                    Anlaesse.datum <= end,
                    Anlaesse.istkegeln.is_(True),
                    Anlaesse.nachkegeln.is_(False),
                )
            )
        )
        if (cnt_anl or 0) > 0:
            act_jahr = False
    anzahl_kegel = int(params.get("ANZAHL_KEGEL", "0") or 0)

    rec_list: list[KegelmeisterCreate] = []
    for adr in adr_rows:
        meister_rows = (
            await db.execute(
                select(Meisterschaft, Anlaesse)
                .join(Anlaesse, Anlaesse.id == Meisterschaft.eventid)
                .where(
                    and_(
                        Meisterschaft.mitgliedid == adr.id,
                        Meisterschaft.total_kegel > 0,
                        Anlaesse.datum >= start,
                        Anlaesse.datum <= end,
                        Anlaesse.istkegeln.is_(True),
                    )
                )
                .order_by(Meisterschaft.total_kegel.desc())
            )
        ).all()

        total_kegel = 0
        babeli = 0
        anz_erg = 0
        anlaesse_count = 0
        for meister, anl in meister_rows:
            total_kegel += int(meister.total_kegel or 0)
            for w in (meister.wurf1, meister.wurf2, meister.wurf3, meister.wurf4, meister.wurf5):
                if w == 9:
                    babeli += 1
            if not anl.nachkegeln:
                anlaesse_count += 1
            anz_erg += 1
            if act_jahr and anz_erg > anzahl_kegel:
                total_kegel -= int(meister.total_kegel or 0)
                meister.streichresultat = True
                meister.updatedAt = datetime.now(UTC)
        rec_list.append(
            KegelmeisterCreate(
                jahr=jahr,
                mitgliedid=adr.id,
                nachname=adr.name,
                vorname=adr.vorname,
                anlaesse=anlaesse_count,
                punkte=total_kegel,
                babeli=babeli,
                status=True,
            )
        )

    rec_list.sort(key=lambda k: (-(k.punkte or 0), -(k.anlaesse or 0), -(k.babeli or 0)))
    punkte_min = (rec_list[0].punkte or 0) * 0.4 if rec_list else 0
    now = datetime.now(UTC)
    for i, rec in enumerate(rec_list, start=1):
        rec.rang = i
        if (rec.punkte or 0) < punkte_min:
            rec.status = False
        db.add(Kegelmeister(**rec.model_dump(), createdAt=now, updatedAt=now))
    await db.flush()
    return RetData(data=rec_list, message="Berechnung Kegelmeister")


@router.post("", response_model=RetData[KegelmeisterEntity], status_code=201)
async def create(
    body: KegelmeisterCreate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[KegelmeisterEntity]:
    now = datetime.now(UTC)
    obj = Kegelmeister(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=KegelmeisterEntity.model_validate(obj), message="create")


@router.get("", response_model=RetData[list[KegelmeisterEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[KegelmeisterEntity]]:
    rows = (
        (await db.execute(select(Kegelmeister).order_by(Kegelmeister.jahr.asc(), Kegelmeister.rang.asc())))
        .scalars()
        .all()
    )
    return RetData(data=[KegelmeisterEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{km_id}", response_model=RetData[KegelmeisterEntity])
async def find_one(
    km_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[KegelmeisterEntity]:
    obj = await db.get(Kegelmeister, km_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=KegelmeisterEntity.model_validate(obj), message="findOne")


@router.patch("/{km_id}", response_model=RetData[KegelmeisterEntity])
async def update(
    km_id: int,
    body: KegelmeisterUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[KegelmeisterEntity]:
    obj = await db.get(Kegelmeister, km_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Kegelmeister nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=KegelmeisterEntity.model_validate(obj), message="update")


@router.delete("/{km_id}", response_model=RetData[KegelmeisterEntity])
async def remove(
    km_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[KegelmeisterEntity]:
    obj = await db.get(Kegelmeister, km_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Kegelmeister nicht gefunden")
    await db.refresh(obj, ["adressen"])
    entity = KegelmeisterEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="remove")
