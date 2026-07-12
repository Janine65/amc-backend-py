"""Schemas for the ``kegelkasse`` module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.journal import JournalEntity
from app.schemas.user import UserEntity


class KegelkasseBase(BaseModel):
    datum: date
    kasse: float
    rappen5: int
    rappen10: int
    rappen20: int
    rappen50: int
    franken1: int
    franken2: int
    franken5: int
    franken10: int
    franken20: int
    franken50: int
    franken100: int
    total: float
    differenz: float
    journalid: int | None = None
    userid: int | None = None


class KegelkasseCreate(KegelkasseBase):
    pass


class KegelkasseUpdate(KegelkasseBase):
    datum: date | None = None  # type: ignore[assignment]
    kasse: float | None = None  # type: ignore[assignment]
    rappen5: int | None = None  # type: ignore[assignment]
    rappen10: int | None = None  # type: ignore[assignment]
    rappen20: int | None = None  # type: ignore[assignment]
    rappen50: int | None = None  # type: ignore[assignment]
    franken1: int | None = None  # type: ignore[assignment]
    franken2: int | None = None  # type: ignore[assignment]
    franken5: int | None = None  # type: ignore[assignment]
    franken10: int | None = None  # type: ignore[assignment]
    franken20: int | None = None  # type: ignore[assignment]
    franken50: int | None = None  # type: ignore[assignment]
    franken100: int | None = None  # type: ignore[assignment]
    total: float | None = None  # type: ignore[assignment]
    differenz: float | None = None  # type: ignore[assignment]


class KegelkasseEntity(KegelkasseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    journal: JournalEntity | None = None
    user: UserEntity | None = None
    userName: str | None = None
    cntUsers: int | None = None
    amountProUser: float | None = None
