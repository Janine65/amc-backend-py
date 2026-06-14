"""Schemas for the ``user`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "user"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    password: str | None = None


class UserEntity(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    userid: str | None = None
    last_login: datetime | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class NewPasswordRequest(BaseModel):
    email: EmailStr


class TokenPayload(BaseModel):
    userId: int
