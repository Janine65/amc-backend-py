"""Schemas for the ``journal_receipt`` module."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JournalReceiptBase(BaseModel):
    journalid: int
    receiptid: int


class JournalReceiptCreate(JournalReceiptBase):
    pass


class JournalReceiptEntity(JournalReceiptBase):
    model_config = ConfigDict(from_attributes=True)
