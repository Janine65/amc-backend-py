"""``user`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.kegelkasse import Kegelkasse
    from app.models.sessions import Sessions


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userid: Mapped[str | None] = mapped_column(String(45), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    email: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    salt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="user", nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    kegelkasse: Mapped[list[Kegelkasse]] = relationship("Kegelkasse", back_populates="user")
    sessions: Mapped[list[Sessions]] = relationship("Sessions", back_populates="user")
