"""FastAPI application entry-point for the AMC backend."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import secure
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import (
    PACKAGE_AUTHOR,
    PACKAGE_NAME,
    PACKAGE_VERSION,
    get_config,
    load_params,
)
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.routers import (
    account,
    adressen,
    anlaesse,
    auth,
    budget,
    clubmeister,
    fiscalyear,
    journal,
    journal_receipt,
    kegelkasse,
    kegelmeister,
    meisterschaft,
    parameter,
    receipt,
    user,
)
from app.routers import (
    file as files_router,
)

# Logging so früh wie möglich konfigurieren – noch vor App-Erzeugung,
# damit auch Lifespan-/Middleware-Initialisierung die Konfiguration nutzt.
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load runtime parameters from the database before serving traffic."""
    logger.info("Starting %s v%s", PACKAGE_NAME, PACKAGE_VERSION)
    await load_params()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description=f"AMC backend (Python port) – maintainer {PACKAGE_AUTHOR}",
    docs_url="/api",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

cors_origin = os.getenv("CORS_ORIGIN", "*")
allow_origins = [o.strip() for o in cors_origin.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

# Rate limiting (slowapi) — 10/sec, 100/min
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "10/second"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# Security headers
# CSP locker genug, damit Swagger-UI (Assets von jsdelivr) in /api funktioniert.
_csp = (
    secure.ContentSecurityPolicy()
    .default_src("'self'")
    .script_src("'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'")
    .style_src("'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'")
    .img_src("'self'", "data:", "https://fastapi.tiangolo.com")
    .font_src("'self'", "data:", "https://cdn.jsdelivr.net")
    .connect_src("'self'")
    .object_src("'none'")
)
secure_headers = secure.Secure(
    csp=_csp,
    hsts=secure.StrictTransportSecurity().max_age(31536000),
    referrer=secure.ReferrerPolicy().strict_origin_when_cross_origin(),
    permissions=(
        secure.PermissionsPolicy()
        .geolocation()
        .microphone()
        .camera()
    ),
    xfo=secure.XFrameOptions().sameorigin(),
    xcto=secure.XContentTypeOptions(),
    coop=secure.CrossOriginOpenerPolicy().same_origin(),
)


@app.middleware("http")
async def set_secure_headers(request: Request, call_next):  # noqa: ANN001
    response = await call_next(request)
    await secure_headers.set_headers_async(response)
    return response


# Exception handlers (DB → HTTP)
register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(parameter.router)
app.include_router(user.router)
app.include_router(account.router)
app.include_router(budget.router)
app.include_router(fiscalyear.router)
app.include_router(journal.router)
app.include_router(journal_receipt.router)
app.include_router(receipt.router)
app.include_router(adressen.router)
app.include_router(anlaesse.router)
app.include_router(meisterschaft.router)
app.include_router(clubmeister.router)
app.include_router(kegelmeister.router)
app.include_router(kegelkasse.router)
app.include_router(files_router.router)


# ---------------------------------------------------------------------------
# Misc endpoints
# ---------------------------------------------------------------------------


@app.get("/about", tags=["meta"])
async def about() -> JSONResponse:
    return JSONResponse(
        {
            "name": PACKAGE_NAME,
            "version": PACKAGE_VERSION,
            "author": PACKAGE_AUTHOR,
        }
    )


@app.get("/health", tags=["meta"])
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Uvicorn entry-point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover - manual entry point
    import uvicorn

    cfg = get_config()
    host = cfg.raw.get("host") or "0.0.0.0"  # nosec B104 - external API
    port = int(cfg.raw.get("node_port") or 3001)
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
