"""Schemas for the ``parameter`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParameterBase(BaseModel):
    key: str
    value: str


class ParameterCreate(ParameterBase):
    pass


class ParameterUpdate(BaseModel):
    key: str | None = None
    value: str | None = None


class ParameterEntity(ParameterBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
