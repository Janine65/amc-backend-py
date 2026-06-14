"""Schemas for the ``anlaesse`` module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AnlaesseBase(BaseModel):
    datum: date
    name: str
    beschreibung: str | None = None
    punkte: int | None = None
    istkegeln: bool = False
    istsamanlass: bool = False
    nachkegeln: bool = False
    gaeste: int | None = 0
    anlaesseid: int | None = None
    status: int = 1
    longname: str


class AnlaesseCreate(AnlaesseBase):
    pass


class AnlaesseUpdate(AnlaesseBase):
    datum: date | None = None  # type: ignore[assignment]
    name: str | None = None  # type: ignore[assignment]
    longname: str | None = None  # type: ignore[assignment]


class AnlaesseRef(AnlaesseBase):
    """Schmaler Self-Ref-Typ ohne weitere Verschachtelung (verhindert Rekursion)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class AnlaesseEntity(AnlaesseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    anlaesse: AnlaesseRef | None = None
