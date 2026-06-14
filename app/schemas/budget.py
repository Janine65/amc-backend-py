"""Schemas for the ``budget`` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.account import AccountEntity


class BudgetBase(BaseModel):
    account: int
    year: int
    memo: str | None = None
    amount: float | None = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    account: int | None = None
    year: int | None = None
    memo: str | None = None
    amount: float | None = None


class BudgetEntity(BudgetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    account_budget_accountToaccount: AccountEntity | None = None


class CopyBudgetYear(BaseModel):
    fromYear: int
    toYear: int
