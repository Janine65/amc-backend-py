"""Schemas for the ``kegelmeister`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.adressen import AdressenRefSelf


class KegelmeisterBase(BaseModel):
    jahr: str
    rang: int | None = None
    vorname: str | None = None
    nachname: str | None = None
    mitgliedid: int
    punkte: int | None = None
    anlaesse: int | None = None
    babeli: int | None = None
    status: bool = True


class KegelmeisterCreate(KegelmeisterBase):
    pass


class KegelmeisterUpdate(BaseModel):
    rang: int | None = None
    punkte: int | None = None
    anlaesse: int | None = None
    babeli: int | None = None
    status: bool | None = None


class KegelmeisterEntity(KegelmeisterBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    adressen: AdressenRefSelf | None = None
