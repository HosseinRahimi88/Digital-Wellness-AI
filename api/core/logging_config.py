"""
api/core/logging_config.py
-----------------------------
Structured (JSON) logging setup for the API process, plus the
request-ID propagation that lets any log line emitted during a
request's handling - including ones from services/ code this API
layer never modified - be correlated back to that request without
having to thread a request_id parameter through every function call.

Deliberately does not touch services/*.py's own `logging.getLogger(__name__)`
calls (already used consistently across the whole project, including by
the Streamlit app) - this module only changes how those same log
records get FORMATTED and OUTPUT when the process serving them is this
API, via the root logger's handlers/formatter. The Streamlit app's own
logging is untouched, since it configures logging independently (or
not at all) and never imports this module.
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import sys
from pathlib import Path

from api.core.config import Settings

# Set by RequestIDMiddleware at the start of every request, read by
# RequestIDLogFilter below so ANY log record emitted while handling
# that request - including from services/ modules this layer never
# touches - gets tagged with the same request_id that appears in the
# response's X-Request-ID header, without changing a single log call
# anywhere else in the codebase.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestIDLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """One JSON object per line - the format most log aggregators
    (CloudWatch, Datadog, Loki, plain `jq`) expect, and the format
    12-factor-style container deployments should emit to stdout."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    """Idempotent: safe to call more than once (e.g. once from the
    lifespan startup hook, and again if a test boots the app more than
    once in the same process) - clears any handlers this function
    itself previously added rather than stacking duplicates."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    for handler in list(root_logger.handlers):
        if getattr(handler, "_digital_wellness_api_handler", False):
            root_logger.removeHandler(handler)

    request_id_filter = RequestIDLogFilter()
    formatter = JSONFormatter()

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_id_filter)
    console_handler._digital_wellness_api_handler = True  # type: ignore[attr-defined]
    root_logger.addHandler(console_handler)

    if settings.log_to_file:
        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # 10 MB per file, 5 backups - bounded disk usage, no unbounded
        # log growth on a long-running bare-metal/VM deployment. In a
        # containerized deployment this is normally left off entirely
        # (LOG_TO_FILE unset) in favor of stdout-only, 12-factor style.
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5,
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_id_filter)
        file_handler._digital_wellness_api_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)

    # Uvicorn's own access/error loggers otherwise use their own
    # default formatter (plain text, no request_id) - route them
    # through the same handlers/formatter for consistent output.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
