"""Reduzierte, öffentliche Sichten für die Homepage (``/public``)."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, ConfigDict


class AgendaPublic(BaseModel):
    """Öffentliche Sicht auf einen Anlass (ohne interne Punkte/Status)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    datum: date
    name: str
    beschreibung: str | None = None
    istkegeln: bool = False
    istmotorrad: bool = False
    zeit_von: time | None = None
    zeit_bis: time | None = None
    ort: str | None = None


class MeisterPublic(BaseModel):
    """Öffentliche Sicht auf einen Club-/Kegelmeister-Eintrag."""

    model_config = ConfigDict(from_attributes=True)
    rang: int | None = None
    vorname: str | None = None
    nachname: str | None = None
    punkte: int | None = None
    anlaesse: int | None = None


class JahrFreigabePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    jahr: str
    clubmeister: bool
    kegelmeister: bool
