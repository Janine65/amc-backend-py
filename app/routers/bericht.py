"""``berichte`` router (Pflege der Homepage-Berichte, nur mit Login)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.bericht import Bericht
from app.schemas.bericht import BerichtCreate, BerichtEntity, BerichtUpdate
from app.schemas.ret_data import RetData

router = APIRouter(prefix="/berichte", tags=["Berichte"])


@router.post("", response_model=RetData[BerichtEntity], status_code=201)
async def create(
    body: BerichtCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[BerichtEntity]:
    now = datetime.now(UTC)
    obj = Bericht(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    return RetData(data=BerichtEntity.model_validate(obj), message="Bericht erstellt")


@router.get("", response_model=RetData[list[BerichtEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[BerichtEntity]]:
    rows = (await db.execute(select(Bericht).order_by(Bericht.datum.desc()))).scalars().all()
    return RetData(data=[BerichtEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{b_id}", response_model=RetData[BerichtEntity])
async def find_one(b_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[BerichtEntity]:
    obj = await db.get(Bericht, b_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=BerichtEntity.model_validate(obj), message="findOne")


@router.patch("/{b_id}", response_model=RetData[BerichtEntity])
async def update(
    b_id: int, body: BerichtUpdate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[BerichtEntity]:
    obj = await db.get(Bericht, b_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    return RetData(data=BerichtEntity.model_validate(obj), message="Bericht aktualisiert")


@router.delete("/{b_id}", response_model=RetData[BerichtEntity])
async def remove(b_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[BerichtEntity]:
    obj = await db.get(Bericht, b_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    entity = BerichtEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Bericht gelöscht")
