"""
api/exceptions/handlers.py
----------------------------
Centralized exception handling. Every error response - whether it
originates from an api.exceptions.errors.APIError, an unhandled
service-layer exception, or a Pydantic validation failure - is
serialized into the same JSON shape:

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

Internal exception details (stack traces, raw exception messages from
unexpected failures) are never sent to the client - only APIError
subclasses and known, explicitly-mapped service exceptions produce a
message the caller sees; anything else becomes a generic 500 with the
request_id logged server-side for correlation.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.exceptions.errors import APIError, DomainValidationError, TooManyRequestsError
from services.storage.json_file_storage import StorageLockTimeout

logger = logging.getLogger("api.errors")


def _error_response(request: Request, *, status_code: int, code: str, message: str, extra: dict | None = None) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = {"error": {"code": code, "message": message, "request_id": request_id}}
    if extra:
        body["error"].update(extra)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(DomainValidationError)
    async def handle_domain_validation_error(request: Request, exc: DomainValidationError) -> JSONResponse:
        return _error_response(
            request, status_code=exc.status_code, code=exc.error_code, message=exc.message,
            extra={"field_errors": exc.field_errors},
        )

    @app.exception_handler(TooManyRequestsError)
    async def handle_too_many_requests(request: Request, exc: TooManyRequestsError) -> JSONResponse:
        response = _error_response(
            request, status_code=exc.status_code, code=exc.error_code, message=exc.message,
            extra={"retry_after_seconds": exc.retry_after_seconds} if exc.retry_after_seconds else None,
        )
        if exc.retry_after_seconds:
            response.headers["Retry-After"] = str(exc.retry_after_seconds)
        return response

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return _error_response(request, status_code=exc.status_code, code=exc.error_code, message=exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's own request-body validation failures (wrong types,
        # missing required fields) - distinct from ValidationService's
        # domain validation (out-of-range feature values), which routers
        # surface as a normal 200-with-errors ValidationResult or a
        # BadRequestError, not this handler.
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="request_validation_error",
            message=details or "Request validation failed.",
        )

    @app.exception_handler(StorageLockTimeout)
    async def handle_storage_lock_timeout(request: Request, exc: StorageLockTimeout) -> JSONResponse:
        """A stuck storage lock used to be invisible: the request simply
        never returned, and the only thing the user ever saw was a
        gateway timeout from whatever sat in front of the app - which
        points at the network and not at the lock. 503 with the actual
        sentence is the whole difference between "the site is broken"
        and "another copy of the app is still running"."""
        return _error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="storage_locked",
            message=str(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code="http_error",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled exception (request_id=%s)", request_id)
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="An unexpected error occurred.",
        )
