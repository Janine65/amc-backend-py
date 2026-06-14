"""``kegelkasse`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.journal import Journal
    from app.models.user import User


class Kegelkasse(Base):
    __tablename__ = "kegelkasse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    kasse: Mapped[float] = mapped_column(Float, nullable=False)
    rappen5: Mapped[int] = mapped_column(Integer, nullable=False)
    rappen10: Mapped[int] = mapped_column(Integer, nullable=False)
    rappen20: Mapped[int] = mapped_column(Integer, nullable=False)
    rappen50: Mapped[int] = mapped_column(Integer, nullable=False)
    franken1: Mapped[int] = mapped_column(Integer, nullable=False)
    franken2: Mapped[int] = mapped_column(Integer, nullable=False)
    franken5: Mapped[int] = mapped_column(Integer, nullable=False)
    franken10: Mapped[int] = mapped_column(Integer, nullable=False)
    franken20: Mapped[int] = mapped_column(Integer, nullable=False)
    franken50: Mapped[int] = mapped_column(Integer, nullable=False)
    franken100: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    differenz: Mapped[float] = mapped_column(Float, nullable=False)
    journalid: Mapped[int | None] = mapped_column(Integer, ForeignKey("journal.id"), nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    userid: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)

    journal: Mapped[Journal | None] = relationship("Journal", back_populates="kegelkasse", lazy="selectin")
    user: Mapped[User | None] = relationship("User", back_populates="kegelkasse", lazy="selectin")
