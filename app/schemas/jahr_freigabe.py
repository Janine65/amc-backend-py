"""Schemas for the ``jahr_freigabe`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JahrFreigabeUpsert(BaseModel):
    jahr: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    clubmeister: bool = False
    kegelmeister: bool = False


class JahrFreigabeEntity(JahrFreigabeUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
