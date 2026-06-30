"""Logging configuration for Debian Desktop Optimizer."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path.home() / ".local" / "state" / "ddo" / "logs"
_LOG_FILE = _LOG_DIR / "ddo.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5


def setup_logging(*, debug: bool = False, verbose: bool = False) -> None:
    """Configure root logger with rotating file handler and console handler."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Capture everything; handlers filter.

    # Rotating file handler — always at DEBUG level
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    # Console handler — respects the requested level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("ddo").setLevel(logging.DEBUG)


def get_log_path() -> Path:
    """Return path to the current log file."""
    return _LOG_FILE
