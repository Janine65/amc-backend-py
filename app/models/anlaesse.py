"""``anlaesse`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.meisterschaft import Meisterschaft


class Anlaesse(Base):
    __tablename__ = "anlaesse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    beschreibung: Mapped[str | None] = mapped_column(String(100), nullable=True)
    punkte: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    istkegeln: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    istsamanlass: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nachkegeln: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gaeste: Mapped[int | None] = mapped_column(SmallInteger, default=0, nullable=True)
    anlaesseid: Mapped[int | None] = mapped_column(Integer, ForeignKey("anlaesse.id"), nullable=True)
    createdAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updatedAt: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    longname: Mapped[str] = mapped_column(String(250), nullable=False)

    # self-referential
    anlaesse: Mapped[Anlaesse | None] = relationship(
        "Anlaesse",
        remote_side=[id],
        back_populates="other_anlaesse",
        foreign_keys=[anlaesseid],
        lazy="selectin",
        join_depth=1,
    )
    other_anlaesse: Mapped[list[Anlaesse]] = relationship(
        "Anlaesse", back_populates="anlaesse", foreign_keys=[anlaesseid]
    )
    meisterschaft: Mapped[list[Meisterschaft]] = relationship(
        "Meisterschaft", back_populates="anlaesse", lazy="selectin", join_depth=1
    )
