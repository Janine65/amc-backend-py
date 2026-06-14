"""Schemas for the ``adressen`` module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AdressenBase(BaseModel):
    mnr: int | None = None
    geschlecht: int = 1
    name: str
    vorname: str
    adresse: str
    plz: int
    ort: str
    land: str = "CH"
    telefon_p: str | None = None
    telefon_g: str | None = None
    mobile: str | None = None
    email: str | None = None
    eintritt: date | None = None
    sam_mitglied: bool = False
    jahresbeitrag: float | None = None
    mnr_sam: int | None = None
    vorstand: bool = False
    ehrenmitglied: bool = False
    veteran1: bool = False
    veteran2: bool = False
    revisor: bool = False
    motojournal: bool = False
    austritt: date | None = None
    austritt_mail: bool = False
    adressenid: int | None = None
    jahrgang: int | None = None
    arbeitgeber: str | None = None
    pensioniert: bool = False
    allianz: bool = False
    notes: str | None = None
    fullname: str | None = None


class AdressenCreate(AdressenBase):
    pass


class AdressenUpdate(AdressenBase):
    name: str | None = None  # type: ignore[assignment]
    vorname: str | None = None  # type: ignore[assignment]
    adresse: str | None = None  # type: ignore[assignment]
    plz: int | None = None  # type: ignore[assignment]
    ort: str | None = None  # type: ignore[assignment]


class AdressenRefSelf(AdressenBase):
    """Schmaler Self-Ref-Typ ohne weitere Verschachtelung (verhindert Rekursion)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class AdressenEntity(AdressenBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    adressen: AdressenRefSelf | None = None


class QrBillRequest(BaseModel):
    """Body for ``POST /adressen/qrbill/{id}``."""

    sender: str | None = None
    subject: str | None = None
    text: str | None = None
    attachReceipt: bool | None = False


class EmailAttachment(BaseModel):
    filename: str
    path: str | None = None
    content: bytes | None = None


class EmailRequest(BaseModel):
    """Body for ``POST /adressen/email`` (mass email)."""

    sender: str | None = None
    subject: str | None = ""
    text: str | None = ""
    html: str | None = None
    attachments: list[EmailAttachment] = []
    recipients: list[str] = []
