"""Schemas for the ``account`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountBase(BaseModel):
    name: str | None = None
    level: int | None = None
    order: int | None = None
    status: int | None = None
    longname: str | None = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(AccountBase):
    pass


class AccountEntity(AccountBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
