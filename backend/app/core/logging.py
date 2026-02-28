# backend/app/core/logging.py
"""
Structured logging configuration for production environments.
Supports JSON format for log aggregation systems.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields for production logging.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add application metadata
        log_record["service"] = settings.APP_NAME
        log_record["version"] = settings.APP_VERSION
        log_record["environment"] = settings.ENVIRONMENT

        # Add log level
        log_record["level"] = record.levelname

        # Add source information
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno


def setup_logging() -> None:
    """
    Configure application-wide logging.
    Uses JSON format in production, standard format in development.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if settings.LOG_FORMAT == "json":
        # JSON formatting for production
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        # Standard formatting for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


class RequestLogger:
    """
    Context manager for request-scoped logging.
    """

    def __init__(self, request_id: str, user_id: str = None):
        self.request_id = request_id
        self.user_id = user_id
        self.logger = logging.getLogger("request")

    def info(self, message: str, **kwargs):
        self.logger.info(
            message,
            extra={"request_id": self.request_id,
                   "user_id": self.user_id, **kwargs}
        )

    def error(self, message: str, **kwargs):
        self.logger.error(
            message,
            extra={"request_id": self.request_id,
                   "user_id": self.user_id, **kwargs}
        )

    def warning(self, message: str, **kwargs):
        self.logger.warning(
            message,
            extra={"request_id": self.request_id,
                   "user_id": self.user_id, **kwargs}
        )
