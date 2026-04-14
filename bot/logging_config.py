"""
Logging configuration for the trading bot.
Sets up structured logging to both console and a rotating log file.
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
BACKUP_COUNT = 3               # keep 3 rotated files


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure root logger with:
      - Console handler  (WARNING and above, concise format)
      - Rotating file handler (DEBUG and above, full detail)

    Returns the package-level logger ``trading_bot``.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── root logger ────────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)          # let handlers decide their own floor

    if root.handlers:                     # avoid duplicate handlers on re-import
        return logging.getLogger("trading_bot")

    # ── formats ────────────────────────────────────────────────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_fmt = logging.Formatter(
        fmt="%(levelname)-8s %(message)s",
    )

    # ── file handler (rotating) ────────────────────────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)

    # ── console handler ─────────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(console_fmt)

    root.addHandler(fh)
    root.addHandler(ch)

    return logging.getLogger("trading_bot")
