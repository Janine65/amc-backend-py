"""``parameter`` service + router (simple CRUD)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.parameter import Parameter
from app.schemas.parameter import ParameterCreate, ParameterEntity, ParameterUpdate
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/parameter", tags=["Parameter"])


@router.post("", response_model=RetData[ParameterEntity], status_code=status.HTTP_201_CREATED)
async def create(
    body: ParameterCreate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[ParameterEntity]:
    obj = Parameter(**body.model_dump(), createdAt=datetime.now(UTC), updatedAt=datetime.now(UTC))
    db.add(obj)
    await db.flush()
    await load_params(True)  # reload params to update the cache
    return RetData(data=ParameterEntity.model_validate(obj), message="Parameter created")


@router.get("", response_model=RetData[list[ParameterEntity]])
async def find_all(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[ParameterEntity]]:
    result = await db.execute(select(Parameter))
    items = [ParameterEntity.model_validate(p) for p in result.scalars()]
    return RetData(data=items, message="Parameters found")


@router.get("/{param_id}", response_model=RetData[ParameterEntity])
async def find_one(
    param_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[ParameterEntity]:
    obj = await db.get(Parameter, param_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Parameter with {param_id} does not exist.")
    return RetData(data=ParameterEntity.model_validate(obj), message="Parameter found")


@router.patch("/{param_id}", response_model=RetData[ParameterEntity])
async def update(
    param_id: int,
    body: ParameterUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[ParameterEntity]:
    obj = await db.get(Parameter, param_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Parameter not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await load_params(True)  # reload params to update the cache
    return RetData(data=ParameterEntity.model_validate(obj), message="Parameter updated")


@router.delete("/{param_id}", response_model=RetData[ParameterEntity])
async def remove(
    param_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[ParameterEntity]:
    obj = await db.get(Parameter, param_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Parameter not found")
    entity = ParameterEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    await load_params(True)  # reload params to update the cache
    return RetData(data=entity, message="Parameter removed")
