"""``meisterschaft`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.adressen import Adressen
    from app.models.anlaesse import Anlaesse


class Meisterschaft(Base):
    __tablename__ = "meisterschaft"
    __table_args__ = (UniqueConstraint("mitgliedid", "eventid", name="eventmitglied"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mitgliedid: Mapped[int] = mapped_column(Integer, ForeignKey("adressen.id"), default=0, nullable=False)
    eventid: Mapped[int] = mapped_column(Integer, ForeignKey("anlaesse.id"), default=0, nullable=False)
    punkte: Mapped[int | None] = mapped_column(SmallInteger, default=50, nullable=True)
    wurf1: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    wurf2: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    wurf3: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    wurf4: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    wurf5: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    zusatz: Mapped[int | None] = mapped_column(Integer, default=5, nullable=True)
    streichresultat: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    total_kegel: Mapped[int | None] = mapped_column(Integer, nullable=True)

    anlaesse: Mapped[Anlaesse] = relationship("Anlaesse", back_populates="meisterschaft", lazy="selectin", join_depth=1)
    adressen: Mapped[Adressen] = relationship("Adressen", back_populates="meisterschaft", lazy="selectin", join_depth=1)


class MeisterAdresse(BaseModel):
    jahr: int
    rangC: int | None = None
    punkteC: int | None = None
    anlaesseC: int | None = None
    werbungenC: int | None = None
    mitglieddauerC: int | None = None
    statusC: int | None = 0
    diffErsterC: int | None = None
    rangK: int | None = None
    punkteK: int | None = None
    anlaesseK: int | None = None
    babeliK: int | None = None
    statusK: int | None = 0
    diffErsterK: int | None = None
