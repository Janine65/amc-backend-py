"""Zentrale Logging-Konfiguration.

Aufruf einmalig beim App-Start (``configure_logging()``). Liefert ein einheitliches
Format mit Zeitstempel, Level, Modul- und Zeilennummer für alle Logger
(``app.*``, ``uvicorn``, ``uvicorn.access``, ``sqlalchemy.*``, ``fastapi``).

Konfiguration via Environment:

* ``LOG_LEVEL``    – ``DEBUG``/``INFO``/``WARNING``/``ERROR`` (Default: ``INFO``).
* ``LOG_FILE``     – Pfad zur Logdatei. Wenn leer/nicht gesetzt, nur stderr.
                     Default-Verhalten: ``<log_dir>/app.log`` aus ``Config``.
* ``LOG_NO_FILE``  – ``1``/``true`` deaktiviert die Datei-Ausgabe explizit.
* ``LOG_NO_COLOR`` – ``1``/``true`` deaktiviert ANSI-Farben am Terminal.
                     (Datei-Log ist immer farblos.)
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s (%(name)s:%(lineno)d - %(funcName)s)"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ANSI escape codes – Tabelle pro Loglevel.
_RESET = "\033[0m"
_LEVEL_COLORS: dict[int, str] = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[1;37;41m",  # bold weiss auf rot
}

_configured = False


class ColorFormatter(logging.Formatter):
    """Formatter, der die gesamte Logzeile je nach Level einfärbt."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = _LEVEL_COLORS.get(record.levelno)
        if color:
            return f"{color}{message}{_RESET}"
        return message


def _color_supported(stream) -> bool:
    if os.environ.get("LOG_NO_COLOR", "").lower() in {"1", "true", "yes"}:
        return False
    if os.environ.get("NO_COLOR"):  # https://no-color.org/
        return False
    if os.environ.get("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def _resolve_log_file() -> Path | None:
    if os.environ.get("LOG_NO_FILE", "").lower() in {"1", "true", "yes"}:
        return None
    explicit = os.environ.get("LOG_FILE")
    if explicit:
        return Path(explicit)
    # Lazy import: vermeidet Zyklus mit ``app.core.config``.
    try:
        from app.core.config import get_config

        cfg = get_config()
        if cfg.log_dir:
            return Path(cfg.log_dir) / "app.log"
    except Exception:  # noqa: BLE001 - Logging darf App-Start nicht crashen
        return None
    return None


def configure_logging(level: str | int | None = None) -> None:
    """Idempotent: konfiguriert das Root-Logging einmalig."""
    global _configured
    if _configured:
        return

    log_level_str = level if isinstance(level, str) else os.environ.get("LOG_LEVEL", "INFO")
    log_level = level if isinstance(level, int) else logging.getLevelName(str(log_level_str).upper())
    if not isinstance(log_level, int):
        log_level = logging.INFO

    plain_formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    color_formatter = ColorFormatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    handlers: list[logging.Handler] = []

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(color_formatter if _color_supported(sys.stderr) else plain_formatter)
    handlers.append(stream)

    log_file = _resolve_log_file()
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(plain_formatter)
            handlers.append(file_handler)
        except OSError:
            # Datei-Logging optional; Stream bleibt.
            pass

    root = logging.getLogger()
    # Vorhandene Handler (z. B. von uvicorn) durch unsere ersetzen.
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)
    root.setLevel(log_level)

    # uvicorn nutzt eigene Logger – auf Root delegieren lassen.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(log_level)

    # SQLAlchemy etwas leiser, ausser DEBUG explizit gewünscht.
    sa_level = log_level if log_level <= logging.DEBUG else logging.WARNING
    for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
        logging.getLogger(name).setLevel(sa_level)

    _configured = True
    logging.getLogger(__name__).debug(
        "Logging configured: level=%s, file=%s",
        logging.getLevelName(log_level),
        log_file,
    )


def get_logger(name: str) -> logging.Logger:
    """Bequeme Helper-Funktion: ``log = get_logger(__name__)``."""
    return logging.getLogger(name)
