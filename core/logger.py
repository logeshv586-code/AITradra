"""AXIOM Structured JSON Logging — every log entry is structured and parseable."""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach extra fields passed via logger.info("msg", extra={...})
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class ContextLogger(logging.Logger):
    """Logger with support for structured keyword arguments."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        if kwargs:
            extra = extra or {}
            extra["extra_data"] = kwargs
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel + 1)


def get_logger(name: str) -> ContextLogger:
    """Get a structured logger instance."""
    logging.setLoggerClass(ContextLogger)
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger
