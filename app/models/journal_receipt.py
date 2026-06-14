"""``journal_receipt`` join table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.journal import Journal
    from app.models.receipt import Receipt


class JournalReceipt(Base):
    __tablename__ = "journal_receipt"

    journalid: Mapped[int] = mapped_column(Integer, ForeignKey("journal.id", ondelete="CASCADE"), primary_key=True)
    receiptid: Mapped[int] = mapped_column(Integer, ForeignKey("receipt.id", ondelete="CASCADE"), primary_key=True)

    journal: Mapped[Journal] = relationship("Journal", back_populates="journal_receipt")
    receipt: Mapped[Receipt] = relationship("Receipt", back_populates="journal_receipt", lazy="selectin")
