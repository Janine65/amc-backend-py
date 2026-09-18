"""Schemas for the ``anlass_anmeldungen`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AnmeldungPublicCreate(BaseModel):
    """Öffentliche Anmeldung von der Homepage (mit Honeypot-Feld ``website``)."""

    anlassid: int
    name: str = Field(min_length=1, max_length=100)
    vorname: str = Field(min_length=1, max_length=100)
    email: EmailStr
    bemerkung: str | None = Field(default=None, max_length=500)
    # Honeypot: muss leer bleiben, wird von Bots ausgefüllt
    website: str | None = None


class AnmeldungUpdate(BaseModel):
    status: int | None = None
    bemerkung: str | None = None


class AnmeldungEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    anlassid: int
    name: str
    vorname: str
    email: str
    bemerkung: str | None = None
    status: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
