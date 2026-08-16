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


class AlreadyCheckedInError(ConflictError):
    """Today already has a recorded check-in.

    Refusing is the point: HistoryService.record() upserts, so allowing
    a second persisted submission silently destroyed the first day's
    real result. The client re-sends with allow_update once the user has
    explicitly said they are editing today rather than adding a day.
    """

    error_code = "already_checked_in_today"

    def __init__(self, day: str) -> None:
        super().__init__(
            f"A check-in for {day} is already recorded. Enable editing to "
            f"replace it - submitting again would overwrite the result "
            f"already saved for today.",
        )
        self.day = day


class DayLockedError(ConflictError):
    """A plan day that is not open yet.

    The week is a sequence: day N+1 opens once day N is fully done.
    Enforced on the server as well as in the UI, because a locked day
    that a direct request can tick anyway is not locked - and "you
    missed a day" only means something if the days had to be done in
    order.
    """

    error_code = "plan_day_locked"

    def __init__(self, day_number: int, unlocked_through: int) -> None:
        super().__init__(
            f"Day {day_number} is not open yet - finish day {unlocked_through} "
            f"first. The week runs in order, one day at a time.",
        )
        self.day_number = day_number
        self.unlocked_through = unlocked_through


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


class TooManyRequestsError(APIError):
    status_code = 429
    error_code = "too_many_requests"

    def __init__(self, message: str, *, error_code: str | None = None, retry_after_seconds: int | None = None) -> None:
        super().__init__(message, error_code=error_code)
        self.retry_after_seconds = retry_after_seconds


class ServiceUnavailableError(APIError):
    status_code = 503
    error_code = "service_unavailable"
