"""``user`` service + router (port of ``UserService``/``UserController``)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import hash_password
from app.dependencies import CurrentUser
from app.models.user import User
from app.schemas.ret_data import RetData
from app.schemas.user import UserCreate, UserEntity, UserUpdate
from app.utils.mail import send_mail

logger = get_logger(__name__)

router = APIRouter(prefix="/user", tags=["Users"])


async def _new_password(db: AsyncSession, email: str) -> User:
    new_password = uuid.uuid4().hex[:10]
    logger.info("Generated new password for %s", email)
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")
    user.password = hash_password(new_password)
    user.updatedAt = datetime.now(UTC)
    await db.flush()
    await send_mail(
        to=user.email,
        subject="Neues Passwort",
        text=f"Dein neues Passwort lautet: {new_password}",
    )
    return user


@router.post("", response_model=RetData[UserEntity], status_code=201)
async def create(body: UserCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[UserEntity]:
    now = datetime.now(UTC)
    user = User(
        name=body.name,
        email=body.email,
        role=body.role,
        password="initialPWD",
        userid=str(uuid.uuid4()),
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    await db.flush()
    user = await _new_password(db, body.email)
    return RetData(data=UserEntity.model_validate(user), message="User created")


@router.get("", response_model=RetData[list[UserEntity]])
async def list_users(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[UserEntity]]:
    rows = (await db.execute(select(User))).scalars().all()
    return RetData(data=[UserEntity.model_validate(u) for u in rows], message="Users found")


@router.get("/newpass/{email}", response_model=RetData[UserEntity])
async def new_password(email: str, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[UserEntity]:
    user = await _new_password(db, email)
    return RetData(data=UserEntity.model_validate(user), message="New password sent")


@router.get("/{user_id}", response_model=RetData[UserEntity])
async def find_one(user_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[UserEntity]:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    return RetData(data=UserEntity.model_validate(user), message="User found")


@router.patch("/{user_id}", response_model=RetData[UserEntity])
async def update(
    user_id: int,
    body: UserUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[UserEntity]:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    payload = body.model_dump(exclude_none=True)
    if "password" in payload:
        payload["password"] = hash_password(payload["password"])
    for k, v in payload.items():
        setattr(user, k, v)
    user.updatedAt = datetime.now(UTC)
    await db.flush()
    return RetData(data=UserEntity.model_validate(user), message="User updated")


@router.delete("/{user_id}", response_model=RetData[UserEntity])
async def remove(user_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[UserEntity]:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    entity = UserEntity.model_validate(user)
    await db.delete(user)
    await db.flush()
    return RetData(data=entity, message="User deleted")
