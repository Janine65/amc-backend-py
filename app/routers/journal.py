"""``journal`` router (incl. Excel/PDF/Zip export)."""

from __future__ import annotations

import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_config, load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.journal import Journal
from app.models.journal_receipt import JournalReceipt
from app.schemas.journal import JournalCreate, JournalEntity, JournalUpdate
from app.schemas.ret_data import RetData, RetDataFile, RetDataFilePayload
from app.utils.general import (
    I_FONT_SIZE_HEADER,
    I_FONT_SIZE_ROW,
    I_FONT_SIZE_TITEL,
    set_cell_value_format,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/journal", tags=["Journal"])

NUM_FMT = "#,##0.00;[Red]-#,##0.00"


def _eager_options():
    return (
        selectinload(Journal.account_journal_from_accountToaccount),
        selectinload(Journal.account_journal_to_accountToaccount),
        selectinload(Journal.journal_receipt).selectinload(JournalReceipt.receipt),
    )


@router.post("", response_model=RetData[JournalEntity], status_code=201)
async def create(
    body: JournalCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[JournalEntity]:
    now = datetime.now(UTC)
    obj = Journal(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(
        obj,
        [
            "account_journal_from_accountToaccount",
            "account_journal_to_accountToaccount",
            "journal_receipt",
        ],
    )
    return RetData(data=JournalEntity.model_validate(obj), message="Journal created")


@router.get("", response_model=RetData[list[JournalEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[JournalEntity]]:
    params = await load_params()
    clubjahr = int(params.get("CLUBJAHR", "0") or 0)
    rows = (
        (
            await db.execute(
                select(Journal)
                .where(Journal.year == clubjahr)
                .options(*_eager_options())
                .order_by(Journal.journalno.asc(), Journal.date.asc(), Journal.from_account.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[JournalEntity.model_validate(r) for r in rows], message="Journal found")


@router.get("/getbyyear", response_model=RetData[list[JournalEntity]])
async def find_by_year(
    year: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[JournalEntity]]:
    rows = (
        (
            await db.execute(
                select(Journal)
                .where(Journal.year == year)
                .options(*_eager_options())
                .order_by(Journal.journalno.asc(), Journal.date.asc(), Journal.from_account.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[JournalEntity.model_validate(r) for r in rows], message="Journal found")


@router.get("/getaccdata", response_model=RetData[list[dict]])
async def find_by_account(
    account: int, year: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[dict]]:
    rows = (
        (
            await db.execute(
                select(Journal)
                .where(
                    and_(
                        Journal.year == year,
                        or_(Journal.from_account == account, Journal.to_account == account),
                    )
                )
                .options(*_eager_options())
                .order_by(Journal.journalno.asc(), Journal.date.asc(), Journal.from_account.asc())
            )
        )
        .scalars()
        .all()
    )
    out: list[dict] = []
    for j in rows:
        from_acc = j.account_journal_from_accountToaccount
        to_acc = j.account_journal_to_accountToaccount
        rec = {
            "id": j.id,
            "journalno": j.journalno,
            "date": j.date.isoformat() if j.date else None,
            "memo": j.memo or "",
            "fromAcc": (to_acc.longname if to_acc else None) or (to_acc.name if to_acc else None),
            "toAcc": (from_acc.longname if from_acc else None) or (from_acc.name if from_acc else None),
            "haben": float(j.amount or 0) if j.to_account == account else 0.0,
            "soll": float(j.amount or 0) if j.to_account != account else 0.0,
        }
        out.append(rec)
    return RetData(data=out, message="Journal found")


def _format_date_ch(d: date) -> str:
    return d.strftime("%d.%m.%Y")


@router.get("/write", response_model=RetDataFile)
async def write_journal(
    year: int,
    receipt: int = 0,
    _: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RetDataFile:
    cfg = get_config()
    rows = (
        (
            await db.execute(
                select(Journal)
                .where(Journal.year == year)
                .options(*_eager_options())
                .order_by(Journal.journalno.asc(), Journal.date.asc(), Journal.from_account.asc())
            )
        )
        .scalars()
        .all()
    )

    # ---------- Excel ----------
    wb = Workbook()
    wb.remove(wb.active)
    sheet = wb.create_sheet("Journal")

    set_cell_value_format(
        sheet,
        "B1",
        f"Journal {year}",
        font=Font(name="Tahoma", size=I_FONT_SIZE_HEADER, bold=True),
    )
    headers = [
        ("B3", "No"),
        ("C3", "Date"),
        ("D3", "From "),
        ("E3", "To "),
        ("F3", "Booking Text "),
        ("G3", "Amount"),
        ("H3", "Receipt"),
    ]
    for cell, text in headers:
        set_cell_value_format(
            sheet,
            cell,
            text,
            border=True,
            font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
            align_v="top",
            align_h="right" if cell.startswith("G") else "left",
        )

    pdf_rows: list[list[str]] = []
    row = 4
    for j in rows:
        d_str = _format_date_ch(j.date) if j.date else ""
        amt = float(j.amount or 0)
        from_acc = j.account_journal_from_accountToaccount
        to_acc = j.account_journal_to_accountToaccount
        from_str = f"{from_acc.order} {from_acc.name}" if from_acc else ""
        to_str = f"{to_acc.order} {to_acc.name}" if to_acc else ""
        link_addr = "\r\n".join(f"{r.receipt.bezeichnung}: {r.receipt.receipt}" for r in j.journal_receipt)
        for col, v in (
            ("B", j.journalno or 0),
            ("C", d_str),
            ("D", from_str),
            ("E", to_str),
            ("F", j.memo or ""),
            ("G", amt),
            ("H", link_addr),
        ):
            set_cell_value_format(
                sheet,
                f"{col}{row}",
                v,
                border=True,
                font=Font(name="Tahoma", size=I_FONT_SIZE_ROW),
                align_v="top",
            )
        sheet[f"G{row}"].number_format = NUM_FMT
        sheet[f"H{row}"].alignment = Alignment(vertical="top", wrap_text=True)

        pdf_rows.append(
            [
                f"{j.journalno or 0}",
                d_str,
                f"{from_acc.order if from_acc else 0}",
                f"{to_acc.order if to_acc else 0}",
                j.memo or "",
                f"{amt:.2f}",
                link_addr,
            ]
        )
        row += 1

    for col, w in [("B", 8), ("C", 18), ("D", 35), ("E", 35), ("F", 50), ("G", 18), ("H", 75)]:
        sheet.column_dimensions[col].width = w

    Path(cfg.exports).mkdir(parents=True, exist_ok=True)
    filename = f"Journal-{year}"
    wb.save(cfg.exports + filename + ".xlsx")

    if not receipt:
        return RetDataFile(data=RetDataFilePayload(filename=filename + ".xlsx"), message="Datei erstellt")

    # ---------- PDF (reportlab) ----------
    pdf_path = cfg.exports + filename + ".pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>Journal {year}</b>", styles["Title"]), Spacer(1, 12)]
    table_data: list[list[str]] = [["No.", "Date", "From", "To", "Booking Text", "Amount", "Receipt"]]
    table_data.extend(pdf_rows)
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                ("ALIGN", (5, 1), (5, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(table)
    doc.build(story)

    # ---------- Zip ----------
    zip_path = cfg.exports + filename + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if Path(pdf_path).exists():
            zf.write(pdf_path, arcname=filename + ".pdf")
        receipt_dir = Path(cfg.documents + str(year) + "/receipt")
        if receipt_dir.exists():
            for fp in receipt_dir.rglob("*"):
                if fp.is_file():
                    zf.write(fp, arcname=f"receipt/{fp.name}")

    return RetDataFile(data=RetDataFilePayload(filename=filename + ".zip"), message="Datei erstellt")


@router.get("/{j_id}", response_model=RetData[JournalEntity])
async def find_one(j_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[JournalEntity]:
    obj = await db.scalar(select(Journal).where(Journal.id == j_id).options(*_eager_options()))
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=JournalEntity.model_validate(obj), message="Journal found")


@router.patch("/{j_id}", response_model=RetData[JournalEntity])
async def update(
    j_id: int,
    body: JournalUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[JournalEntity]:
    obj = await db.get(Journal, j_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Journal not updated")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(
        obj,
        [
            "account_journal_from_accountToaccount",
            "account_journal_to_accountToaccount",
            "journal_receipt",
        ],
    )
    return RetData(data=JournalEntity.model_validate(obj), message="Journal updated")


@router.delete("/{j_id}", response_model=RetData[JournalEntity])
async def remove(j_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[JournalEntity]:
    obj = await db.get(Journal, j_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Journal not deleted")
    await db.refresh(
        obj,
        [
            "account_journal_from_accountToaccount",
            "account_journal_to_accountToaccount",
            "journal_receipt",
        ],
    )
    entity = JournalEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Journal deleted")
