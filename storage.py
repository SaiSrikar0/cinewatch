"""
Storage — read/write the snapshot JSON to disk.

Snapshot schema:
{
    "movie": "Spider-Man: Brand New Day",
    "city": "Hyderabad",
    "booking_open": false,
    "theatres": ["Prasads IMAX", "Allu Cineplex"],
    "formats": ["PCX", "Dolby Atmos"],
    "shows": [
        {"theatre": "Prasads IMAX", "time": "9:00 AM", "format": "PCX"}
    ],
    "last_updated": "2026-07-04T06:00:00"
}
"""

import json
import os
from datetime import datetime
from typing import Any

import config
from logger import get_logger

logger = get_logger()

EMPTY_SNAPSHOT: dict[str, Any] = {
    "movie": "",
    "city": "",
    "booking_open": False,
    "theatres": [],
    "formats": [],
    "shows": [],
    "last_updated": "",
}


def load_snapshot() -> dict[str, Any]:
    """Load the previous snapshot from disk. Returns empty snapshot if none exists."""
    path = config.SNAPSHOT_FILE
    if not os.path.exists(path):
        logger.info("No previous snapshot found. Starting fresh.")
        return dict(EMPTY_SNAPSHOT)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded snapshot from %s", path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load snapshot (%s). Starting fresh.", exc)
        return dict(EMPTY_SNAPSHOT)


def save_snapshot(snapshot: dict[str, Any]) -> None:
    """Persist the current snapshot to disk with a timestamp."""
    snapshot["last_updated"] = datetime.now().isoformat(timespec="seconds")
    try:
        with open(config.SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        logger.info("Snapshot saved to %s", config.SNAPSHOT_FILE)
    except OSError as exc:
        logger.error("Failed to save snapshot: %s", exc)
