"""``receipt`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.journal_receipt import JournalReceipt


class Receipt(Base):
    __tablename__ = "receipt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    jahr: Mapped[str | None] = mapped_column(String(4), nullable=True)
    bezeichnung: Mapped[str | None] = mapped_column(String(100), nullable=True)

    journal_receipt: Mapped[list[JournalReceipt]] = relationship(
        "JournalReceipt", back_populates="receipt", cascade="all, delete-orphan", lazy="selectin"
    )
