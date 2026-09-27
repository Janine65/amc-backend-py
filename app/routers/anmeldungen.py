"""``anlass_anmeldungen`` router (Verwaltung der Anmeldungen, nur mit Login)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlsxImage
from openpyxl.styles import Font
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config, load_params
from app.core.database import get_db
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.models.adressen import Adressen
from app.models.anlaesse import Anlaesse
from app.models.anlass_anmeldung import AnlassAnmeldung
from app.models.meisterschaft import Meisterschaft
from app.schemas.anlass_anmeldung import AnmeldungEntity, AnmeldungManualCreate, AnmeldungUpdate
from app.schemas.ret_data import RetData, RetDataFile, RetDataFilePayload
from app.utils.general import format_date_long, set_cell_value_format
from app.utils.mail import send_mail

logger = get_logger(__name__)

router = APIRouter(prefix="/anmeldungen", tags=["Anmeldungen"])


async def _send_bestaetigung(obj: AnlassAnmeldung, anlass_name: str) -> None:
    """Bestätigungsmail mit Text aus Parameter ``MAIL_ANMELDUNG`` senden."""
    if not obj.email:
        return
    params = await load_params()
    text = params.get("MAIL_ANMELDUNG", "")
    if not text:
        logger.warning("Parameter MAIL_ANMELDUNG fehlt – keine Bestätigungsmail gesendet (Anmeldung %s)", obj.id)
        return
    # Platzhalter {vorname}, {name}, {anlass} sind optional
    text = text.replace("{vorname}", obj.vorname).replace("{name}", obj.name).replace("{anlass}", anlass_name)
    html = text if "<" in text else "<p>" + text.replace("\n", "<br>") + "</p>"
    await send_mail(
        subject=f"Anmeldung zum {anlass_name}",
        to=obj.email,
        text=text,
        html=html,
    )


async def _find_adresse(db: AsyncSession, obj: AnlassAnmeldung) -> Adressen | None:
    """Adresse anhand Name, Vorname und E-Mail suchen (case-insensitive)."""
    return await db.scalar(
        select(Adressen).where(
            and_(
                func.lower(Adressen.name) == obj.name.strip().lower(),
                func.lower(Adressen.vorname) == obj.vorname.strip().lower(),
                func.lower(Adressen.email) == obj.email.strip().lower(),
            )
        )
    )


async def _resolve_adresse(db: AsyncSession, obj: AnlassAnmeldung) -> Adressen | None:
    """Verknüpfte Adresse laden; ohne Verknüpfung automatisch matchen und persistieren."""
    if obj.adresseid:
        adresse = await db.get(Adressen, obj.adresseid)
        if adresse is not None:
            return adresse
    adresse = await _find_adresse(db, obj)
    if adresse is not None:
        obj.adresseid = adresse.id
    return adresse


async def _create_buchung(db: AsyncSession, obj: AnlassAnmeldung, adresse: Adressen) -> None:
    """Meisterschafts-Buchung für die Person auf dem Anlass anlegen (falls nicht vorhanden)."""
    existing = await db.scalar(
        select(Meisterschaft).where(and_(Meisterschaft.mitgliedid == adresse.id, Meisterschaft.eventid == obj.anlassid))
    )
    if existing is not None:
        return
    anlass = await db.get(Anlaesse, obj.anlassid)
    now = datetime.now(UTC)
    db.add(
        Meisterschaft(
            mitgliedid=adresse.id,
            eventid=obj.anlassid,
            punkte=anlass.punkte if anlass else 50,
            zusatz=5,
            streichresultat=False,
            createdAt=now,
            updatedAt=now,
        )
    )
    await db.flush()


@router.get("", response_model=RetData[list[AnmeldungEntity]])
async def find_all(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    anlassid: int | None = None,
) -> RetData[list[AnmeldungEntity]]:
    stmt = (
        select(AnlassAnmeldung, Anlaesse.longname)
        .join(Anlaesse, AnlassAnmeldung.anlassid == Anlaesse.id)
        # Ältere Anmeldungen (6 Monate) ausblenden
        .where(AnlassAnmeldung.updatedAt >= datetime.now(UTC) - timedelta(days=183))
        .order_by(AnlassAnmeldung.createdAt.desc())
    )
    if anlassid is not None:
        stmt = stmt.where(AnlassAnmeldung.anlassid == anlassid)
    rows = (await db.execute(stmt)).all()
    data = [AnmeldungEntity.model_validate(a).model_copy(update={"anlass_longname": longname}) for a, longname in rows]
    return RetData(data=data, message="findAll")


@router.post("", response_model=RetData[AnmeldungEntity], status_code=201)
async def create_manual(
    body: AnmeldungManualCreate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AnmeldungEntity]:
    """Manuelle Anmeldung einer Adresse für einen Anlass."""
    adresse = await db.get(Adressen, body.adresseid)
    if adresse is None:
        raise HTTPException(status_code=404, detail="Adresse nicht gefunden")
    if not adresse.email:
        raise HTTPException(status_code=400, detail="Adresse hat keine E-Mail-Adresse.")
    anlass = await db.get(Anlaesse, body.anlassid)
    if anlass is None:
        raise HTTPException(status_code=404, detail="Anlass nicht gefunden")

    existing = await db.scalar(
        select(AnlassAnmeldung).where(
            and_(
                AnlassAnmeldung.anlassid == body.anlassid,
                AnlassAnmeldung.email == adresse.email.lower(),
            )
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Für diese Person existiert bereits eine Anmeldung.")

    now = datetime.now(UTC)
    obj = AnlassAnmeldung(
        anlassid=body.anlassid,
        adresseid=adresse.id,
        name=adresse.name,
        vorname=adresse.vorname,
        email=adresse.email.lower(),
        bemerkung="Manuell erfasst",
        status=1,
        createdAt=now,
        updatedAt=now,
    )
    db.add(obj)
    await db.flush()
    return RetData(data=AnmeldungEntity.model_validate(obj), message="Anmeldung erstellt")


@router.get("/export", response_model=RetDataFile)
async def export_anmeldungen(
    anlassid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetDataFile:
    """Teilnehmerliste als Excel, Layout gemäss Vorlage ``Anmeldungen.xls``."""
    anlass = await db.get(Anlaesse, anlassid)
    if anlass is None:
        raise HTTPException(status_code=404, detail="Anlass nicht gefunden")

    rows = (
        await db.execute(
            select(AnlassAnmeldung, Adressen)
            .join(Adressen, AnlassAnmeldung.adresseid == Adressen.id, isouter=True)
            .where(and_(AnlassAnmeldung.anlassid == anlassid, AnlassAnmeldung.status != 0))
            .order_by(AnlassAnmeldung.name.asc(), AnlassAnmeldung.vorname.asc())
        )
    ).all()

    workbook = Workbook()
    if workbook.active is not None:
        workbook.remove(workbook.active)
    sheet = workbook.create_sheet("Anmeldungen")

    # Layout/Formatierung exakt gemäss Vorlage public/assets/Anmeldungen.xls (Arial)
    for col, width in zip("ABCDEF", (18, 23, 11, 23, 34, 40), strict=True):
        sheet.column_dimensions[col].width = width
    for row, height in ((2, 18), (3, 13), (4, 13), (10, 18), (12, 18), (13, 18), (14, 16), (18, 23)):
        sheet.row_dimensions[row].height = height

    def arial(size: int, bold: bool = False, color: str | None = None) -> Font:
        return Font(name="Arial", size=size, bold=bold, color=color)

    # Logo links oben (Grösse wie Vorlage)
    logo_path = Path(get_config().assets) / "AMCfarbigKlein.jpg"
    if logo_path.exists():
        logo = XlsxImage(str(logo_path))
        logo.width, logo.height = 138, 154
        sheet.add_image(logo, "A1")

    # Kontaktblock Sportpräsident: rechtsbündig über A:F
    set_cell_value_format(sheet, "A2:F2", "Sportpräsident", merge=True, font=arial(14, True), align_h="right")
    set_cell_value_format(sheet, "A3:F3", "Hansjörg Dutler", merge=True, font=arial(10), align_h="right")
    set_cell_value_format(sheet, "A4:F4", "079 629 33 03", merge=True, font=arial(10), align_h="right")

    set_cell_value_format(sheet, "A10:F10", "Anmeldungen", merge=True, font=arial(14, True), align_h="center")

    set_cell_value_format(sheet, "A12", "Anlass:", font=arial(12))
    set_cell_value_format(sheet, "B12", anlass.name, font=arial(14))
    set_cell_value_format(sheet, "A13", "Datum", font=arial(12))
    set_cell_value_format(sheet, "B13:C13", format_date_long(anlass.datum), merge=True, font=arial(14))
    set_cell_value_format(sheet, "A14", "Clubpunkte", font=arial(12))
    set_cell_value_format(sheet, "B14", anlass.punkte, font=arial(12))

    set_cell_value_format(sheet, "A18", "TeilnehmerInnen", font=arial(12))
    # Teilnehmerzahl: blau/fett auf orangem Grund, zentriert (wie Vorlage)
    set_cell_value_format(sheet, "B18", len(rows), font=arial(18, True, "0000FF"), fill="FFCC99", align_h="center")

    # Tabellenkopf ohne Rahmen (wie Vorlage), Daten mit Rahmen ab Zeile 22
    headers = ("Name", "Vorname", "Geburtsjahr", "Adresse", "Ort", "Email")
    for col, title in zip("ABCDEF", headers, strict=True):
        set_cell_value_format(sheet, f"{col}20", title, font=arial(11))

    r = 22
    for anmeldung, adresse in rows:
        values = (
            anmeldung.name,
            anmeldung.vorname,
            adresse.jahrgang if adresse else None,
            adresse.adresse if adresse else None,
            f"{adresse.plz} {adresse.ort}" if adresse else None,
            anmeldung.email,
        )
        for col, value in zip("ABCDEF", values, strict=True):
            set_cell_value_format(sheet, f"{col}{r}", value, border=True, font=arial(11))
        r += 1
    # Vorlage enthält vorformatierte Leerzeilen bis Zeile 49
    for empty_r in range(r, 50):
        for col in "ABCDEF":
            set_cell_value_format(sheet, f"{col}{empty_r}", None, border=True, font=arial(11))

    cfg = get_config()
    filename = f"Anmeldungen-{anlassid}.xlsx"
    Path(cfg.exports).mkdir(parents=True, exist_ok=True)
    workbook.save(cfg.exports + filename)
    return RetDataFile(data=RetDataFilePayload(filename=filename), message="Excelfile erstellt")


@router.post("/bestaetigen", response_model=RetData[int])
async def confirm_all(anlassid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[int]:
    """Alle neuen Anmeldungen (Status 1) des Anlasses bestätigen und Mails senden."""
    anlass = await db.get(Anlaesse, anlassid)
    if anlass is None:
        raise HTTPException(status_code=404, detail="Anlass nicht gefunden")
    rows = (
        (
            await db.execute(
                select(AnlassAnmeldung).where(and_(AnlassAnmeldung.anlassid == anlassid, AnlassAnmeldung.status == 1))
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    for obj in rows:
        obj.status = 2
        obj.updatedAt = now
        await _send_bestaetigung(obj, anlass.longname or anlass.name)
    await db.flush()
    return RetData(data=len(rows), message=f"{len(rows)} Anmeldungen bestätigt")


@router.post("/anwesend", response_model=RetData[int])
async def attend_all(anlassid: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[int]:
    """Alle Anmeldungen (Status 1/2) des Anlasses auf "war anwesend" setzen und buchen.

    Einträge ohne passende Adresse bleiben unverändert und werden in der
    Meldung aufgeführt.
    """
    rows = (
        (
            await db.execute(
                select(AnlassAnmeldung).where(
                    and_(AnlassAnmeldung.anlassid == anlassid, AnlassAnmeldung.status.in_([1, 2]))
                )
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    done = 0
    failed: list[str] = []
    for obj in rows:
        adresse = await _resolve_adresse(db, obj)
        if adresse is None:
            failed.append(f"{obj.vorname} {obj.name}")
            continue
        await _create_buchung(db, obj, adresse)
        obj.status = 3
        obj.updatedAt = now
        done += 1
    await db.flush()
    message = f"{done} Anmeldungen gebucht"
    if failed:
        message += "; keine Adresse verknüpft für: " + ", ".join(failed)
    return RetData(data=done, message=message)


@router.patch("/{a_id}", response_model=RetData[AnmeldungEntity])
async def update(
    a_id: int, body: AnmeldungUpdate, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> RetData[AnmeldungEntity]:
    obj = await db.get(AnlassAnmeldung, a_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Anmeldung nicht gefunden")
    old_status = obj.status

    # Manuelle Verknüpfung: Adresse validieren und direkt setzen
    if body.adresseid is not None:
        if await db.get(Adressen, body.adresseid) is None:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")
        obj.adresseid = body.adresseid

    # Auf "war anwesend" → Buchung nötig; ohne verknüpfte Adresse Wechsel ablehnen
    if body.status == 3 and old_status != 3:
        adresse = await _resolve_adresse(db, obj)
        if adresse is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Keine Adresse mit {obj.vorname} {obj.name} ({obj.email}) verknüpft – "
                    "bitte zuerst manuell verknüpfen."
                ),
            )
        await _create_buchung(db, obj, adresse)

    for k, v in body.model_dump(exclude_none=True, exclude={"adresseid"}).items():
        setattr(obj, k, v)
    obj.updatedAt = datetime.now(UTC)
    await db.flush()

    # Neu bestätigt → Bestätigungsmail an die angemeldete Person
    if obj.status == 2 and old_status != 2:
        anlass = await db.get(Anlaesse, obj.anlassid)
        anlass_name = (anlass.longname or anlass.name) if anlass else ""
        await _send_bestaetigung(obj, anlass_name)

    return RetData(data=AnmeldungEntity.model_validate(obj), message="Anmeldung aktualisiert")


@router.delete("/{a_id}", response_model=RetData[AnmeldungEntity])
async def remove(a_id: int, _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> RetData[AnmeldungEntity]:
    obj = await db.get(AnlassAnmeldung, a_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Anmeldung nicht gefunden")
    entity = AnmeldungEntity.model_validate(obj)
    await db.delete(obj)
    await db.flush()
    return RetData(data=entity, message="Anmeldung gelöscht")
