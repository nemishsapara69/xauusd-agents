"""Logging setup for the backend."""

from __future__ import annotations

import logging

from .config import BACKEND_DIR

LOG_DIR = BACKEND_DIR / "logs"
LOG_FILE = LOG_DIR / "application.log"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure console and file logging once and return the app logger."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("xauusd")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    console_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger