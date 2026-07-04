"""
Logger setup — single call, consistent format across all modules.
"""

import logging
import sys


def get_logger(name: str = "cinewatch") -> logging.Logger:
    """Return a configured logger. Safe to call multiple times with the same name."""
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — don't add duplicate handlers
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (append mode — survives restarts)
    file_handler = logging.FileHandler("cinewatch.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
