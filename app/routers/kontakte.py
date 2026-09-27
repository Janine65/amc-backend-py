"""``kontakte`` router (Verwaltung der Kontaktanfragen, nur mit Login)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.kontakt import Kontakt
from app.schemas.kontakt import KontaktEntity
from app.schemas.ret_data import RetData

router = APIRouter(prefix="/kontakte", tags=["Kontakte"])


@router.get("", response_model=RetData[list[KontaktEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[KontaktEntity]]:
    rows = (await db.execute(select(Kontakt).order_by(Kontakt.createdAt.desc()))).scalars().all()
    return RetData(data=[KontaktEntity.model_validate(r) for r in rows], message="findAll")


@router.delete("/{k_id}", response_model=RetData[KontaktEntity])
async def remove(k_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[KontaktEntity]:
    obj = await db.get(Kontakt, k_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Kontaktanfrage nicht gefunden")
    entity = KontaktEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Kontaktanfrage gelöscht")
