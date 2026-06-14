"""Schemas for the ``receipt`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReceiptBase(BaseModel):
    receipt: str
    jahr: str | None = None
    bezeichnung: str | None = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(BaseModel):
    receipt: str | None = None
    jahr: str | None = None
    bezeichnung: str | None = None


class JournalReceiptForReceipt(BaseModel):
    """Nested ``journal_receipt`` row exposed inside a ``ReceiptEntity``.

    Bewusst ohne ``journal``-Verschachtelung, um Zirkular-Imports mit
    ``app.schemas.journal`` zu vermeiden.
    """

    model_config = ConfigDict(from_attributes=True)
    journalid: int
    receiptid: int


class ReceiptEntity(ReceiptBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    journal_receipt: list[JournalReceiptForReceipt] = []


class Add2JournalRequest(BaseModel):
    receiptid: int
    journalid: int
    sourceFilename: str
