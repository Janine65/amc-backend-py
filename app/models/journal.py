"""``journal`` table."""

from __future__ import annotations

from datetime import date as date_t
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.account import Account
    from app.models.fiscalyear import Fiscalyear
    from app.models.journal_receipt import JournalReceipt
    from app.models.kegelkasse import Kegelkasse


class Journal(Base):
    __tablename__ = "journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_account: Mapped[int | None] = mapped_column(Integer, ForeignKey("account.id"), nullable=True)
    to_account: Mapped[int | None] = mapped_column(Integer, ForeignKey("account.id"), nullable=True)
    date: Mapped[date_t | None] = mapped_column(Date, nullable=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    journalno: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, default=0, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, ForeignKey("fiscalyear.year"), nullable=True)

    account_journal_from_accountToaccount: Mapped[Account | None] = relationship(
        "Account",
        foreign_keys=[from_account],
        back_populates="journal_journal_from_accountToaccount",
        lazy="selectin",
    )
    account_journal_to_accountToaccount: Mapped[Account | None] = relationship(
        "Account",
        foreign_keys=[to_account],
        back_populates="journal_journal_to_accountToaccount",
        lazy="selectin",
    )
    fiscalyear: Mapped[Fiscalyear | None] = relationship("Fiscalyear", back_populates="journal")
    journal_receipt: Mapped[list[JournalReceipt]] = relationship(
        "JournalReceipt", back_populates="journal", cascade="all, delete-orphan", lazy="selectin"
    )
    kegelkasse: Mapped[list[Kegelkasse]] = relationship("Kegelkasse", back_populates="journal")
