from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class BesucherAufruf(BaseModel):
    session_id: UUID
    page_id: UUID
    path: str = Field(max_length=100)
    referrer: str | None = Field(default=None, max_length=2048)
    client_ip: str | None = Field(default=None, max_length=45)
    user_agent: str = Field(default="", max_length=512)


class BesucherAktivitaet(BaseModel):
    session_id: UUID
    page_id: UUID


class BesucherGruppe(BaseModel):
    label: str
    count: int


class BesucherStatistik(BaseModel):
    von: date
    bis: date
    timezone: str = "Europe/Zurich"
    retention_days: int = 365
    visits: int
    pageviews: int
    measured_visits: int
    average_duration_seconds: float | None
    countries: list[BesucherGruppe]
    sources: list[BesucherGruppe]
    referrers: list[BesucherGruppe]
    weekdays: list[BesucherGruppe]
    hours: list[BesucherGruppe]
    days: list[BesucherGruppe]
    durations: list[BesucherGruppe]
    pages: list[BesucherGruppe]
    entry_pages: list[BesucherGruppe]
    devices: list[BesucherGruppe]
    browsers: list[BesucherGruppe]
