"""``news`` table (Homepage-News)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titel: Mapped[str] = mapped_column(String(150), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    bild: Mapped[str | None] = mapped_column(String(255), nullable=True)
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    publiziert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
