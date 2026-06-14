"""``kegelmeister`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.adressen import Adressen


class Kegelmeister(Base):
    __tablename__ = "kegelmeister"
    __table_args__ = (UniqueConstraint("jahr", "rang", name="kegelmeister_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jahr: Mapped[str] = mapped_column(String(4), nullable=False)
    rang: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    vorname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nachname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mitgliedid: Mapped[int] = mapped_column(SmallInteger, ForeignKey("adressen.id"), nullable=False)
    punkte: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    anlaesse: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    babeli: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    adressen: Mapped[Adressen] = relationship("Adressen", back_populates="kegelmeister", lazy="selectin")
