"""Configuration service.

Equivalent of ``ConfigService`` (src/config/config.service.ts) from amc-backend.
Loads layered configuration from ``config.json`` (development/test/production),
overlays environment variables (``UPPER_SNAKE_CASE`` of the keys), resolves
``${VAR}`` placeholders inside string values, and exposes filesystem paths,
SMTP signatures and a ``params`` dict that mirrors the ``parameter`` table.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from app.core.logging import get_logger

# ---------------------------------------------------------------------------
# Configuration data structures
# ---------------------------------------------------------------------------

logger = get_logger(__name__)


@dataclass
class SmtpSignature:
    smtp: str
    smtp_port: int
    smtp_user: str
    # In config.json this contains the *name* of the env variable.  After
    # ENV-resolution the actual password value is stored here.
    smtp_pwd_env: str
    email_from: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_REF_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")
_ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SENSITIVE_KEY_RE = re.compile(r"(password|passwd|pwd|secret|token|api[_-]?key)", re.IGNORECASE)


def _resolve_env_string(value: str) -> str:
    """Replace ``${VAR}`` placeholders or pure ENV variable names with their values."""
    result = _ENV_REF_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if _ENV_NAME_RE.match(result) and result in os.environ:
        result = os.environ[result]
    return result


def _resolve_env_refs(obj: Any) -> Any:
    """Recursively resolve ENV-references inside dicts/lists in-place."""
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if isinstance(value, str):
                obj[key] = _resolve_env_string(value)
            else:
                _resolve_env_refs(value)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str):
                obj[i] = _resolve_env_string(item)
            else:
                _resolve_env_refs(item)
    return obj


def _camel_to_upper_snake(key: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).upper()


def _coerce_env(env_val: str, current: Any) -> Any:
    if isinstance(current, bool):
        return env_val == "true" or env_val == "1"
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            return int(env_val)
        except ValueError:
            return current
    if isinstance(current, float):
        try:
            return float(env_val)
        except ValueError:
            return current
    return env_val


# Package metadata that mirrors NestJS' package.json reads
PACKAGE_NAME = "amc-backend-py"
PACKAGE_VERSION = "7.0.11"
PACKAGE_AUTHOR = "Janine Franken"
PACKAGE_DESCRIPTION = "Backend for AMC Internal Application"
PACKAGE_EMAIL = "janine@automoto-sr.info"
PACKAGE_HOMEPAGE = "https://interna.automoto-sr.info"


# ---------------------------------------------------------------------------
# ConfigService singleton
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Runtime configuration (singleton)."""

    _instance: ClassVar[Config | None] = None

    raw: dict[str, Any] = field(default_factory=dict)
    documents: str = ""
    public: str = ""
    uploads: str = ""
    exports: str = ""
    assets: str = ""
    log_dir: str = ""
    params: dict[str, str] = field(default_factory=dict)

    # --------------- meta accessors ---------------
    @property
    def name(self) -> str:
        return PACKAGE_NAME

    @property
    def version(self) -> str:
        return PACKAGE_VERSION

    @property
    def author(self) -> str:
        return PACKAGE_AUTHOR

    @property
    def description(self) -> str:
        return PACKAGE_DESCRIPTION

    @property
    def email(self) -> str:
        return PACKAGE_EMAIL

    @property
    def homepage(self) -> str:
        return PACKAGE_HOMEPAGE

    # --------------- generic getter ---------------
    def get(self, key: str, default: Any) -> Any:
        value = self.raw.get(key)
        if value is None:
            return default
        return value

    def get_smtp_password(self, signature: str) -> str:
        smtp_cfg = self.raw.get(signature) or {}
        value = smtp_cfg.get("smtp_pwd_env") if isinstance(smtp_cfg, dict) else None
        if not value:
            raise RuntimeError(f'SMTP configuration for "{signature}" is missing "smtp_pwd_env".')
        if _ENV_NAME_RE.match(value):
            raise RuntimeError(
                f'Environment variable "{value}" is not set (required for SMTP signature "{signature}").'
            )
        return value

    # --------------- migration helper ---------------
    def database_url_sync_for_alembic(self) -> str:
        """Return a sync-style URL for Alembic (asyncpg works there too)."""
        url = os.environ.get("DATABASE_URL", "")
        if url:
            return url
        return self._build_database_url()

    # --------------- internal ---------------
    def _build_database_url(self) -> str:
        pwd = os.environ.get("DB_PASSWORD")
        if not pwd:
            raise RuntimeError("Database credentials missing: set DATABASE_URL or DB_PASSWORD env var.")
        return (
            f"{self.raw.get('dbtype', 'postgresql+asyncpg')}://"
            f"{self.raw.get('db_user')}:{pwd}@"
            f"{self.raw.get('dbhost')}:{self.raw.get('port')}/"
            f"{self.raw.get('database')}"
        )

    @property
    def database_url(self) -> str:
        url = os.environ.get("DATABASE_URL")
        if url:
            # Allow plain postgres URLs by upgrading them to the asyncpg driver.
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return self._build_database_url()


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"


def _load_raw_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as fh:
        document = json.load(fh)
    sections = document.get("config", {})
    default = sections.get("development", {})
    env = os.environ.get("APP_ENV") or os.environ.get("NODE_ENV") or "development"
    overlay = sections.get(env, default)
    merged: dict[str, Any] = {**default, **overlay}

    # Overlay env vars
    for key in list(merged.keys()):
        env_key = _camel_to_upper_snake(key)
        env_val = os.environ.get(env_key)
        if env_val is None or env_val == "":
            continue
        current = merged[key]
        if isinstance(current, dict):
            continue
        merged[key] = _coerce_env(env_val, current)

    _resolve_env_refs(merged)
    return merged


def _ensure_dir(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    return str(path) + "/"


def get_config() -> Config:
    """Return the singleton ``Config`` instance, building it on first call."""
    if Config._instance is not None:
        return Config._instance

    raw = _load_raw_config()
    base = Path(__file__).resolve().parent.parent.parent
    cfg = Config(
        raw=raw,
        documents=_ensure_dir(base / "documents"),
        public=_ensure_dir(base / "public"),
        uploads=_ensure_dir(base / "public" / "uploads"),
        exports=_ensure_dir(base / "public" / "exports"),
        assets=_ensure_dir(base / "public" / "assets"),
        log_dir=_ensure_dir(base / "logs"),
    )
    Config._instance = cfg
    logger.debug(f"Loaded configuration for environment '{os.environ.get('APP_ENV', 'development')}'")
    return cfg


async def load_params(reload: bool = False) -> dict[str, str]:
    """Load the ``parameter`` table into ``Config.params``."""
    from sqlalchemy import select

    from app.core.database import async_session_maker  # local to avoid cycles
    from app.models.parameter import Parameter

    cfg = get_config()
    if cfg.params and not reload:
        return cfg.params
    async with async_session_maker() as session:
        logger.debug("Loading parameters from database...")
        cfg.params.clear()
        result = await session.execute(select(Parameter))
        for param in result.scalars():
            cfg.params[param.key] = param.value
    return cfg.params
