"""``journal_receipt`` service + router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.journal_receipt import JournalReceipt
from app.schemas.journal_receipt import JournalReceiptCreate, JournalReceiptEntity
from app.schemas.receipt import ReceiptEntity
from app.schemas.ret_data import RetData

logger = get_logger(__name__)

router = APIRouter(prefix="/journal-receipt", tags=["JournalReceipt"])


@router.post("/add2journal", response_model=RetData[dict])
async def add2journal(
    journalid: int,
    receipts: list[ReceiptEntity],
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[dict]:
    for receipt in receipts:
        db.add(JournalReceipt(journalid=journalid, receiptid=receipt.id))
    await db.flush()
    return RetData(data={"count": len(receipts)}, message="JournalReceipt added")


@router.post("", response_model=RetData[JournalReceiptEntity], status_code=201)
async def create(
    body: JournalReceiptCreate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[JournalReceiptEntity]:
    obj = JournalReceipt(**body.model_dump())
    db.add(obj)
    await db.flush()
    return RetData(data=JournalReceiptEntity.model_validate(obj), message="JournalReceipt created")


@router.get("", response_model=RetData[list[JournalReceiptEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[JournalReceiptEntity]]:
    rows = (await db.execute(select(JournalReceipt))).scalars().all()
    return RetData(
        data=[JournalReceiptEntity.model_validate(r) for r in rows],
        message="JournalReceipts found",
    )


@router.get("/getbyjournalid", response_model=RetData[list[JournalReceiptEntity]])
async def get_by_journal(
    journalid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[JournalReceiptEntity]]:
    rows = (await db.execute(select(JournalReceipt).where(JournalReceipt.journalid == journalid))).scalars().all()
    return RetData(
        data=[JournalReceiptEntity.model_validate(r) for r in rows],
        message="JournalReceipt found",
    )


@router.get("/getbyreceiptid", response_model=RetData[list[JournalReceiptEntity]])
async def get_by_receipt(
    receiptid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[JournalReceiptEntity]]:
    rows = (await db.execute(select(JournalReceipt).where(JournalReceipt.receiptid == receiptid))).scalars().all()
    return RetData(
        data=[JournalReceiptEntity.model_validate(r) for r in rows],
        message="JournalReceipt found",
    )


@router.delete("", response_model=RetData[dict])
async def remove(
    journalid: int,
    receiptid: int,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[dict]:
    result = await db.execute(
        delete(JournalReceipt).where(and_(JournalReceipt.journalid == journalid, JournalReceipt.receiptid == receiptid))
    )
    await db.flush()
    return RetData(data={"count": result.rowcount or 0}, message="JournalReceipt removed")
