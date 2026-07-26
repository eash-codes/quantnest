"""Structured logging configuration.

Emits JSON in production (``LOG_FORMAT=json``, the default) so logs are
machine-parseable, and a readable console format during development.

Replaces the 21 ``print()`` calls that previously served as logging.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

#: Correlation ID for the in-flight request, set by the API middleware.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Attributes present on every LogRecord; anything else is a caller-supplied extra.
_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info",
    "thread", "threadName", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render each record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value if _is_jsonable(value) else str(value)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Compact human-readable format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        base = f"{timestamp} {record.levelname:<8} {record.name:<32} {record.getMessage()}"

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        }
        if extras:
            base += "  " + " ".join(f"{k}={v}" for k, v in extras.items())

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def _is_jsonable(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None), list, dict))


def configure_logging(level: str | None = None, fmt: str | None = None) -> None:
    """Install the root logging configuration.

    Args:
        level: ``LOG_LEVEL`` override (default ``INFO``).
        fmt: ``json`` or ``console`` (``LOG_FORMAT``, default ``json``).
    """
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    fmt = (fmt or os.getenv("LOG_FORMAT", "json")).lower()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if fmt == "json" else ConsoleFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # yfinance and urllib3 are extremely chatty at INFO.
    logging.getLogger("yfinance").setLevel(logging.ERROR)
    logging.getLogger("peewee").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
