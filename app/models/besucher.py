"""``besucher_zaehler`` table (Besucherzähler der Homepage, eine Zeile)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BesucherZaehler(Base):
    __tablename__ = "besucher_zaehler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zaehler: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
