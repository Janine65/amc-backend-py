"""Schemas for the ``news`` module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class NewsBase(BaseModel):
    titel: str
    text: str
    bild: str | None = None
    datum: date
    publiziert: bool = False


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    titel: str | None = None
    text: str | None = None
    bild: str | None = None
    datum: date | None = None
    publiziert: bool | None = None


class NewsEntity(NewsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class NewsPublic(BaseModel):
    """Reduzierte Sicht für die Homepage."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    titel: str
    text: str
    bild: str | None = None
    datum: date
