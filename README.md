# amc-backend-py

Python / FastAPI für die AMC Internal Application.

## Stack

- **FastAPI** + Uvicorn
- **SQLAlchemy 2.0 (async, asyncpg)** + Alembic
- **Pydantic v2** + `pydantic-settings`
- **PyJWT** für JWT, **pwdlib[bcrypt]** für Passwort-Hashing
- **openpyxl** (Excel), **reportlab** (PDF), **qrbill** (Swiss QR-Bill)
- **fastapi-mail** für SMTP

Das Datenbankschema entspricht 1:1 dem bestehenden Prisma-Schema – die SQLAlchemy-Modelle
sind so getypt, dass keine Migration nötig ist. Alembic ist für künftige Änderungen
konfiguriert (`autogenerate` ist deaktiviert; nur manuelle Revisionen).

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # Werte ausfüllen
```

Bei bestehenden Umgebungen nach dem Update `pip uninstall python-jose ecdsa` ausführen.
Diese nicht mehr benötigten Pakete werden durch `pip install -r requirements-dev.txt`
nicht automatisch entfernt. Bestehende HS256-Tokens bleiben mit demselben
`JWT_SECRET` gültig.

Die JWT-Kompatibilitätstests benötigen keine Datenbankverbindung:

```bash
python -m pytest tests/test_auth.py -k jwt
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
| `/besucher`         | Sitzungsbezogene Homepage-Statistik                |

## Besucherstatistik

Backend, Homepage und Verwaltungs-Frontend gemeinsam aktualisieren und
`alembic upgrade head` ausführen (Revision `0008_besucher_statistik`).
Der bestehende Gesamtzähler bleibt erhalten; alte Besuche haben keine Details.

- `ANALYTICS_SECRET`: derselbe zufällige Schlüssel (mindestens 32 Zeichen) in
  Backend und Homepage, niemals im Browser oder im Verwaltungs-Frontend.
  Ohne Schlüssel ist die neue Erfassung deaktiviert und wird im Log gemeldet.
- `GEOIP_COUNTRY_DB`: Backend-Pfad zu einer lokalen GeoIP-Country-MMDB-Datei.
  Sie muss separat beschafft, lesbar eingebunden und regelmäßig aktualisiert
  werden. Es werden keine Besucher-IPs an einen externen GeoIP-Dienst gesendet.
  Ohne Datei ist das Land „Unbekannt“; ein konfigurierter ungültiger Pfad
  verhindert den Start.
- `POST /besucher/aufruf` und `/besucher/aktivitaet` verlangen den
  serverseitigen Header `X-Analytics-Key`.
- `GET /besucher/statistik?von=YYYY-MM-DD&bis=YYYY-MM-DD` verlangt Login
  mit Rolle `user` oder `admin`. Zeitraum: 1–365 Tage innerhalb der
  vergangenen 365 Tage, inklusive Enddatum,
  Zeitzone Europe/Zurich; Standard: letzte 30 Tage.

Auswertungen zählen Sitzungen nach ihrem Beginn im gewählten Zeitraum, keine
eindeutig identifizierten Menschen. Seitenaufrufe gehören zu diesen Sitzungen
und werden bis zum Ende des gewählten Zeitraums berücksichtigt.
Die Dauer misst näherungsweise die Zeit zwischen erstem Aufruf und letzter
erfasster Aktivität (auch Pausen zwischen Aufrufen), nicht aktive Lesezeit.
Nicht messbare Besuche bleiben im Durchschnitt unberücksichtigt und werden
gesondert ausgewiesen. Mehrere Tabs teilen eine Sitzung; nach 30 Minuten ohne
erfasste Aktivität beginnt eine neue.

Gespeichert werden zufällige Sitzungs-/Seiten-IDs, Zeitpunkte, normalisierte
Seitenpfade, Land, Herkunftskategorie, Referrer-Hostname und grobe
Geräte-/Browserkategorien. Keine IPs, vollständigen User-Agents, Suchbegriffe,
Formularinhalte oder Query-Parameter in den Statistikdaten.
Abgelaufene Sitzungen und ihre Seitenaufrufe werden beim Start und anschließend
täglich gelöscht (365 Tage), auch wenn die neue Erfassung deaktiviert ist.
Fehler beim Löschlauf werden protokolliert und nach einer Stunde erneut versucht.
Auch vor dem nächsten Löschlauf werden abgelaufene Daten nicht ausgewertet.
Der historische Gesamtzähler wird nicht gelöscht.

Die Homepage berücksichtigt DNT/GPC und zeigt einen Hinweis zur Erfassung.
Erfassung ohne Einwilligungsdialog wurde gewünscht; Rechtsgrundlage,
Informationspflichten und bestehende Infrastruktur-/Zugriffslogs müssen
vor dem produktiven Einsatz separat geprüft werden.

Validierung: `python -m pytest tests/test_besucher.py`.
Die Datenbanktests erstellen und entfernen ausschließlich ein eigenes,
zufällig benanntes Testschema in der konfigurierten PostgreSQL-Datenbank.

## Lizenz

UNLICENSED – siehe `LICENSE` im ursprünglichen Repository.
