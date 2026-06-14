"""``adressen`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.clubmeister import Clubmeister
    from app.models.kegelmeister import Kegelmeister
    from app.models.meisterschaft import Meisterschaft


class Adressen(Base):
    __tablename__ = "adressen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mnr: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    geschlecht: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vorname: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse: Mapped[str] = mapped_column(String(255), nullable=False)
    plz: Mapped[int] = mapped_column(Integer, nullable=False)
    ort: Mapped[str] = mapped_column(String(255), nullable=False)
    land: Mapped[str] = mapped_column(String(45), default="CH", nullable=False)
    telefon_p: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telefon_g: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    eintritt: Mapped[date | None] = mapped_column(Date, nullable=True)
    sam_mitglied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    jahresbeitrag: Mapped[float | None] = mapped_column(Float, nullable=True)
    mnr_sam: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    vorstand: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ehrenmitglied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    veteran1: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    veteran2: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revisor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    motojournal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    austritt: Mapped[date | None] = mapped_column(Date, nullable=True)
    austritt_mail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adressenid: Mapped[int | None] = mapped_column(Integer, ForeignKey("adressen.id"), nullable=True)
    jahrgang: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arbeitgeber: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pensioniert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allianz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    fullname: Mapped[str | None] = mapped_column(String(250), nullable=True)

    # self-referential
    adressen: Mapped[Adressen | None] = relationship(
        "Adressen",
        remote_side=[id],
        back_populates="other_adressen",
        foreign_keys=[adressenid],
        lazy="selectin",
        join_depth=1,
    )
    other_adressen: Mapped[list[Adressen]] = relationship(
        "Adressen",
        back_populates="adressen",
        foreign_keys=[adressenid],
        lazy="selectin",
        join_depth=1,
    )
    clubmeister: Mapped[list[Clubmeister]] = relationship(
        "Clubmeister", back_populates="adressen", lazy="selectin", join_depth=1
    )
    kegelmeister: Mapped[list[Kegelmeister]] = relationship(
        "Kegelmeister", back_populates="adressen", lazy="selectin", join_depth=1
    )
    meisterschaft: Mapped[list[Meisterschaft]] = relationship(
        "Meisterschaft", back_populates="adressen", lazy="selectin", join_depth=1
    )
