import logging
import re
import sys
from typing import Any

from app.config import settings

SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"(api[_\-]?key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"(bot\d+:)[A-Za-z0-9_\-]{25,}", re.IGNORECASE),
    re.compile(r"(client_secret[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"(refresh_token[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
]


class SanitizingFilter(logging.Filter):
    """Filter that strips out sensitive keys, tokens, and authorization headers from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in SECRET_PATTERNS:
                record.msg = pattern.sub(r"\1[REDACTED]", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                sanitized_dict = {}
                for k, v in record.args.items():
                    if any(secret_term in str(k).lower() for secret_term in ["token", "key", "secret", "auth", "password"]):
                        sanitized_dict[k] = "[REDACTED]"
                    else:
                        sanitized_dict[k] = v
                record.args = sanitized_dict
            elif isinstance(record.args, tuple):
                record.args = tuple("[REDACTED]" if any(secret_term in str(arg).lower() for secret_term in ["token", "key", "secret", "auth", "password"]) else arg for arg in record.args)
        return True


def setup_logging() -> None:
    """Configures application-wide logging format, level, and redaction filters."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SanitizingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Suppress verbose 3rd party logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
