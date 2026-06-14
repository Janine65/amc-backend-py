"""Schemas for the ``fiscalyear`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FiscalyearBase(BaseModel):
    name: str | None = None
    state: int | None = None
    year: int | None = None


class FiscalyearCreate(FiscalyearBase):
    pass


class FiscalyearUpdate(FiscalyearBase):
    pass


class FiscalyearEntity(FiscalyearBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
