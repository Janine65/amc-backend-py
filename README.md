# amc-backend-py

Python / FastAPI für die AMC Internal Application.

## Stack

- **FastAPI** + Uvicorn
- **SQLAlchemy 2.0 (async, asyncpg)** + Alembic
- **Pydantic v2** + `pydantic-settings`
- **python-jose** für JWT, **passlib[bcrypt]** für Passwort-Hashing
- **openpyxl** (Excel), **reportlab** (PDF), **qrbill** (Swiss QR-Bill)
- **fastapi-mail** für SMTP

Das Datenbankschema entspricht 1:1 dem bestehenden Prisma-Schema – die SQLAlchemy-Modelle
sind so getypt, dass keine Migration nötig ist. Alembic ist für künftige Änderungen
konfiguriert (`autogenerate` ist deaktiviert; nur manuelle Revisionen).

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # Werte ausfüllen
```

## Starten

```bash
uvicorn app.main:app --reload
```

Swagger UI: <http://localhost:3002/api>

## Projektstruktur

```
app/
  core/
    config.py       # entspricht ConfigService (mit config.json + ENV)
    database.py     # SQLAlchemy Engine + Session
    security.py     # JWT + Password
    exceptions.py   # globale Exception Handler (PrismaClientExceptionFilter-Äquivalent)
  models/           # SQLAlchemy Modelle (1:1 Prisma)
  schemas/          # Pydantic Schemas (DTOs + Entities)
  routers/          # FastAPI Router (entspricht NestJS Controllern)
  services/         # Business Logic (entspricht NestJS Services)
  utils/            # Hilfsklassen (RetData, Excel/PDF Helpers, Mail)
  main.py           # App-Bootstrap, Middleware, Swagger
config.json         # 1:1 aus amc-backend übernommen
alembic/            # Migrationen
tests/              # Verschieden Tests für Routen
```

## Endpunkte

Alle Endpunkte aus `amc-backend` wurden 1:1 portiert. Auflistung der Hauptpräfixe:

| Präfix              | Modul                                              |
| ------------------- | -------------------------------------------------- |
| `/auth`             | Login / Refresh Token                              |
| `/about`, `/health` | App-Meta                                           |
| `/account`          | Konten                                             |
| `/adressen`         | Mitglieder-Adressen                                |
| `/anlaesse`         | Anlässe                                            |
| `/budget`           | Budget                                             |
| `/clubmeister`      | Clubmeisterschaft                                  |
| `/fiscalyear`       | Geschäftsjahr (inkl. Bilanz/Erfolgsrechnung Excel) |
| `/journal`          | Journal (inkl. Excel/PDF Export)                   |
| `/journal-receipt`  | Journal-Receipt-Verknüpfung                        |
| `/kegelkasse`       | Kegelkasse (inkl. Excel/PDF Export)                |
| `/kegelmeister`     | Kegelmeisterschaft                                 |
| `/meisterschaft`    | Meisterschaft                                      |
| `/parameter`        | Parameter                                          |
| `/receipt`          | Belege                                             |
| `/user`             | Benutzer                                           |
| `/files`            | Datei-Upload/Download                              |

## Lizenz

UNLICENSED – siehe `LICENSE` im ursprünglichen Repository.
