"""``news`` router (Pflege der Homepage-News, nur mit Login)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.news import News
from app.schemas.news import NewsCreate, NewsEntity, NewsUpdate
from app.schemas.ret_data import RetData

router = APIRouter(prefix="/news", tags=["News"])


@router.post("", response_model=RetData[NewsEntity], status_code=201)
async def create(body: NewsCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[NewsEntity]:
    now = datetime.now(UTC)
    obj = News(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    return RetData(data=NewsEntity.model_validate(obj), message="News erstellt")


@router.get("", response_model=RetData[list[NewsEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[NewsEntity]]:
    rows = (await db.execute(select(News).order_by(News.datum.desc()))).scalars().all()
    return RetData(data=[NewsEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{n_id}", response_model=RetData[NewsEntity])
async def find_one(n_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[NewsEntity]:
    obj = await db.get(News, n_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=NewsEntity.model_validate(obj), message="findOne")


@router.patch("/{n_id}", response_model=RetData[NewsEntity])
async def update(
    n_id: int, body: NewsUpdate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[NewsEntity]:
    obj = await db.get(News, n_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="News nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    return RetData(data=NewsEntity.model_validate(obj), message="News aktualisiert")


@router.delete("/{n_id}", response_model=RetData[NewsEntity])
async def remove(n_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[NewsEntity]:
    obj = await db.get(News, n_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="News nicht gefunden")
    entity = NewsEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="News gelöscht")
