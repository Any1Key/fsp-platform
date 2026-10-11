import io
import logging

from app.logging_safety import SafeLogFilter, SafeLogFormatter, redact_log_text


def _formatted_log(level: int, message: str, *args: object, exc_info=None) -> str:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SafeLogFilter())
    handler.setFormatter(SafeLogFormatter("%(levelname)s %(message)s"))
    logger = logging.getLogger("fsp.secret-audit")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        logger.log(level, message, *args, exc_info=exc_info)
        return stream.getvalue()
    finally:
        logger.removeHandler(handler)


def test_redact_log_text_covers_bearer_assignments_urls_and_search_queries():
    value = (
        "Authorization: Bearer eyJsecret.token.value, "
        "password=super-secret, "
        "DATABASE_URL=postgresql://fsp:db-password@app-db:5432/fsp, "
        "GET /radar?q=Alice%20Example"
    )

    redacted = redact_log_text(value)

    assert "eyJsecret.token.value" not in redacted
    assert "super-secret" not in redacted
    assert "db-password" not in redacted
    assert "Alice%20Example" not in redacted
    assert redacted.count("[REDACTED]") >= 4


def test_log_filter_redacts_format_arguments_and_exception_text():
    try:
        raise RuntimeError("token=exception-secret password=exception-password")
    except RuntimeError:
        output = _formatted_log(
            logging.ERROR,
            "request failed Authorization=%s",
            "Bearer argument-secret",
            exc_info=True,
        )

    assert "argument-secret" not in output
    assert "exception-secret" not in output
    assert "exception-password" not in output
    assert "[REDACTED]" in output
