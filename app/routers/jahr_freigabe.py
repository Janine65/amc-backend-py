"""``jahr_freigabe`` router (Freigabe der Meisterschafts-Jahre, nur mit Login)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.jahr_freigabe import JahrFreigabe
from app.schemas.jahr_freigabe import JahrFreigabeEntity, JahrFreigabeUpsert
from app.schemas.ret_data import RetData

router = APIRouter(prefix="/jahrfreigabe", tags=["JahrFreigabe"])


@router.get("", response_model=RetData[list[JahrFreigabeEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[JahrFreigabeEntity]]:
    rows = (await db.execute(select(JahrFreigabe).order_by(JahrFreigabe.jahr.desc()))).scalars().all()
    return RetData(data=[JahrFreigabeEntity.model_validate(r) for r in rows], message="findAll")


@router.put("", response_model=RetData[JahrFreigabeEntity])
async def upsert(
    body: JahrFreigabeUpsert, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[JahrFreigabeEntity]:
    now = datetime.now(UTC)
    obj = await db.scalar(select(JahrFreigabe).where(JahrFreigabe.jahr == body.jahr))
    if obj is None:
        obj = JahrFreigabe(**body.model_dump(), createdAt=now, updatedAt=now)
        db.add(obj)
    else:
        obj.clubmeister = body.clubmeister
        obj.kegelmeister = body.kegelmeister
        obj.updatedAt = now
    await db.flush()
    return RetData(data=JahrFreigabeEntity.model_validate(obj), message="Freigabe gespeichert")
