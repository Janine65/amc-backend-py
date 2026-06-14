"""``sessions`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sid: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    userid: Mapped[str | None] = mapped_column(String(45), ForeignKey("user.userid"), nullable=True)
    expires: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    data: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    user: Mapped[User | None] = relationship("User", back_populates="sessions")
