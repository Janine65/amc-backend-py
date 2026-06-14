"""``adressen`` router (CRUD + Excel export + Email + QR-Bill)."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from pydantic import BaseModel
from qrbill import QRBill
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from svglib.svglib import svg2rlg

from app.core.config import get_config, load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.adressen import Adressen
from app.models.journal import Journal
from app.models.journal_receipt import JournalReceipt
from app.models.receipt import Receipt
from app.schemas.adressen import AdressenCreate, AdressenEntity, AdressenUpdate
from app.schemas.ret_data import RetData, RetDataFile, RetDataFilePayload
from app.utils.general import I_FONT_SIZE_ROW, I_FONT_SIZE_TITEL, set_cell_value_format
from app.utils.mail import send_mail

logger = get_logger(__name__)

router = APIRouter(prefix="/adressen", tags=["Adressen"])


class EmailBody(BaseModel):
    email_an: str | None = None
    email_cc: str | None = None
    email_bcc: str | None = None
    email_subject: str
    email_body: str
    email_uploadfiles: str | None = None
    email_signature: str | None = None


# ---------------------------------------------------------------------------
# overview / fk-data / list
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=RetData[list[dict]])
async def get_overview(db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[dict]]:
    today = date_cls.today()
    aktiv = await db.scalar(select(func.count(Adressen.id)).where(Adressen.austritt >= today))
    sam = await db.scalar(
        select(func.count(Adressen.id)).where(Adressen.austritt >= today, Adressen.sam_mitglied.is_(True))
    )
    nosam = await db.scalar(
        select(func.count(Adressen.id)).where(Adressen.austritt >= today, Adressen.sam_mitglied.is_(False))
    )
    return RetData(
        data=[
            {"label": "Aktive Mitglieder", "value": int(aktiv or 0)},
            {"label": "SAM Mitglieder", "value": int(sam or 0)},
            {"label": "Freimitglieder", "value": int(nosam or 0)},
        ],
        message="Adressen Overview",
    )


@router.get("/getFkData", response_model=RetData[list[dict]])
async def get_fk_data(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[dict]]:
    today = date_cls.today()
    rows = (
        await db.execute(
            select(Adressen.id, Adressen.fullname).where(Adressen.austritt >= today).order_by(asc(Adressen.fullname))
        )
    ).all()
    return RetData(data=[{"id": r[0], "value": r[1] or ""} for r in rows], message="FK Data")


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------


@router.post("/export", response_model=RetDataFile)
async def export_adressen(adressen: list[AdressenEntity], _: CurrentUser) -> RetDataFile:
    cfg = get_config()
    fmt_today = date_cls.today().strftime("%d.%m.%Y")

    wb = Workbook()
    sheet = wb.active
    sheet.title = "Adressen"

    title_font = Font(name="Tahoma", size=I_FONT_SIZE_TITEL, bold=True)
    row_font = Font(name="Tahoma", size=I_FONT_SIZE_ROW)
    headers = [
        "MNR",
        "Anrede",
        "Name",
        "Vorname",
        "Adresse",
        "PLZ",
        "Ort",
        "Land",
        "Telefon (P)",
        "Mobile",
        "Email",
        "Notizen",
        "SAM Nr.",
        "SAM Mitglied",
        "Ehrenmitglied",
        "Vorstand",
        "Revisor",
        "Allianz",
        "Eintritt",
        "Austritt",
    ]
    for i, h in enumerate(headers, start=1):
        col = chr(ord("A") + i - 1)
        set_cell_value_format(sheet, f"{col}1", h, border=True, font=title_font)

    row = 2
    for a in adressen:
        cells = [
            a.mnr,
            "Herr" if a.geschlecht == 1 else "Frau",
            a.name,
            a.vorname,
            a.adresse,
            a.plz,
            a.ort,
            a.land,
            a.telefon_p,
            a.mobile,
            a.email,
            a.notes,
            a.mnr_sam,
            "Ja" if a.sam_mitglied else "Nein",
            "Ja" if a.ehrenmitglied else "Nein",
            "Ja" if a.vorstand else "Nein",
            "Ja" if a.revisor else "Nein",
            "Ja" if a.allianz else "Nein",
            a.eintritt.strftime("%d.%m.%Y") if a.eintritt else "",
            a.austritt.strftime("%d.%m.%Y") if a.austritt and a.austritt.strftime("%d.%m.%Y") != "01.01.3000" else "",
        ]
        for i, val in enumerate(cells, start=1):
            col = chr(ord("A") + i - 1)
            set_cell_value_format(sheet, f"{col}{row}", val, border=True, font=row_font)
            if i in (14, 15, 16, 17, 18):
                sheet[f"{col}{row}"].alignment = Alignment(horizontal="center")
        row += 1

    sheet.auto_filter.ref = "A1:T1"
    widths = [10, 12, 15, 15, 25, 8, 25, 10, 20, 20, 35, 35, 13, 20, 20, 20, 20, 20, 12, 12]
    for i, w in enumerate(widths, start=1):
        sheet.column_dimensions[chr(ord("A") + i - 1)].width = w

    Path(cfg.exports).mkdir(parents=True, exist_ok=True)
    filename = f"Adressen-{fmt_today}.xlsx"
    wb.save(cfg.exports + filename)
    return RetDataFile(data=RetDataFilePayload(filename=filename), message="Excelfile erstellt")


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


@router.post("/sendmail", response_model=RetData[dict])
async def send_email(body: EmailBody, _: CurrentUser) -> RetData[dict]:
    if not (body.email_an or body.email_bcc or body.email_cc):
        return RetData(data={}, type="error", message="No recipients defined")
    if not body.email_body:
        return RetData(data={}, type="error", message="No message to send")

    cfg = get_config()
    signature = body.email_signature or cfg.raw.get("defaultEmail", "JanineFranken")
    attachments: list[str] = []
    if body.email_uploadfiles:
        attachments = [cfg.uploads + f for f in body.email_uploadfiles.split(",") if f]
    try:
        await send_mail(
            sender_signature=signature,
            to=[t for t in [body.email_an] if t],
            cc=[c for c in [body.email_cc] if c],
            bcc=[b for b in [body.email_bcc] if b],
            subject=body.email_subject,
            html=body.email_body,
            attachments=attachments,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("sendmail failed (signature=%s)", signature)
        return RetData(data={}, type="error", message=str(exc))
    return RetData(data={}, type="success", message="Email sent")


# ---------------------------------------------------------------------------
# Swiss QR-Bill
# ---------------------------------------------------------------------------


@router.get("/qrbill", response_model=RetDataFile)
async def create_qr_bill(id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetDataFile:
    cfg = get_config()
    params = await load_params()
    jahr = params.get("CLUBJAHR", str(date_cls.today().year))

    adresse = await db.get(Adressen, id)
    if adresse is None:
        return RetDataFile(data=None, type="error", message="Adresse nicht gefunden")

    creditor = {
        "name": "Auto-Moto-Club Swissair",
        "line1": "Breitenrain 4",
        "line2": "8917 Oberlunkhofen",
        "country": "CH",
    }
    debtor = {
        "name": f"{adresse.vorname} {adresse.name}",
        "line1": adresse.adresse or "",
        "line2": f"{adresse.plz or ''} {adresse.ort or ''}".strip(),
        "country": adresse.land or "CH",
    }
    additional = f"Rechnungsnummer {jahr}0000{adresse.mnr}"

    filename = f"AMC-Mitgliederbeitrag-{jahr}-{adresse.mnr}.pdf"
    Path(cfg.uploads).mkdir(parents=True, exist_ok=True)
    upload_path = cfg.uploads + filename

    pdf = canvas.Canvas(upload_path, pagesize=A4)
    pdf.setTitle(f"Mitgliederrechnung {jahr}")
    pdf.setAuthor("Auto-Moto-Club Swissair")

    # Logo
    logo_path = cfg.assets + "AMCfarbigKlein.jpg"
    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            140 * mm,
            A4[1] - 5 * mm - 30 * mm,
            width=50 * mm,
            height=30 * mm,
            preserveAspectRatio=True,
        )

    pdf.setFont("Helvetica", 12)
    pdf.drawString(20 * mm, A4[1] - 35 * mm, creditor["name"])
    pdf.drawString(20 * mm, A4[1] - 40 * mm, creditor["line1"])
    pdf.drawString(20 * mm, A4[1] - 45 * mm, creditor["line2"])

    pdf.drawString(130 * mm, A4[1] - 60 * mm, debtor["name"])
    pdf.drawString(130 * mm, A4[1] - 65 * mm, debtor["line1"])
    pdf.drawString(130 * mm, A4[1] - 70 * mm, debtor["line2"])

    pdf.setFont("Helvetica", 11)
    today = date_cls.today()
    pdf.drawRightString(190 * mm, A4[1] - 85 * mm, f"Oberlunkhofen {today.day}.{today.month}.{today.year}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, A4[1] - 100 * mm, additional)

    pdf.setFont("Helvetica", 12)
    anrede = "Lieber " if adresse.geschlecht == 1 else "Liebe "
    text_obj = pdf.beginText(20 * mm, A4[1] - 110 * mm)
    body_lines = [
        anrede + (adresse.vorname or ""),
        params.get("RECHNUNG", ""),
        "",
        "Mit liebem Clubgruss",
        "Janine Franken",
    ]
    for line in body_lines:
        for sub in line.split("\n"):
            text_obj.textLine(sub)
    pdf.drawText(text_obj)

    # TWINT
    try:
        twint_path = cfg.assets + "TWINT_DE.svg"
        if os.path.exists(twint_path):
            drawing = svg2rlg(twint_path)
            if drawing is not None:
                # Original-SVG ist 521 x 238 px (Verhältnis ~2.19).
                # 1 px = 25.4/96 mm  (SVG-Standard 96 DPI).
                # Hier: Breite auf 60 mm, Höhe per Aspect-Ratio.
                px_to_mm = 25.4 / 96
                target_w = 60 * mm
                if drawing.width and drawing.height:
                    target_h = target_w * (drawing.height / drawing.width)
                    sx = target_w / drawing.width
                    sy = target_h / drawing.height
                    drawing.scale(sx, sy)
                    drawing.width = target_w
                    drawing.height = target_h
                else:
                    # Fallback: feste px-Werte aus Original umrechnen
                    target_h = 238 * px_to_mm * mm
                renderPDF.draw(drawing, pdf, (A4[0] - target_w) / 2, 120 * mm)
    except Exception:  # noqa: BLE001
        logger.exception("Error adding TWINT image for adresse id=%s", id)

    # Swiss QR-Bill
    try:
        bill = QRBill(
            account="CH3009000000870661227",
            creditor={
                "name": creditor["name"],
                "line1": creditor["line1"],
                "line2": creditor["line2"],
                "country": creditor["country"],
            },
            debtor={
                "name": debtor["name"],
                "line1": debtor["line1"],
                "line2": debtor["line2"],
                "country": debtor["country"],
            },
            additional_information=additional,
            language="de",
        )
        # Swiss QR-Bill als SVG erzeugen, mit svglib zu Drawing parsen und
        # an den unteren A4-Rand zeichnen (Beleg ist 210 mm × 105 mm).
        svg_fd, svg_path = tempfile.mkstemp(suffix=".svg")
        os.close(svg_fd)
        try:
            bill.as_svg(svg_path)
            drawing = svg2rlg(svg_path)
            if drawing is not None:
                target_w = 210 * mm
                target_h = 105 * mm
                # svg2rlg liefert Dimensionen in Punkten; auf Belegmaß skalieren.
                if drawing.width and drawing.height:
                    sx = target_w / drawing.width
                    sy = target_h / drawing.height
                    drawing.scale(sx, sy)
                    drawing.width = target_w
                    drawing.height = target_h
                renderPDF.draw(drawing, pdf, 0, 0)
        finally:
            try:
                os.remove(svg_path)
            except OSError:
                pass
    except Exception:  # noqa: BLE001
        logger.exception("Error creating QR-Bill for adresse id=%s", id)
    pdf.showPage()
    pdf.save()

    email_body_html = (
        "<p>"
        + anrede
        + (adresse.vorname or "")
        + "</p>"
        + "<p>"
        + (params.get("RECHNUNG", "") or "").replace("\n", "</p><p>")
        + "</p>"
        + "<p>Mit liebem Clubgruss</p><p>Janine Franken</p>"
    )

    try:
        await send_mail(
            sender_signature="JanineFranken",
            to=[adresse.email] if adresse.email else [],
            subject="Auto-Moto-Club Swissair - Mitgliederrechnung",
            html=email_body_html,
            attachments=[upload_path],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send QR-Bill email to %s", adresse.email)
        return RetDataFile(
            data=RetDataFilePayload(filename=filename),
            type="error",
            message=str(exc),
        )

    # Journal entry + receipt copy
    now = datetime.now(UTC)
    journal = Journal(
        memo=f"Mitgliederbeitrag {jahr} von {debtor['name']}",
        date=today,
        year=today.year,
        amount=30,
        from_account=31,
        to_account=21,
        createdAt=now,
        updatedAt=now,
    )
    db.add(journal)
    await db.flush()

    base_path = cfg.documents + str(jahr) + "/"
    os.makedirs(base_path + "receipt", exist_ok=True)
    receipt_name = f"receipt/Journal-{journal.id}.pdf"
    if os.path.exists(upload_path):
        shutil.copyfile(upload_path, base_path + receipt_name)
    else:
        return RetDataFile(
            data=RetDataFilePayload(filename=filename),
            type="error",
            message="QR-Rechnung erstellt und versendet. Konnte File nicht kopieren",
        )

    receipt_obj = Receipt(
        receipt=receipt_name,
        bezeichnung=filename,
        jahr=str(jahr),
        createdAt=now,
        updatedAt=now,
    )
    db.add(receipt_obj)
    await db.flush()
    db.add(JournalReceipt(journalid=journal.id, receiptid=receipt_obj.id))

    return RetDataFile(
        data=RetDataFilePayload(filename=filename),
        message="QR-Rechnung erstellt und versendet",
    )


# --------------------------------------------------------------------------- CRUD


@router.post("", response_model=RetData[AdressenEntity], status_code=201)
async def create(
    body: AdressenCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AdressenEntity]:
    existing = await db.scalar(select(Adressen).where(Adressen.vorname == body.vorname, Adressen.name == body.name))
    if existing:
        raise HTTPException(status_code=409, detail="Adress already exists")
    now = datetime.now(UTC)
    data = body.model_dump()
    data["fullname"] = f"{body.vorname} {body.name}"
    obj = Adressen(**data, createdAt=now, updatedAt=now)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=AdressenEntity.model_validate(obj), message="Address created")


@router.get("", response_model=RetData[list[AdressenEntity]])
async def find_all(_: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[list[AdressenEntity]]:
    today = date_cls.today()
    rows = (
        (
            await db.execute(
                select(Adressen).where(Adressen.austritt >= today).order_by(asc(Adressen.name), asc(Adressen.vorname))
            )
        )
        .scalars()
        .all()
    )
    return RetData(data=[AdressenEntity.model_validate(r) for r in rows], message="Addresses found")


@router.get("/{adr_id}", response_model=RetData[AdressenEntity | None])
async def find_one(
    adr_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AdressenEntity | None]:
    obj = await db.get(Adressen, adr_id)
    if obj is None:
        return RetData(data=None, message="findOne")
    return RetData(data=AdressenEntity.model_validate(obj), message="Address found")


@router.patch("/{adr_id}", response_model=RetData[AdressenEntity])
async def update(
    adr_id: int,
    body: AdressenUpdate,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetData[AdressenEntity]:
    obj = await db.get(Adressen, adr_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Address not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=AdressenEntity.model_validate(obj), message="Address updated")


@router.delete("/{adr_id}", response_model=RetData[AdressenEntity])
async def remove(adr_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[AdressenEntity]:
    obj = await db.get(Adressen, adr_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Address not found")
    obj.austritt = date_cls.today()
    obj.updatedAt = datetime.now(UTC)
    await db.flush()
    await db.refresh(obj, ["adressen"])
    return RetData(data=AdressenEntity.model_validate(obj), message="Address deleted")
