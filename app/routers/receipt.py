"""``receipt`` router."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_config
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.journal_receipt import JournalReceipt
from app.models.receipt import Receipt
from app.schemas.receipt import ReceiptEntity, ReceiptUpdate
from app.schemas.ret_data import (
    RetData,
    RetDataFiles,
    RetDataFilesPayload,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/receipt", tags=["Receipt"])


class UploadFiles(BaseModel):
    year: str
    uploadfiles: str
    journalId: int | None = Field(default=None, alias="journalId")

    model_config = {"populate_by_name": True}


def _ensure_year_path(year: str) -> str:
    cfg = get_config()
    base = cfg.documents + year + "/"
    os.makedirs(base + "receipt", exist_ok=True)
    return base


@router.post("", response_model=RetDataFiles)
async def create(data: UploadFiles, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetDataFiles:
    cfg = get_config()
    base = _ensure_year_path(data.year)
    payload: list[str] = []
    msg = ""
    typ = "info"
    now = datetime.now(UTC)
    for upload in data.uploadfiles.split(","):
        if not upload:
            continue
        src = cfg.uploads + upload
        if not os.path.exists(src):
            msg += f"Error while reading the file {upload}; "
            typ = "error"
            continue
        rec = Receipt(
            receipt=f"receipt/{upload}",
            jahr=data.year,
            bezeichnung=upload,
            createdAt=now,
            updatedAt=now,
        )
        db.add(rec)
        await db.flush()
        new_filename = f"receipt/journal-{rec.id}.pdf"
        rec.receipt = new_filename
        target = base + new_filename
        shutil.copyfile(src, target)
        try:
            os.chmod(target, 0o640)
        except OSError:
            logger.warning("chmod failed for %s", target, exc_info=True)
        payload.append(new_filename)
    return RetDataFiles(data=RetDataFilesPayload(files=payload), type=typ, message=msg)


@router.get("/findallatt", response_model=RetData[list[ReceiptEntity]])
async def find_all_attachments(
    jahr: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    journalId: str | None = None,  # noqa: N803
) -> RetData[list[ReceiptEntity]]:
    stmt = (
        select(Receipt)
        .where(Receipt.jahr == jahr)
        .options(selectinload(Receipt.journal_receipt))
        .order_by(Receipt.bezeichnung.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    if journalId is None:
        rows = [r for r in rows if r.journal_receipt]
    else:
        jid = int(journalId)
        rows = [r for r in rows if any(jr.journalid == jid for jr in r.journal_receipt)]
    return RetData(data=[ReceiptEntity.model_validate(r) for r in rows], message="findAllAttachments")


@router.get("/findatt", response_model=RetData[list[ReceiptEntity]])
async def find_attachments(
    journalid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[ReceiptEntity]]:
    rows = (
        (
            await db.execute(
                select(Receipt)
                .join(JournalReceipt, Receipt.id == JournalReceipt.receiptid)
                .where(JournalReceipt.journalid == journalid)
                .options(selectinload(Receipt.journal_receipt))
                .order_by(Receipt.bezeichnung.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[ReceiptEntity.model_validate(r) for r in rows], message="findAttachments")


@router.get("/uploadatt")
async def upload_att(filename: str, year: str, _: CurrentUser) -> FileResponse:
    cfg = get_config()
    file_path = Path(cfg.documents) / year / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.post("/att2journal", response_model=RetDataFiles)
async def add_attachment_to_journal(
    data: UploadFiles, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetDataFiles:
    if not data.uploadfiles:
        return RetDataFiles(data=RetDataFilesPayload(files=[]), type="info", message="No files to add")
    if data.journalId is None:
        raise HTTPException(status_code=400, detail="journalId required")

    cfg = get_config()
    base = _ensure_year_path(data.year)
    payload: list[str] = []
    msg = ""
    typ = "info"
    now = datetime.now(UTC)

    for upload in data.uploadfiles.split(","):
        if not upload:
            continue
        src = cfg.uploads + upload
        if not os.path.exists(src):
            msg += f"Error while reading the file {upload}; "
            typ = "error"
            continue
        rec = Receipt(
            receipt=f"receipt/{upload}",
            jahr=data.year,
            bezeichnung=upload,
            createdAt=now,
            updatedAt=now,
        )
        db.add(rec)
        await db.flush()
        new_filename = f"receipt/journal-{rec.id}.pdf"
        rec.receipt = new_filename
        db.add(JournalReceipt(journalid=data.journalId, receiptid=rec.id))
        target = base + new_filename
        shutil.copyfile(src, target)
        try:
            os.chmod(target, 0o640)
        except OSError:
            logger.warning("chmod failed for %s", target, exc_info=True)
        payload.append(new_filename)

    return RetDataFiles(data=RetDataFilesPayload(files=payload), type=typ, message=msg)


@router.get("", response_model=RetData[list[ReceiptEntity]])
async def find_all(
    year: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[ReceiptEntity]]:
    cfg = get_config()
    rows = (
        (
            await db.execute(
                select(Receipt)
                .where(Receipt.jahr == year)
                .options(selectinload(Receipt.journal_receipt))
                .order_by(Receipt.bezeichnung.asc())
            )
        )
        .scalars()
        .all()
    )
    pathname = cfg.documents + year + "/"
    os.makedirs(cfg.uploads + "receipt/", exist_ok=True)
    out: list[ReceiptEntity] = []
    for r in rows:
        src = pathname + (r.receipt or "")
        if os.path.exists(src):
            try:
                shutil.copyfile(src, cfg.uploads + (r.receipt or ""))
            except OSError:
                logger.warning("Could not copy receipt %s -> %s", src, cfg.uploads, exc_info=True)
                r.receipt = f"File not found: {r.receipt}"
        else:
            r.receipt = f"File not found: {r.receipt}"
        out.append(ReceiptEntity.model_validate(r))
    return RetData(data=out, message="findAll")


@router.get("/{rec_id}", response_model=RetData[ReceiptEntity | None])
async def find_one(
    rec_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[ReceiptEntity | None]:
    obj = await db.get(Receipt, rec_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=ReceiptEntity.model_validate(obj), message="findOne")


@router.patch("/{rec_id}", response_model=RetData[ReceiptEntity])
async def update(
    rec_id: int,
    body: ReceiptUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[ReceiptEntity]:
    obj = await db.get(Receipt, rec_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["journal_receipt"])
    return RetData(data=ReceiptEntity.model_validate(obj), message="update")


@router.delete("/{rec_id}", response_model=RetData[ReceiptEntity])
async def remove(rec_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[ReceiptEntity]:
    obj = await db.get(Receipt, rec_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    await db.refresh(obj, ["journal_receipt"])
    entity = ReceiptEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="remove")
