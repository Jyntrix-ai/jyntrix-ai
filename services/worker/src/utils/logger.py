"""
Logging Configuration Module

Provides structured logging for the worker with JSON formatting for production
and human-readable formatting for development.
"""

import logging
import sys
from datetime import UTC, datetime
from typing import Any

from src.config import config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json

        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "memory_id"):
            log_data["memory_id"] = record.memory_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for development environment."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # Format timestamp
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        base_msg = f"{timestamp} | {record.levelname:18} | {record.name} | {record.getMessage()}"

        # Add extra context if present
        extras = []
        if hasattr(record, "task_id"):
            extras.append(f"task_id={record.task_id}")
        if hasattr(record, "user_id"):
            extras.append(f"user_id={record.user_id}")
        if hasattr(record, "memory_id"):
            extras.append(f"memory_id={record.memory_id}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")

        if extras:
            base_msg += f" [{', '.join(extras)}]"

        # Add exception info if present
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"

        return base_msg


def setup_logging() -> None:
    """Configure logging for the worker application."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.log_level))

    # Select formatter based on environment
    if config.is_production:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name, typically __name__ from the calling module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class TaskLogger:
    """Context manager for task-specific logging with timing."""

    def __init__(
        self,
        logger: logging.Logger,
        task_name: str,
        task_id: str | None = None,
        user_id: str | None = None,
        **extra: Any,
    ) -> None:
        self.logger = logger
        self.task_name = task_name
        self.task_id = task_id
        self.user_id = user_id
        self.extra = extra
        self.start_time: float | None = None

    def __enter__(self) -> "TaskLogger":
        import time

        self.start_time = time.perf_counter()
        self.logger.info(
            f"Starting task: {self.task_name}",
            extra={
                "task_id": self.task_id,
                "user_id": self.user_id,
                **self.extra,
            },
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        import time

        duration_ms = int((time.perf_counter() - (self.start_time or 0)) * 1000)

        if exc_type is not None:
            self.logger.error(
                f"Task failed: {self.task_name} - {exc_val}",
                extra={
                    "task_id": self.task_id,
                    "user_id": self.user_id,
                    "duration_ms": duration_ms,
                    **self.extra,
                },
                exc_info=True,
            )
        else:
            self.logger.info(
                f"Task completed: {self.task_name}",
                extra={
                    "task_id": self.task_id,
                    "user_id": self.user_id,
                    "duration_ms": duration_ms,
                    **self.extra,
                },
            )

    def log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log a message with task context."""
        self.logger.log(
            level,
            message,
            extra={
                "task_id": self.task_id,
                "user_id": self.user_id,
                **self.extra,
                **kwargs,
            },
        )
