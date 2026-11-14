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
| `CLOUDFLARE_TURNSPIKE_SITEKEY` | für Kontaktformular | Öffentlicher Turnstile Site Key |
| `CLOUDFLARE_TURNSPIKE_SECRET` | für Kontaktformular | Geheimer Turnstile-Schlüssel, nur im Backend |

\* eines von beiden. \*\* nur für E-Mail-Versand nötig.

## Spam-Schutz im Kontaktformular

Die beiden Turnstile-Variablen müssen in der Backend-Laufzeitumgebung gesetzt
sein (bei Docker in der über `--env-file` geladenen Datei). Die Schreibweise
`TURNSPIKE` entspricht den bestehenden Variablennamen.
`GET /public/turnstile` liefert ausschliesslich den öffentlichen Site Key.
`POST /public/kontakt` verlangt `turnstile_token` und prüft das Token bei
Cloudflare mit der Aktion `kontakt`, bevor eine Nachricht gespeichert oder
versendet wird. Fehlende/ungültige Tokens werden abgelehnt; bei einem Ausfall
oder fehlender Konfiguration wird HTTP 503 zurückgegeben, ohne Captcha-Fallback.
Honeypot und das bestehende Rate-Limit bleiben aktiv. Anlass-Anmeldungen nutzen
weiterhin die Rechenaufgabe.

Backend und Homepage müssen gemeinsam aktualisiert werden. Die Homepage benötigt
keinen Secret Key und lädt den Site Key serverseitig vom Backend. Im
Cloudflare-Widget müssen die tatsächlich verwendeten Homepage-Hostnamen
freigegeben sein (für lokale Tests gegebenenfalls auch `localhost`).

## Volumes

| Pfad im Container        | Zweck                                       |
| ------------------------ | ------------------------------------------- |
| `/usr/src/app/documents` | erzeugte Dokumente (QR-Rechnungen, Exporte) |
| `/usr/src/app/public`    | assets, exports und imports                 |
| `/usr/src/app/logs`      | System Logfiles                             |

## Zusammenspiel

Wird üblicherweise zusammen mit [`janine65/amcfrontend`](https://hub.docker.com/r/janine65/amcfrontend) betrieben; das Frontend-nginx proxied `/amcbackend/` auf diesen Service (Compose-Servicename `amcbackend`, Port 3001).
