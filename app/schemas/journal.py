"""Schemas for the ``journal`` module."""

from __future__ import annotations

from datetime import date as date_t
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.account import AccountEntity


class JournalBase(BaseModel):
    from_account: int | None = None
    to_account: int | None = None
    date: date_t | None = None
    memo: str | None = None
    journalno: int | None = None
    amount: float | None = 0
    status: int | None = None
    year: int | None = None


class JournalCreate(JournalBase):
    pass


class JournalUpdate(JournalBase):
    pass


class ReceiptForJournal(BaseModel):
    """Slim Receipt-View ohne Backref ``journal_receipt`` (verhindert Lazy-Load-Kaskade)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    receipt: str | None = None
    bezeichnung: str | None = None
    jahr: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class JournalReceiptNested(BaseModel):
    """Nested ``journal_receipt`` row exposed inside a ``JournalEntity``."""

    model_config = ConfigDict(from_attributes=True)
    journalid: int
    receiptid: int
    receipt: ReceiptForJournal | None = None


class JournalEntity(JournalBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    account_journal_from_accountToaccount: AccountEntity | None = None
    account_journal_to_accountToaccount: AccountEntity | None = None
    journal_receipt: list[JournalReceiptNested] = []
