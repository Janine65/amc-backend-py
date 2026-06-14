"""Global exception handlers (NestJS PrismaClientExceptionFilter equivalent)."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NoResultFound)
    async def not_found_handler(request: Request, exc: NoResultFound) -> JSONResponse:
        logger.info("NoResultFound on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "statusCode": status.HTTP_404_NOT_FOUND,
                "type": "error",
                "message": str(exc),
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        message = str(getattr(exc, "orig", exc)).split("\n")[0]
        logger.warning(
            "IntegrityError on %s %s: %s", request.method, request.url.path, message
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "statusCode": status.HTTP_409_CONFLICT,
                "type": "error",
                "message": message,
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqla_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "SQLAlchemyError on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "type": "error",
                "message": str(exc),
            },
        )
