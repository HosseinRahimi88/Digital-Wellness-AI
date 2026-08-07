"""
api/exceptions/errors.py
-------------------------
API-layer exception types. These wrap (never replace) the existing
service-layer exceptions - routers catch a service exception once, at
the boundary, and translate it into one of these so every error
response has a consistent shape. Business logic never raises these
directly; only routers do.
"""

from __future__ import annotations


class APIError(Exception):
    """Base class for every API-layer error. Carries the HTTP status
    code and a machine-readable error code alongside the human message,
    so api/exceptions/handlers.py can serialize all of them uniformly."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, error_code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(APIError):
    status_code = 400
    error_code = "bad_request"


class UnauthorizedError(APIError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(APIError):
    status_code = 403
    error_code = "forbidden"


class NotFoundError(APIError):
    status_code = 404
    error_code = "not_found"


class ConflictError(APIError):
    status_code = 409
    error_code = "conflict"


class UnprocessableEntityError(APIError):
    status_code = 422
    error_code = "unprocessable_entity"


class DomainValidationError(APIError):
    """Raised when ValidationService (the existing, authoritative
    feature-schema validator) rejects a payload. Carries the same
    per-field error dict ValidationResult.errors already produces -
    the API layer does not reinterpret or re-derive these messages,
    only relays them."""

    status_code = 422
    error_code = "validation_failed"

    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("One or more fields failed validation.")
        self.field_errors = field_errors


class ServiceUnavailableError(APIError):
    status_code = 503
    error_code = "service_unavailable"
