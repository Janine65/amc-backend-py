"""Schemas for the ``meisterschaft`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.anlaesse import AnlaesseRef


class AdressenRef(BaseModel):
    """Minimal address reference (id + fullname) used in nested responses."""

    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    fullname: str | None = None


class MeisterschaftBase(BaseModel):
    mitgliedid: int = 0
    eventid: int = 0
    punkte: int | None = 50
    wurf1: int | None = 0
    wurf2: int | None = 0
    wurf3: int | None = 0
    wurf4: int | None = 0
    wurf5: int | None = 0
    zusatz: int | None = 5
    streichresultat: bool | None = False
    total_kegel: int | None = None


class MeisterschaftCreate(MeisterschaftBase):
    pass


class MeisterschaftUpdate(MeisterschaftBase):
    mitgliedid: int | None = None  # type: ignore[assignment]
    eventid: int | None = None  # type: ignore[assignment]


class MeisterschaftEntity(MeisterschaftBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    anlaesse: AnlaesseRef | None = None
    adressen: AdressenRef | None = None


class MeisterEntity(BaseModel):
    """Aggregated meister entity per Mitglied/Jahr (port of MeisterEnitity)."""

    jahr: str
    rang: int | None = None
    vorname: str | None = None
    nachname: str | None = None
    mitgliedid: int
    clubpunkte: int | None = None
    kegelpunkte: int | None = None
    anlaesse: int | None = None
    babeli: int | None = None
    werbungen: int | None = None
    mitglieddauer: int | None = None
    diff_first: int | None = None
