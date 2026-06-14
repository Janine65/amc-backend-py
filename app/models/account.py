"""``account`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.budget import Budget
    from app.models.journal import Journal


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    longname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # relations
    budget_budget_accountToaccount: Mapped[list[Budget]] = relationship(
        "Budget", back_populates="account_budget_accountToaccount"
    )
    journal_journal_from_accountToaccount: Mapped[list[Journal]] = relationship(
        "Journal",
        foreign_keys="Journal.from_account",
        back_populates="account_journal_from_accountToaccount",
    )
    journal_journal_to_accountToaccount: Mapped[list[Journal]] = relationship(
        "Journal",
        foreign_keys="Journal.to_account",
        back_populates="account_journal_to_accountToaccount",
    )
