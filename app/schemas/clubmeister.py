"""Schemas for the ``clubmeister`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.adressen import AdressenRefSelf


class ClubmeisterBase(BaseModel):
    jahr: str
    rang: int | None = None
    vorname: str | None = None
    nachname: str | None = None
    mitgliedid: int
    punkte: int | None = None
    anlaesse: int | None = None
    werbungen: int | None = None
    mitglieddauer: int | None = None
    status: bool = True


class ClubmeisterCreate(ClubmeisterBase):
    pass


class ClubmeisterUpdate(BaseModel):
    rang: int | None = None
    punkte: int | None = None
    anlaesse: int | None = None
    werbungen: int | None = None
    mitglieddauer: int | None = None
    status: bool | None = None


class ClubmeisterEntity(ClubmeisterBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    adressen: AdressenRefSelf | None = None
