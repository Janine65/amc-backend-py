"""``anlass_anmeldungen`` router (Verwaltung der Anmeldungen, nur mit Login)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.anlass_anmeldung import AnlassAnmeldung
from app.schemas.anlass_anmeldung import AnmeldungEntity, AnmeldungUpdate
from app.schemas.ret_data import RetData

router = APIRouter(prefix="/anmeldungen", tags=["Anmeldungen"])


@router.get("", response_model=RetData[list[AnmeldungEntity]])
async def find_all(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    anlassid: int | None = None,
) -> RetData[list[AnmeldungEntity]]:
    stmt = select(AnlassAnmeldung).order_by(AnlassAnmeldung.createdAt.desc())
    if anlassid is not None:
        stmt = stmt.where(AnlassAnmeldung.anlassid == anlassid)
    rows = (await db.execute(stmt)).scalars().all()
    return RetData(data=[AnmeldungEntity.model_validate(r) for r in rows], message="findAll")


@router.patch("/{a_id}", response_model=RetData[AnmeldungEntity])
async def update(
    a_id: int, body: AnmeldungUpdate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AnmeldungEntity]:
    obj = await db.get(AnlassAnmeldung, a_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Anmeldung nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    return RetData(data=AnmeldungEntity.model_validate(obj), message="Anmeldung aktualisiert")


@router.delete("/{a_id}", response_model=RetData[AnmeldungEntity])
async def remove(a_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[AnmeldungEntity]:
    obj = await db.get(AnlassAnmeldung, a_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Anmeldung nicht gefunden")
    entity = AnmeldungEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Anmeldung gelöscht")
