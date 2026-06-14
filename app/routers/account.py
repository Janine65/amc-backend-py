"""``account`` router."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.account import Account
from app.models.budget import Budget
from app.models.journal import Journal
from app.schemas.account import AccountCreate, AccountEntity, AccountUpdate
from app.schemas.ret_data import RetData, RetDataFile, RetDataFilePayload
from app.utils.general import (
    I_FONT_SIZE_HEADER,
    I_FONT_SIZE_ROW,
    I_FONT_SIZE_TITEL,
    set_cell_value_format,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])

NUM_FMT = "#,##0.00;[Red]-#,##0.00"


async def _get_account_jahr(db: AsyncSession, jahr: int, all_: int) -> list[Account]:
    if all_ == 0:
        sub_a = select(Journal.from_account).where(Journal.year == jahr)
        sub_b = select(Journal.to_account).where(Journal.year == jahr)
        stmt = (
            select(Account)
            .where(or_(Account.id.in_(sub_a), Account.id.in_(sub_b)))
            .order_by(Account.level.asc(), Account.order.asc())
        )
    else:
        stmt = select(Account).where(Account.order > 10).order_by(Account.level.asc(), Account.order.asc())
    return list((await db.execute(stmt)).scalars().all())


@router.get("/getaccjahr", response_model=RetData[list[AccountEntity]])
async def get_account_jahr(
    jahr: int, all: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[AccountEntity]]:
    rows = await _get_account_jahr(db, jahr, all)
    return RetData(data=[AccountEntity.model_validate(r) for r in rows], message="Account Jahr")


@router.get("/getonedatabyorder", response_model=RetData[AccountEntity | None])
async def get_one_by_order(
    order: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AccountEntity | None]:
    row = await db.scalar(select(Account).where(Account.order == order))
    if row is None:
        raise HTTPException(status_code=404, detail="Account not created")
    return RetData(data=AccountEntity.model_validate(row), message="Account by order")


@router.get("/getamountoneacc", response_model=RetData[dict])
async def get_amount_one_acc(
    order: int, date: date_cls, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[dict]:
    acc = await db.scalar(select(Account).where(Account.order == order))
    if acc is None:
        return RetData(data={"id": None, "amount": "0.00"}, message="Amount one account")
    amt_a = (
        await db.scalar(
            select(func.sum(Journal.amount)).where(
                and_(Journal.year == date.year, Journal.date <= date, Journal.from_account == acc.id)
            )
        )
        or 0
    )
    amt_b = (
        await db.scalar(
            select(func.sum(Journal.amount)).where(
                and_(Journal.year == date.year, Journal.date <= date, Journal.to_account == acc.id)
            )
        )
        or 0
    )
    diff = float(amt_a) - float(amt_b)
    return RetData(data={"id": acc.id, "amount": f"{diff:.2f}"}, message="Amount one account")


@router.get("/getfkdata", response_model=RetData[list[dict]])
async def get_fk_data(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[dict]]:
    rows = (
        (
            await db.execute(
                select(Account).where(Account.order >= 10).order_by(Account.level.asc(), Account.order.asc())
            )
        )
        .scalars()
        .all()
    )
    out = [{"id": a.id, "value": a.longname or f"{a.order} {a.name}"} for a in rows]
    return RetData(data=out, message="FK Data")


@router.get("/getaccountsummary", response_model=RetData[list[dict]])
async def get_account_summary(
    jahr: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[dict]]:
    rows = (
        (
            await db.execute(
                select(Account).where(Account.order >= 10).order_by(Account.level.asc(), Account.order.asc())
            )
        )
        .scalars()
        .all()
    )
    out: list[dict] = []
    for a in rows:
        budget_amt = (
            await db.scalar(select(func.sum(Budget.amount)).where(and_(Budget.year == jahr, Budget.account == a.id)))
            or 0
        )
        amt_a = (
            await db.scalar(
                select(func.sum(Journal.amount)).where(and_(Journal.year == jahr, Journal.from_account == a.id))
            )
            or 0
        )
        amt_b = (
            await db.scalar(
                select(func.sum(Journal.amount)).where(and_(Journal.year == jahr, Journal.to_account == a.id))
            )
            or 0
        )
        amt_a, amt_b, budget_amt = float(amt_a), float(amt_b), float(budget_amt)
        if a.level in (1, 4):
            amount = amt_a - amt_b
            diff = amount - budget_amt
        else:
            amount = amt_b - amt_a
            diff = budget_amt - amount
        if amount != 0 or budget_amt != 0 or (a.status or 0) != 0:
            out.append(
                {
                    "id": a.id,
                    "level": a.level,
                    "order": a.order,
                    "name": a.longname or f"{a.order} {a.name}",
                    "status": a.status or 0,
                    "amount": amount,
                    "budget": budget_amt,
                    "diff": diff,
                    "$css": "active" if a.status else "inactive",
                }
            )
    return RetData(data=out, message="Account Summary")


@router.get("/writekontoauszug", response_model=RetDataFile)
async def write_kontoauszug(
    year: int,
    all: bool = False,
    _: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RetDataFile:
    cfg = get_config()
    wb = Workbook()
    wb.remove(wb.active)
    accounts = await _get_account_jahr(db, year, 1 if all else 0)

    for acc in accounts:
        journals = (
            (
                await db.execute(
                    select(Journal)
                    .where(
                        and_(
                            Journal.year == year,
                            or_(Journal.from_account == acc.id, Journal.to_account == acc.id),
                        )
                    )
                    .order_by(Journal.date.asc())
                )
            )
            .scalars()
            .all()
        )

        sheet_name = f"{acc.order} {(acc.name or '').replace('/', '')}"[:31]
        sheet = wb.create_sheet(sheet_name)
        set_cell_value_format(
            sheet,
            "B1",
            f"{acc.order} {acc.name}",
            font=Font(name="Tahoma", size=I_FONT_SIZE_HEADER, bold=True),
        )
        for cell, hdr in (
            ("B3", "No."),
            ("C3", "Datum"),
            ("D3", "Gegenkonto"),
            ("E3", "Text "),
            ("F3", "Soll "),
            ("G3", "Haben"),
            ("H3", "Saldo"),
        ):
            set_cell_value_format(
                sheet,
                cell,
                hdr,
                border=True,
                font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
                align_h="right" if cell.startswith(("F", "G", "H")) else "left",
            )

        for col, w in [("B", 12), ("C", 12), ("D", 35), ("E", 55), ("F", 12), ("G", 12), ("H", 12)]:
            sheet.column_dimensions[col].width = w

        i_saldo = 0.0
        row = 4
        font_row = Font(name="Tahoma", size=I_FONT_SIZE_ROW)
        for j in journals:
            i_amount = float(j.amount or 0)
            set_cell_value_format(sheet, f"B{row}", j.journalno or 0, border=True, font=font_row)
            set_cell_value_format(sheet, f"C{row}", j.date, border=True, font=font_row)
            set_cell_value_format(sheet, f"E{row}", j.memo or "", border=True, font=font_row)
            for col in ("F", "G", "H"):
                sheet[f"{col}{row}"].number_format = NUM_FMT

            if j.from_account == acc.id:
                gegen = next((a for a in accounts if a.id == j.to_account), None)
                gegen_str = f"{gegen.order} {gegen.name}" if gegen else (j.to_account or "")
                set_cell_value_format(sheet, f"D{row}", gegen_str, border=True, font=font_row)
                set_cell_value_format(sheet, f"F{row}", i_amount, border=True, font=font_row)
                set_cell_value_format(sheet, f"G{row}", "", border=True, font=font_row)
                if (acc.level or 0) in (2, 6):
                    i_saldo -= i_amount
                else:
                    i_saldo += i_amount
            else:
                gegen = next((a for a in accounts if a.id == j.from_account), None)
                gegen_str = f"{gegen.order} {gegen.name}" if gegen else (j.from_account or "")
                set_cell_value_format(sheet, f"D{row}", gegen_str, border=True, font=font_row)
                set_cell_value_format(sheet, f"F{row}", "", border=True, font=font_row)
                set_cell_value_format(sheet, f"G{row}", i_amount, border=True, font=font_row)
                if (acc.level or 0) in (2, 6):
                    i_saldo += i_amount
                else:
                    i_saldo -= i_amount
            sheet[f"F{row}"].number_format = NUM_FMT
            sheet[f"G{row}"].number_format = NUM_FMT
            set_cell_value_format(sheet, f"H{row}", i_saldo, border=True, font=font_row)
            sheet[f"H{row}"].number_format = NUM_FMT
            row += 1

    filename = f"Kontoauszug-{year}.xlsx"
    Path(cfg.exports).mkdir(parents=True, exist_ok=True)
    wb.save(cfg.exports + filename)
    return RetDataFile(data=RetDataFilePayload(filename=filename), message="Kontoauszug erstellt")


# --------------------------------------------------------------------------- CRUD


@router.post("", response_model=RetData[AccountEntity], status_code=201)
async def create(
    body: AccountCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AccountEntity]:
    now = datetime.now(UTC)
    obj = Account(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    return RetData(data=AccountEntity.model_validate(obj), message="Account created")


@router.get("", response_model=RetData[list[AccountEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[AccountEntity]]:
    rows = (await db.execute(select(Account).order_by(Account.level.asc(), Account.order.asc()))).scalars().all()
    return RetData(data=[AccountEntity.model_validate(r) for r in rows], message="Account found")


@router.get("/{acc_id}", response_model=RetData[AccountEntity])
async def find_one(acc_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[AccountEntity]:
    obj = await db.get(Account, acc_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return RetData(data=AccountEntity.model_validate(obj), message="Account found")


@router.patch("/{acc_id}", response_model=RetData[AccountEntity])
async def update(
    acc_id: int,
    body: AccountUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[AccountEntity]:
    obj = await db.get(Account, acc_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Account not updated")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    return RetData(data=AccountEntity.model_validate(obj), message="Account updated")


@router.delete("/{acc_id}", response_model=RetData[AccountEntity])
async def remove(acc_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[AccountEntity]:
    obj = await db.get(Account, acc_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Account not deleted")
    entity = AccountEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Account deleted")
