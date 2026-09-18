"""Schemas for the ``berichte`` module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BerichtBase(BaseModel):
    titel: str
    text: str
    datei: str | None = None
    datum: date
    publiziert: bool = False


class BerichtCreate(BerichtBase):
    pass


class BerichtUpdate(BaseModel):
    titel: str | None = None
    text: str | None = None
    datei: str | None = None
    datum: date | None = None
    publiziert: bool | None = None


class BerichtEntity(BerichtBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class BerichtPublic(BaseModel):
    """Reduzierte Sicht für die Homepage."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    titel: str
    text: str
    datei: str | None = None
    datum: date
