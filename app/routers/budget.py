"""``budget`` service + router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.account import Account
from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetEntity, BudgetUpdate
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/budget", tags=["Budget"])


@router.put("/copyyear", response_model=RetData[list[BudgetEntity]])
async def copy_year(
    from_: Annotated[int, "year"],
    to: int,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[list[BudgetEntity]]:
    """``PUT /budget/copyyear?from=YYYY&to=YYYY`` (alias ``from`` is reserved)."""
    raise HTTPException(status_code=501, detail="use the canonical /budget/copy endpoint")


@router.put("/copy", response_model=RetData[list[BudgetEntity]])
async def copy_year_q(
    fromYear: int,
    toYear: int,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[list[BudgetEntity]]:
    """Same logic as NestJS ``budget/copyyear?from=&to=`` (renamed query keys to avoid Python keyword)."""
    rows = (await db.execute(select(Budget).where(Budget.year == fromYear))).scalars().all()
    now = datetime.now(UTC)
    for src in rows:
        db.add(
            Budget(
                account=src.account,
                year=toYear,
                memo=src.memo,
                amount=src.amount,
                createdAt=now,
                updatedAt=now,
            )
        )
    await db.flush()
    items = (
        (
            await db.execute(
                select(Budget)
                .where(Budget.year == toYear)
                .options(selectinload(Budget.account_budget_accountToaccount))
                .order_by(Account.order.asc())
                .join(Account, Account.id == Budget.account)
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[BudgetEntity.model_validate(b) for b in items], message="Budgets copied")


@router.post("", response_model=RetData[BudgetEntity], status_code=201)
async def create(
    body: BudgetCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[BudgetEntity]:
    now = datetime.now(UTC)
    obj = Budget(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["account_budget_accountToaccount"])
    return RetData(data=BudgetEntity.model_validate(obj), message="Budget created")


@router.get("", response_model=RetData[list[BudgetEntity]])
async def find_all(
    year: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[BudgetEntity]]:
    items = (
        (
            await db.execute(
                select(Budget)
                .where(Budget.year == year)
                .options(selectinload(Budget.account_budget_accountToaccount))
                .join(Account, Account.id == Budget.account)
                .order_by(Account.order.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[BudgetEntity.model_validate(b) for b in items], message="Budgets found")


@router.get("/{budget_id}", response_model=RetData[BudgetEntity])
async def find_one(
    budget_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[BudgetEntity]:
    obj = await db.scalar(
        select(Budget).where(Budget.id == budget_id).options(selectinload(Budget.account_budget_accountToaccount))
    )
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=BudgetEntity.model_validate(obj), message="Budget found")


@router.patch("/{budget_id}", response_model=RetData[BudgetEntity])
async def update(
    budget_id: int,
    body: BudgetUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[BudgetEntity]:
    obj = await db.get(Budget, budget_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["account_budget_accountToaccount"])
    return RetData(data=BudgetEntity.model_validate(obj), message="Budget updated")


@router.delete("/{budget_id}", response_model=RetData[BudgetEntity])
async def remove(budget_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[BudgetEntity]:
    obj = await db.get(Budget, budget_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.refresh(obj, ["account_budget_accountToaccount"])
    entity = BudgetEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Budget removed")
