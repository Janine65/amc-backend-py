"""``fiscalyear`` table."""

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


class Fiscalyear(Base):
    __tablename__ = "fiscalyear"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    budget: Mapped[list[Budget]] = relationship("Budget", back_populates="fiscalyear")
    journal: Mapped[list[Journal]] = relationship("Journal", back_populates="fiscalyear")
