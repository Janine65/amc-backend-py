"""``kegelkasse`` router."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_config
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.journal_receipt import JournalReceipt
from app.models.kegelkasse import Kegelkasse
from app.models.receipt import Receipt
from app.schemas.kegelkasse import KegelkasseCreate, KegelkasseEntity, KegelkasseUpdate
from app.schemas.ret_data import RetData, RetDataFile, RetDataFilePayload
from app.utils.general import (
    I_FONT_SIZE_HEADER,
    I_FONT_SIZE_TITEL,
    format_date_long,
    set_cell_value_format,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/kegelkasse", tags=["Kegelkasse"])

NUM_FMT = "#,##0.00;[Red]-#,##0.00"


@router.get("/kassebydatum", response_model=RetData[KegelkasseEntity | None])
async def kasse_by_datum(
    monat: int,
    jahr: int,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[KegelkasseEntity | None]:
    start = date_cls(jahr, monat, 1)
    end = date_cls(jahr if monat < 12 else jahr + 1, monat % 12 + 1, 1)
    row = await db.scalar(select(Kegelkasse).where(and_(Kegelkasse.datum >= start, Kegelkasse.datum < end)))
    return RetData(
        data=KegelkasseEntity.model_validate(row) if row else None,
        message="kasseByDatum",
    )


@router.get("/kassebyjahr", response_model=RetData[list[KegelkasseEntity]])
async def kasse_by_jahr(
    jahr: str, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[list[KegelkasseEntity]]:
    start = date_cls(int(jahr), 1, 1)
    end = date_cls(int(jahr) + 1, 1, 1)
    rows = (
        (
            await db.execute(
                select(Kegelkasse)
                .where(and_(Kegelkasse.datum >= start, Kegelkasse.datum < end))
                .order_by(Kegelkasse.datum.asc())
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[KegelkasseEntity.model_validate(r) for r in rows], message="kasseByJahr")


@router.get("/genreceipt", response_model=RetDataFile)
async def gen_receipt(
    kegelkasseId: int,  # noqa: N803
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetDataFile:
    cfg = get_config()
    kk = await db.scalar(select(Kegelkasse).where(Kegelkasse.id == kegelkasseId).options(selectinload(Kegelkasse.user)))
    if kk is None:
        return RetDataFile(data=None, type="error", message="Kegelkasse nicht gefunden")
    if not (kk.journalid and kk.journalid > 0):
        return RetDataFile(data=None, type="error", message="Journal nicht gefunden")

    kegel_date = kk.datum if isinstance(kk.datum, date_cls) else date_cls.fromisoformat(str(kk.datum))
    kegel_date_fmt = kegel_date.strftime("%d.%m.%Y")

    # ---------- Excel ----------
    wb = Workbook()
    wb.remove(wb.active)
    sheet = wb.create_sheet("Kegelkasse")
    for col in ("A", "B", "C"):
        sheet.column_dimensions[col].width = 17

    set_cell_value_format(
        sheet,
        "A1:C1",
        f"Kegelkasse {kegel_date_fmt}",
        merge=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_HEADER, bold=True),
    )
    for cell, hdr in (("A3", "Einheit"), ("B3", "Anzahl"), ("C3", "Total")):
        set_cell_value_format(
            sheet,
            cell,
            hdr,
            border=True,
            font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
        )

    denominations = [
        (0.05, kk.rappen5),
        (0.1, kk.rappen10),
        (0.2, kk.rappen20),
        (0.5, kk.rappen50),
        (1, kk.franken1),
        (2, kk.franken2),
        (5, kk.franken5),
        (10, kk.franken10),
        (20, kk.franken20),
        (50, kk.franken50),
        (100, kk.franken100),
    ]
    rows_pdf: list[list[str]] = []
    sum_total = 0.0
    row_no = 4
    for value, count in denominations:
        cnt = int(count or 0)
        total = float(value) * cnt
        sum_total += total
        font_r = Font(name="Tahoma", size=13)
        set_cell_value_format(sheet, f"A{row_no}", float(value), border=True, font=font_r)
        sheet[f"A{row_no}"].number_format = "#,##0.00"
        set_cell_value_format(sheet, f"B{row_no}", cnt, border=True, font=font_r)
        sheet[f"B{row_no}"].number_format = "#,##0"
        set_cell_value_format(sheet, f"C{row_no}", total, border=True, font=font_r)
        sheet[f"C{row_no}"].number_format = NUM_FMT
        rows_pdf.append([f"{value:.2f}", str(cnt), f"{total:.2f}"])
        row_no += 1

    row_no += 1
    set_cell_value_format(
        sheet,
        f"A{row_no}:B{row_no}",
        "Total",
        border=True,
        merge=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
    )
    set_cell_value_format(
        sheet,
        f"C{row_no}",
        sum_total,
        border=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
    )
    sheet[f"C{row_no}"].number_format = NUM_FMT
    rows_pdf.append(["Total", "", f"{sum_total:.2f}"])
    row_no += 2

    set_cell_value_format(
        sheet,
        f"A{row_no}:B{row_no}",
        "Kasse",
        border=True,
        merge=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
    )
    kasse_val = float(kk.kasse or 0)
    set_cell_value_format(
        sheet,
        f"C{row_no}",
        kasse_val,
        border=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
    )
    sheet[f"C{row_no}"].number_format = NUM_FMT
    rows_pdf.append(["Kasse", "", f"{kasse_val:.2f}"])
    row_no += 1

    diff_val = float(kk.differenz or 0)
    set_cell_value_format(
        sheet,
        f"A{row_no}:B{row_no}",
        "Differenz",
        border=True,
        merge=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True),
    )
    set_cell_value_format(
        sheet,
        f"C{row_no}",
        diff_val,
        border=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True, color="00CD143C"),
    )
    sheet[f"C{row_no}"].number_format = NUM_FMT
    rows_pdf.append(["Differenz", "", f"{diff_val:.2f}"])
    row_no += 2

    set_cell_value_format(
        sheet,
        f"A{row_no}:C{row_no}",
        f"Glattbrugg, den {format_date_long(kegel_date)}",
        merge=True,
        font=Font(name="Tahoma", size=I_FONT_SIZE_TITEL, italic=True),
    )

    Path(cfg.exports).mkdir(parents=True, exist_ok=True)
    filename = f"Kegelkasse-{kegel_date.isoformat()}.xlsx"
    wb.save(cfg.exports + filename)

    # ---------- PDF ----------
    filename_pdf = filename.replace(".xlsx", ".pdf")
    pdf_path = cfg.exports + filename_pdf
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>Kegelkasse {kegel_date_fmt}</b>", styles["Title"]),
        Spacer(1, 18),
    ]
    table = Table([["Einheit", "Anzahl", "Total"], *rows_pdf])
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 11),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 11),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story += [
        table,
        Spacer(1, 24),
        Paragraph(f"Glattbrugg, den {format_date_long(kegel_date)}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(
            f"<i>Kegelkasse erfasst durch {kk.user.name if kk.user else ''}</i>",
            styles["Normal"],
        ),
    ]
    doc.build(story)

    # PDF an Journal hängen
    year = kegel_date.year
    base_path = cfg.documents + f"{year}/"
    os.makedirs(base_path + "receipt", exist_ok=True)

    now = datetime.now(UTC)
    new_receipt = Receipt(
        receipt=f"receipt/{filename_pdf}",
        jahr=str(year),
        bezeichnung=f"Kegelkasse {kegel_date_fmt}",
        createdAt=now,
        updatedAt=now,
    )
    db.add(new_receipt)
    await db.flush()
    new_filename = f"receipt/journal-{new_receipt.id}.pdf"
    new_receipt.receipt = new_filename
    db.add(JournalReceipt(journalid=kk.journalid, receiptid=new_receipt.id))

    target = base_path + new_filename
    shutil.copyfile(pdf_path, target)
    try:
        os.chmod(target, 0o640)
    except OSError:
        logger.warning("chmod failed for %s", target, exc_info=True)

    return RetDataFile(data=RetDataFilePayload(filename=new_filename), message="genReceiptPDF")


# --------------------------------------------------------------------------- CRUD


@router.post("", response_model=RetData[KegelkasseEntity], status_code=201)
async def create(
    body: KegelkasseCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[KegelkasseEntity]:
    now = datetime.now(UTC)
    obj = Kegelkasse(**body.model_dump(), createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["journal", "user"])
    return RetData(data=KegelkasseEntity.model_validate(obj), message="create")


@router.get("", response_model=RetData[list[KegelkasseEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[KegelkasseEntity]]:
    rows = (await db.execute(select(Kegelkasse))).scalars().all()
    return RetData(data=[KegelkasseEntity.model_validate(r) for r in rows], message="findAll")


@router.get("/{kk_id}", response_model=RetData[KegelkasseEntity | None])
async def find_one(
    kk_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[KegelkasseEntity | None]:
    obj = await db.get(Kegelkasse, kk_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=KegelkasseEntity.model_validate(obj), message="findOne")


@router.patch("/{kk_id}", response_model=RetData[KegelkasseEntity])
async def update(
    kk_id: int,
    body: KegelkasseUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[KegelkasseEntity]:
    obj = await db.get(Kegelkasse, kk_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Kegelkasse nicht gefunden")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["journal", "user"])
    return RetData(data=KegelkasseEntity.model_validate(obj), message="update")


@router.delete("/{kk_id}", response_model=RetData[KegelkasseEntity])
async def remove(kk_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[KegelkasseEntity]:
    obj = await db.get(Kegelkasse, kk_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Kegelkasse nicht gefunden")
    await db.refresh(obj, ["journal", "user"])
    entity = KegelkasseEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="remove")
