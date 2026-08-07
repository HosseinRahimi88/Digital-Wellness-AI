"""
api/middleware/request_context.py
-----------------------------------
Two small, dependency-free ASGI middlewares:

- RequestIDMiddleware: stamps every request with a UUID (reusing the
  client's X-Request-ID if it sent one), stores it on request.state for
  exception handlers/logging to read, and echoes it back in the
  response headers - the standard mechanism for correlating a client
  bug report with server logs.
- SecurityHeadersMiddleware: adds the small set of response headers
  that cost nothing and have no legitimate reason to be absent from a
  production API (nosniff, frame-deny, referrer policy). Not a
  replacement for a real WAF/CSP policy - deliberately minimal.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.core.logging_config import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rejects any request whose Content-Length exceeds
    Settings.max_request_body_bytes with 413, before the body is ever
    read into memory - a client sending gigabytes of JSON otherwise
    gets fully buffered before Pydantic (or anything else) gets a
    chance to reject it. Checks Content-Length up front (fast path,
    covers the overwhelming majority of real clients, which always
    send it); a client that omits Content-Length and streams an
    oversized body without it would bypass this specific check, but
    every uploadable/writable endpoint in this API (predict, what-if,
    reports, ...) reads the *entire* body into a single Pydantic model
    before any processing anyway - it never streams into a file, a
    database, or anything else where an unbounded, unannounced body
    could be independently damaging beyond the memory it consumes."""

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return Response(
                        content='{"error": {"code": "payload_too_large", "message": "Request body exceeds the maximum allowed size."}}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass  # malformed Content-Length - let normal request handling reject it
        return await call_next(request)
