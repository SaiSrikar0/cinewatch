"""
CineWatch Configuration
All application settings in one place. Edit this file to configure your monitoring.
"""

import os

# ---------------------------------------------------------------------------
# Movie & Location
# ---------------------------------------------------------------------------
MOVIE_NAME: str = os.getenv("MOVIE_NAME", "Spider-Man: Brand New Day")
CITY: str = os.getenv("CITY", "Hyderabad")

# BMS-specific identifiers (confirmed live on BMS as of 2026-07-04)
# These are stable — update if BMS changes the movie listing
BMS_EVENT_CODE: str = os.getenv("BMS_EVENT_CODE", "ET00502600")
BMS_MOVIE_SLUG: str = os.getenv("BMS_MOVIE_SLUG", "spiderman-brand-new-day-3d")

# ---------------------------------------------------------------------------
# Preferred Theatres  (partial match, case-insensitive)
# ---------------------------------------------------------------------------
PREFERRED_THEATRES: list[str] = [
    "Prasads",
    "Allu Cineplex",
]

# ---------------------------------------------------------------------------
# Preferred Formats  (keyword match inside format/screen name, case-insensitive)
# ---------------------------------------------------------------------------
PREFERRED_FORMATS: list[str] = [
    "PCX",
    "Barco",
    "3D",
    "Dolby",
]

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------
CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes

# ---------------------------------------------------------------------------
# Playwright
# ---------------------------------------------------------------------------
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
STEALTH: bool = os.getenv("STEALTH", "true").lower() == "true"  # playwright-stealth bypass
PAGE_TIMEOUT_MS: int = 30_000   # max wait for page elements (milliseconds)
BROWSER_LAUNCH_TIMEOUT_MS: int = 60_000

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
SNAPSHOT_FILE: str = os.getenv("SNAPSHOT_FILE", "snapshot.json")

# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------
MAX_SCRAPE_RETRIES: int = 3
RETRY_DELAY_SECONDS: int = 30
