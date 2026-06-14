"""SQLAlchemy 2.0 async engine + session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _split_schema(url: str) -> tuple[str, str | None]:
    """Strip Prisma-style ``?schema=...`` from a DB URL.

    Returns the cleaned URL and the extracted schema (or ``None``).
    asyncpg's ``connect()`` does not accept a ``schema`` kwarg, so we move it
    into ``server_settings.search_path`` instead.
    """
    parts = urlsplit(url)
    if not parts.query:
        return url, None
    params = parse_qsl(parts.query, keep_blank_values=True)
    schema: str | None = None
    remaining: list[tuple[str, str]] = []
    for key, value in params:
        if key == "schema":
            schema = value or None
        else:
            remaining.append((key, value))
    new_query = urlencode(remaining)
    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )
    return cleaned, schema


def _build_engine() -> AsyncEngine:
    cfg = get_config()
    url, schema = _split_schema(cfg.database_url)
    connect_args: dict[str, object] = {}
    if schema:
        connect_args["server_settings"] = {"search_path": schema}
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def async_session_maker() -> AsyncSession:  # type: ignore[override]
    """Return an ``AsyncSession`` context manager (used as ``async with``)."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_maker()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an ``AsyncSession``."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.exception("DB session rollback")
            await session.rollback()
            raise
