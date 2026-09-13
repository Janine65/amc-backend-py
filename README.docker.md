# AMC Backend (`janine65/amcbackend`)

FastAPI-Backend der internen Vereinsverwaltung des Auto-Moto-Club Swissair (Mitglieder, Anlässe, Meisterschaften, Buchhaltung inkl. Swiss QR-Rechnung und E-Mail-Versand).

## Stack

- Python 3.13 / FastAPI / SQLAlchemy (async) / PostgreSQL
- Uvicorn auf Port **3001**
- Alembic-Migrationen, Excel-Export (openpyxl), PDF/QR-Bill (reportlab, qrbill)

## Tags

| Tag      | Bedeutung                                      |
| -------- | ---------------------------------------------- |
| `latest` | aktueller Build von `main`                     |
| `x.y.z`  | Release-Version (entspricht `PACKAGE_VERSION`) |

## Verwendung

```bash
docker run -d --name amcbackend \
  -p 3001:3001 \
  --env-file .env-prod \
  -v /pfad/zu/documents:/usr/src/app/dist/src/documents \
  janine65/amcbackend:latest
```

Health-/Info-Endpoint: `GET http://localhost:3001/` – Swagger-UI unter `/docs`.

## Umgebungsvariablen

| Variable                   | Pflicht   | Beschreibung                                                           |
| -------------------------- | --------- | ---------------------------------------------------------------------- |
| `APP_ENV`                  | nein      | `development` / `test` / `production` (Default im Image: `production`) |
| `DATABASE_URL`             | ja\*      | z. B. `postgresql+asyncpg://user:pwd@host:5432/amcadmin`               |
| `DB_PASSWORD`              | ja\*      | Alternative zu `DATABASE_URL` (URL wird aus config.json aufgebaut)     |
| `JWT_SECRET`               | ja        | Signierschlüssel für Auth-Tokens (min. 32 Zeichen)                     |
| `JWT_EXPIRES_IN`           | nein      | Token-Lebensdauer in Sekunden (Default 3600)                           |
| `CORS_ORIGIN`              | ja        | erlaubte Origins, kommasepariert                                       |
| `SMTP_PWD_JANINEFRANKEN`   | ja\*\*    | SMTP-Passwort der Signatur „JanineFranken“                             |
| `SMTP_PWD_HANSJOERGDUTLER` | ja\*\*    | SMTP-Passwort der Signatur „HansjoergDutler“                           |
| `UNSUBSCRIBE_SECRET`       | empfohlen | Secret für signierte One-Click-Abmeldelinks in Massen-E-Mails          |

\* eines von beiden. \*\* nur für E-Mail-Versand nötig.

## Volumes

| Pfad im Container        | Zweck                                       |
| ------------------------ | ------------------------------------------- |
| `/usr/src/app/documents` | erzeugte Dokumente (QR-Rechnungen, Exporte) |
| `/usr/src/app/public`    | assets, exports und imports                 |
| `/usr/src/app/logs`      | System Logfiles                             |

## Zusammenspiel

Wird üblicherweise zusammen mit [`janine65/amcfrontend`](https://hub.docker.com/r/janine65/amcfrontend) betrieben; das Frontend-nginx proxied `/amcbackend/` auf diesen Service (Compose-Servicename `amcbackend`, Port 3001).
