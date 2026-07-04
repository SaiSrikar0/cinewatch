"""
Parser — takes raw scrape output and converts it into a normalized snapshot.

Also handles preferred theatre/format matching.
"""

from typing import Any

import config
from logger import get_logger

logger = get_logger()


def build_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert raw scraper output into a canonical snapshot dict.

    Args:
        raw: dict returned by scraper.scrape_movie()

    Returns:
        Normalized snapshot ready for comparison and storage.
    """
    theatres = [t.strip() for t in raw.get("theatres", []) if t.strip()]
    formats = [f.strip() for f in raw.get("formats", []) if f.strip()]
    shows = raw.get("shows", [])

    preferred_theatres_found = _match_preferred(theatres, config.PREFERRED_THEATRES)
    preferred_formats_found = _match_preferred(formats, config.PREFERRED_FORMATS)

    # movie_section: "not_listed" | "upcoming" | "listed" | "now_showing"
    movie_section = raw.get("movie_section", "unknown")
    movie_found = raw.get("movie_found", False)

    # Booking is open if either the page detected a button OR the section confirms it
    booking_open = bool(raw.get("booking_open", False))

    snapshot: dict[str, Any] = {
        "movie": config.MOVIE_NAME,
        "city": config.CITY,
        "event_code": config.BMS_EVENT_CODE,
        "booking_open": booking_open,
        "movie_found": movie_found,
        "movie_section": movie_section,
        "theatres": sorted(theatres),
        "formats": sorted(formats),
        "shows": shows,
        "preferred_theatres_found": sorted(preferred_theatres_found),
        "preferred_formats_found": sorted(preferred_formats_found),
        "source_url": raw.get("raw_url", ""),
    }

    logger.info(
        "Snapshot built | found=%s | section=%s | booking_open=%s | preferred_theatres=%s | preferred_formats=%s",
        snapshot["movie_found"],
        snapshot["movie_section"],
        snapshot["booking_open"],
        snapshot["preferred_theatres_found"],
        snapshot["preferred_formats_found"],
    )
    return snapshot


def _match_preferred(items: list[str], preferred: list[str]) -> list[str]:
    """
    Return items that contain any of the preferred keywords (case-insensitive).

    Example:
        items     = ["Prasads PCX", "INOX", "Allu Cineplex"]
        preferred = ["Prasads", "Allu"]
        → ["Prasads PCX", "Allu Cineplex"]
    """
    matched: list[str] = []
    for item in items:
        item_lower = item.lower()
        for keyword in preferred:
            if keyword.lower() in item_lower:
                matched.append(item)
                break
    return matched
