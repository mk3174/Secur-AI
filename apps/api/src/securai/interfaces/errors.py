"""Exception handlers mapping domain errors to RFC 9457 problem+json."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from securai.shared.context import get_request_id
from securai.shared.errors import SecurAIError
from securai.shared.logging import get_logger

logger = get_logger("securai.errors")


def _problem(
    status: int, error_type: str, message: str, detail: dict | None = None
) -> JSONResponse:
    body = {
        "type": f"https://securai.dev/errors/{error_type}",
        "title": error_type,
        "status": status,
        "detail": message,
        "request_id": get_request_id(),
    }
    if detail:
        body["meta"] = detail
    headers = {}
    if status == 429 and detail and "retry_after_seconds" in detail:
        headers["Retry-After"] = str(detail["retry_after_seconds"])
    return JSONResponse(status_code=status, content=body, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SecurAIError)
    async def _securai_error(_: Request, exc: SecurAIError):
        if exc.status_code >= 500:
            logger.error("domain_error", error_type=exc.error_type, message=exc.message)
        return _problem(exc.status_code, exc.error_type, exc.message, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return _problem(
            422, "validation_error", "Request validation failed.", {"errors": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), error_class=type(exc).__name__)
        return _problem(500, "internal_error", "An unexpected error occurred.")
