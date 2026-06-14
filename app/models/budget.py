"""``budget`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.account import Account
    from app.models.fiscalyear import Fiscalyear


class Budget(Base):
    __tablename__ = "budget"
    __table_args__ = (UniqueConstraint("account", "year", name="budget_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[int] = mapped_column(Integer, ForeignKey("account.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, ForeignKey("fiscalyear.year"), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    account_budget_accountToaccount: Mapped[Account] = relationship(
        "Account", back_populates="budget_budget_accountToaccount", lazy="selectin", join_depth=1
    )
    fiscalyear: Mapped[Fiscalyear] = relationship("Fiscalyear", back_populates="budget", lazy="selectin", join_depth=1)
