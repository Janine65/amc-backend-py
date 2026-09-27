"""Schemas for the ``kontakte`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class KontaktPublicCreate(BaseModel):
    """Öffentliche Kontaktanfrage von der Homepage (mit Honeypot-Feld ``website``)."""

    name: str = Field(min_length=1, max_length=100)
    vorname: str = Field(min_length=1, max_length=100)
    email: EmailStr
    betreff: str = Field(min_length=1, max_length=200)
    nachricht: str = Field(min_length=1, max_length=5000)
    # Honeypot: muss leer bleiben, wird von Bots ausgefüllt
    website: str | None = None
    # Rechen-Captcha (Token von GET /public/captcha)
    captcha: str | None = None
    captcha_token: str | None = None


class KontaktEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    vorname: str
    email: str
    betreff: str
    nachricht: str
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
