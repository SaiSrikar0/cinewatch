"""
Notifier — sends Telegram messages when meaningful changes are detected.

Duplicate prevention: tracks which event keys have already been notified
in memory (resets on restart). For production, persist sent events in JSON.
"""

import json
import os
from typing import Any

import httpx  # lightweight HTTP client (no requests needed for simple POSTs)

import config
from comparator import ChangeEvent
from logger import get_logger

logger = get_logger()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Tracks already-notified event keys (theatre+format+time combos)
# Persisted to disk so restarts don't cause duplicate notifications.
NOTIFIED_FILE = "notified.json"


def _load_notified() -> set[str]:
    if not os.path.exists(NOTIFIED_FILE):
        return set()
    try:
        with open(NOTIFIED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:  # noqa: BLE001
        return set()


def _save_notified(notified: set[str]) -> None:
    try:
        with open(NOTIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(notified), f, indent=2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save notified set: %s", exc)


def notify(events: list[ChangeEvent], snapshot: dict[str, Any]) -> None:
    """
    For each change event, send a Telegram notification (if not already sent).
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured. Skipping notification.")
        return

    notified = _load_notified()
    sent_any = False

    for event in events:
        if event.event_type == "NO_CHANGE":
            continue

        # Build a unique key to deduplicate
        key = f"{event.event_type}::{event.detail}"
        if key in notified:
            logger.info("Duplicate notification skipped: %s", key)
            continue

        message = _build_message(event, snapshot)
        success = _send_telegram(message)

        if success:
            notified.add(key)
            sent_any = True
            logger.info("Notification sent: %s", key)

    if sent_any:
        _save_notified(notified)


def _build_message(event: ChangeEvent, snapshot: dict[str, Any]) -> str:
    """Format a human-readable Telegram message for the given event."""
    movie = snapshot.get("movie", config.MOVIE_NAME)
    url = snapshot.get("source_url", "https://in.bookmyshow.com")

    lines = [f"🎬 *{movie}*"]

    if event.event_type == "BOOKING_OPEN":
        lines.append("🚨 *BOOKINGS ARE NOW OPEN!*")

    elif event.event_type == "MOVIE_APPEARING":
        lines.append("\u2728 Movie just appeared on BookMyShow!")
        lines.append("📍 It may not be bookable yet — keep watching.")

    elif event.event_type == "MOVIE_NOW_SHOWING":
        lines.append("🎬 Movie moved to *Now Showing* section!")
        lines.append("🚨 Bookings may open very soon.")

    elif event.event_type == "PREFERRED_THEATRE":
        lines.append(f"📍 Preferred theatre detected: *{event.detail}*")

    elif event.event_type == "PREFERRED_FORMAT":
        lines.append(f"🎥 Preferred format detected: *{event.detail}*")

    elif event.event_type == "NEW_THEATRE":
        lines.append(f"🏟 New theatre: *{event.detail}*")

    elif event.event_type == "NEW_FORMAT":
        lines.append(f"🖥 New format: *{event.detail}*")

    elif event.event_type == "NEW_SHOW":
        parts = event.detail.split("|")
        theatre = parts[0] if len(parts) > 0 else ""
        time_str = parts[1] if len(parts) > 1 else ""
        fmt = parts[2] if len(parts) > 2 else ""
        if theatre:
            lines.append(f"📍 {theatre}")
        if fmt:
            lines.append(f"🎥 {fmt}")
        if time_str:
            lines.append(f"🕘 {time_str}")

    lines.append(f"\n👉 [Open BookMyShow]({url})")
    return "\n".join(lines)


def _send_telegram(message: str) -> bool:
    """POST the message to Telegram Bot API. Returns True on success."""
    url = TELEGRAM_API.format(token=config.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        response = httpx.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        logger.error("Telegram API error %s: %s", exc.response.status_code, exc.response.text)
    except httpx.RequestError as exc:
        logger.error("Telegram request failed: %s", exc)
    return False
