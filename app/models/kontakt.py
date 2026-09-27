"""``kontakte`` table (Kontaktanfragen von der Homepage)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Kontakt(Base):
    __tablename__ = "kontakte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vorname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    betreff: Mapped[str] = mapped_column(String(200), nullable=False)
    nachricht: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
