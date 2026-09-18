"""``jahr_freigabe`` table (Freigabe der Meisterschafts-Jahre für die Homepage)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JahrFreigabe(Base):
    __tablename__ = "jahr_freigabe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jahr: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    clubmeister: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kegelmeister: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
