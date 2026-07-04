"""
Comparator — diffs two snapshots and returns a list of change events.

Events:
  BOOKING_OPEN      — bookings just became open
  MOVIE_APPEARING   — movie appeared on BMS for the first time
  MOVIE_NOW_SHOWING — movie moved from upcoming to now-showing section
  NEW_THEATRE       — a new theatre appeared
  NEW_FORMAT        — a new format appeared
  NEW_SHOW          — a new show time appeared
  PREFERRED_THEATRE — a preferred theatre appeared
  PREFERRED_FORMAT  — a preferred format appeared
  NO_CHANGE         — nothing meaningful changed
"""

from dataclasses import dataclass, field
from typing import Any

from logger import get_logger

logger = get_logger()


@dataclass
class ChangeEvent:
    """Represents a single meaningful change."""
    event_type: str          # one of the constants above
    detail: str = ""         # human-readable detail


def is_preferred_show(show: dict[str, Any]) -> bool:
    """Check if a show matches the configured preferred theatres and formats."""
    import config
    theatre = show.get("theatre", "")
    fmt = show.get("format", "")
    
    # Match theatre
    theatre_match = True
    if config.PREFERRED_THEATRES:
        theatre_match = any(kw.lower() in theatre.lower() for kw in config.PREFERRED_THEATRES)
        
    # Match format
    format_match = True
    if config.PREFERRED_FORMATS:
        format_match = any(kw.lower() in fmt.lower() for kw in config.PREFERRED_FORMATS)
        
    return theatre_match and format_match


def compare_snapshots(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> list[ChangeEvent]:
    """
    Compare two snapshots and return a list of ChangeEvents.
    Returns [ChangeEvent("NO_CHANGE")] if nothing meaningful changed.
    """
    import config
    events: list[ChangeEvent] = []

    # 0. Movie appeared for the first time on BMS
    if not previous.get("movie_found") and current.get("movie_found"):
        if not config.PREFERRED_THEATRES and not config.PREFERRED_FORMATS:
            events.append(ChangeEvent("MOVIE_APPEARING", "Spider-Man just appeared on BookMyShow!"))
            logger.info("Event: MOVIE_APPEARING")

    # 0b. Movie moved from upcoming to now-showing section
    prev_section = previous.get("movie_section", "")
    curr_section = current.get("movie_section", "")
    if prev_section == "upcoming" and curr_section == "now_showing":
        if not config.PREFERRED_THEATRES and not config.PREFERRED_FORMATS:
            events.append(ChangeEvent("MOVIE_NOW_SHOWING", "Movie moved to Now Showing section!"))
            logger.info("Event: MOVIE_NOW_SHOWING")

    # 1. Booking status
    if not previous.get("booking_open") and current.get("booking_open"):
        # If preferred configurations exist, only notify if we have at least one preferred show
        if not config.PREFERRED_THEATRES and not config.PREFERRED_FORMATS:
            events.append(ChangeEvent("BOOKING_OPEN", "Bookings just opened!"))
            logger.info("Event: BOOKING_OPEN")
        else:
            has_pref_shows = any(is_preferred_show(s) for s in current.get("shows", []))
            if has_pref_shows:
                events.append(ChangeEvent("BOOKING_OPEN", "Bookings just opened for preferred theatres/formats!"))
                logger.info("Event: BOOKING_OPEN (preferred)")

    # 2. New theatres (only preferred if list is set)
    prev_theatres = set(previous.get("theatres", []))
    curr_theatres = set(current.get("theatres", []))
    for theatre in sorted(curr_theatres - prev_theatres):
        if not config.PREFERRED_THEATRES or any(kw.lower() in theatre.lower() for kw in config.PREFERRED_THEATRES):
            events.append(ChangeEvent("NEW_THEATRE", theatre))
            logger.info("Event: NEW_THEATRE — %s", theatre)

    # 3. New formats (only preferred if list is set)
    prev_formats = set(previous.get("formats", []))
    curr_formats = set(current.get("formats", []))
    for fmt in sorted(curr_formats - prev_formats):
        if not config.PREFERRED_FORMATS or any(kw.lower() in fmt.lower() for kw in config.PREFERRED_FORMATS):
            events.append(ChangeEvent("NEW_FORMAT", fmt))
            logger.info("Event: NEW_FORMAT — %s", fmt)

    # 4. New shows (only preferred if list is set)
    prev_shows = _show_set(previous.get("shows", []))
    curr_shows = _show_set(current.get("shows", []))
    new_shows = curr_shows - prev_shows
    for show_key in sorted(new_shows):
        parts = show_key.split("|")
        show_dict = {
            "theatre": parts[0] if len(parts) > 0 else "",
            "time": parts[1] if len(parts) > 1 else "",
            "format": parts[2] if len(parts) > 2 else ""
        }
        if is_preferred_show(show_dict):
            events.append(ChangeEvent("NEW_SHOW", show_key))
            logger.info("Event: NEW_SHOW — %s", show_key)

    # 5. Preferred theatres newly appeared
    prev_pref_t = set(previous.get("preferred_theatres_found", []))
    curr_pref_t = set(current.get("preferred_theatres_found", []))
    for theatre in sorted(curr_pref_t - prev_pref_t):
        events.append(ChangeEvent("PREFERRED_THEATRE", theatre))
        logger.info("Event: PREFERRED_THEATRE — %s", theatre)

    # 6. Preferred formats newly appeared
    prev_pref_f = set(previous.get("preferred_formats_found", []))
    curr_pref_f = set(current.get("preferred_formats_found", []))
    for fmt in sorted(curr_pref_f - prev_pref_f):
        events.append(ChangeEvent("PREFERRED_FORMAT", fmt))
        logger.info("Event: PREFERRED_FORMAT — %s", fmt)

    if not events:
        logger.info("No meaningful changes detected.")
        return [ChangeEvent("NO_CHANGE")]

    return events


def _show_set(shows: list[dict]) -> set[str]:
    """Convert show dicts to a set of comparable strings."""
    result = set()
    for show in shows:
        key = f"{show.get('theatre','')}|{show.get('time','')}|{show.get('format','')}"
        result.add(key)
    return result
