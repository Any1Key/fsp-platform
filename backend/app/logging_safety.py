"""Redact credentials and personal data at the Python logging boundary."""

from __future__ import annotations

import logging
import re
import traceback
from typing import Any

_BEARER_RE = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)([\"']?(?:authorization|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"(?:api|client|bot|db|database|keycloak|telegram|openai)[_-]?key|secret|password|token|"
    r"private[_-]?key)[\"']?\s*[:=]\s*[\"']?)([^\"'\s,;}]+)"
)
_URL_PASSWORD_RE = re.compile(r"(?i)(://[^/\s:@]+:)[^@\s]+(@)")
_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&](?:q|query|email|phone|contact|token|authorization|password|secret)=)[^&\s]+"
)


def redact_log_text(value: Any) -> str:
    """Return log-safe text without changing the surrounding diagnostic shape."""

    text = str(value)
    text = _BEARER_RE.sub(r"\1[REDACTED]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1[REDACTED]", text)
    text = _URL_PASSWORD_RE.sub(r"\1[REDACTED]\2", text)
    return _SENSITIVE_QUERY_RE.sub(r"\1[REDACTED]", text)


class SafeLogFilter(logging.Filter):
    """Remove secrets from messages, arguments and exception tracebacks."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = redact_log_text(record.getMessage())
        if record.exc_info:
            traceback_text = "".join(traceback.format_exception(*record.exc_info))
            message = f"{message}\n{redact_log_text(traceback_text)}"
            record.exc_info = None
            record.exc_text = None
        # Uvicorn's access formatter consumes a five-item args tuple to
        # render client, method, path, protocol and status. Keep that shape
        # while redacting each value; clearing args breaks every access log.
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            record.args = tuple(redact_log_text(value) if isinstance(value, str) else value for value in record.args)
        else:
            record.msg = message
            record.args = ()
        if record.stack_info:
            record.stack_info = redact_log_text(record.stack_info)
        return True


class SafeLogFormatter(logging.Formatter):
    """Formatter paired with :class:`SafeLogFilter` for direct use in tests/tools."""

    def format(self, record: logging.LogRecord) -> str:
        SafeLogFilter().filter(record)
        return super().format(record)


def install_safe_logging() -> None:
    """Attach the redaction filter to application and server log handlers.

    The application deliberately does not log request bodies. This filter is
    defense in depth for future diagnostics and for standard Uvicorn,
    SQLAlchemy and Alembic handlers that may be present at import time.
    """

    logger_names = (
        "",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy.engine",
        "alembic",
    )
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if not any(isinstance(item, SafeLogFilter) for item in handler.filters):
                handler.addFilter(SafeLogFilter())
