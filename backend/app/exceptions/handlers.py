"""RFC7807-style error responses + handler registration."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx
from app.services.base import ServiceError

log = get_logger(__name__)


class AppError(Exception):
    status_code = 400
    title = "Application error"

    def __init__(self, detail: str = "", status_code: int | None = None):
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    title = "Not found"


class UnauthorizedError(AppError):
    status_code = 401
    title = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    title = "Forbidden"


def _problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "trace_id": request_id_ctx.get(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _problem(exc.status_code, exc.title, exc.detail)

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return _problem(400, "Service error", str(exc))

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        return _problem(400, "Bad request", str(exc))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", error=str(exc))
        return _problem(500, "Internal server error", "An unexpected error occurred")
