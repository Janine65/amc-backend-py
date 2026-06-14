"""Authentication router (login, refresh)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import create_access_token, verify_password
from app.dependencies import CurrentUser
from app.models.user import User
from app.schemas.ret_data import CookiePayload, RetDataUser
from app.schemas.user import LoginRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    """OAuth2 password-flow response (used by Swagger ``Authorize`` dialog)."""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=RetDataUser)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> RetDataUser:
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")
    user.last_login = datetime.now(UTC)
    await db.flush()
    token = create_access_token({"userId": user.id})
    return RetDataUser(
        cookie=CookiePayload(accessToken=token),
        data={"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        message="Login OK",
        type="info",
    )


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """OAuth2 password-flow endpoint.

    Wird vom Swagger ``Authorize``-Dialog genutzt: ``username`` ist die Email,
    ``password`` das Passwort. Antwort enthält ``access_token``/``token_type``,
    Swagger setzt den Bearer-Header danach automatisch.
    """
    user = await db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login = datetime.now(UTC)
    await db.flush()
    token = create_access_token({"userId": user.id})
    return TokenResponse(access_token=token)


@router.get("/refreshToken", response_model=RetDataUser)
async def refresh_token(current: CurrentUser) -> RetDataUser:
    token = create_access_token({"userId": current.id})
    return RetDataUser(
        cookie=CookiePayload(accessToken=token),
        data={"id": current.id, "email": current.email, "name": current.name},
        message="Token refreshed",
        type="info",
    )
