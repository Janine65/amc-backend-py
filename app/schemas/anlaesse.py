"""Schemas for the ``anlaesse`` module."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, field_validator


class AnlaesseBase(BaseModel):
    datum: date
    name: str
    beschreibung: str | None = None
    punkte: int | None = None
    istkegeln: bool = False
    istsamanlass: bool = False
    nachkegeln: bool = False
    istmotorrad: bool = False
    gaeste: int | None = 0
    anlaesseid: int | None = None
    status: int = 1
    longname: str
    zeit_von: time | None = None
    zeit_bis: time | None = None
    ort: str | None = None

    @field_validator("istkegeln", "istsamanlass", "nachkegeln", "istmotorrad", mode="before")
    @classmethod
    def _bool_none_to_false(cls, v: object) -> object:
        # Frontend sendet für nicht gesetzte Checkboxen null
        return False if v is None else v


class AnlaesseCreate(AnlaesseBase):
    # longname wird im Backend aus Datum + Name generiert
    longname: str | None = None  # type: ignore[assignment]


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
