"""``anlass_anmeldungen`` table (öffentliche Anmeldungen zu Anlässen)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.anlaesse import Anlaesse


class AnlassAnmeldung(Base):
    __tablename__ = "anlass_anmeldungen"
    __table_args__ = (UniqueConstraint("anlassid", "email", name="anmeldung_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anlassid: Mapped[int] = mapped_column(Integer, ForeignKey("anlaesse.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vorname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    bemerkung: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 1 = neu, 2 = bestätigt, 0 = abgelehnt
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    anlass: Mapped[Anlaesse] = relationship("Anlaesse", lazy="selectin")
