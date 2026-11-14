"""``besucher_zaehler`` table (Besucherzähler der Homepage, eine Zeile)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BesucherZaehler(Base):
    __tablename__ = "besucher_zaehler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zaehler: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class BesucherSitzung(Base):
    __tablename__ = "besucher_sitzung"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    duration_observed: Mapped[bool] = mapped_column(Boolean, default=False)
    country: Mapped[str | None] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(20))
    referrer_host: Mapped[str | None] = mapped_column(String(253))
    entry_path: Mapped[str] = mapped_column(String(100))
    device: Mapped[str] = mapped_column(String(20))
    browser: Mapped[str] = mapped_column(String(20))


class BesucherSeite(Base):
    __tablename__ = "besucher_seite"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("besucher_sitzung.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
