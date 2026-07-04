"""
Scheduler — runs the check loop using APScheduler.

One job: check_movie()
  Calls: scraper → parser → comparator → notifier → storage

Retry logic: built into the job itself (not APScheduler misfire handling).
"""

import time

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from comparator import compare_snapshots
from logger import get_logger
from notifier import notify
from parser import build_snapshot
from scraper import scrape_movie
from storage import load_snapshot, save_snapshot

logger = get_logger()


def check_movie() -> None:
    """
    Main job: scrape → parse → compare → notify → save.
    Wrapped in retry logic to survive transient failures.
    """
    logger.info("=" * 60)
    logger.info("Starting scan for '%s' in %s", config.MOVIE_NAME, config.CITY)

    raw = _scrape_with_retry()
    if raw is None:
        logger.error("Scrape failed after %d retries. Will try again next interval.", config.MAX_SCRAPE_RETRIES)
        return

    current_snapshot = build_snapshot(raw)
    previous_snapshot = load_snapshot()

    events = compare_snapshots(previous_snapshot, current_snapshot)

    has_real_changes = any(e.event_type != "NO_CHANGE" for e in events)
    if has_real_changes:
        notify(events, current_snapshot)
        save_snapshot(current_snapshot)
    else:
        logger.info("No changes. Sleeping until next check.")
        # Still update snapshot so last_updated is fresh
        save_snapshot(current_snapshot)

    logger.info("Scan complete. Next check in %ds.", config.CHECK_INTERVAL_SECONDS)


def _scrape_with_retry() -> dict | None:
    """Retry scraping up to MAX_SCRAPE_RETRIES times."""
    for attempt in range(1, config.MAX_SCRAPE_RETRIES + 1):
        try:
            logger.info("Scrape attempt %d/%d", attempt, config.MAX_SCRAPE_RETRIES)
            raw = scrape_movie(config.MOVIE_NAME, config.CITY)
            return raw
        except Exception as exc:  # noqa: BLE001
            logger.warning("Scrape attempt %d failed: %s", attempt, exc)
            if attempt < config.MAX_SCRAPE_RETRIES:
                logger.info("Waiting %ds before retry...", config.RETRY_DELAY_SECONDS)
                time.sleep(config.RETRY_DELAY_SECONDS)
    return None


def start_scheduler() -> None:
    """
    Start the APScheduler blocking scheduler.
    Runs check_movie() immediately on startup, then every CHECK_INTERVAL_SECONDS.
    """
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        check_movie,
        trigger="interval",
        seconds=config.CHECK_INTERVAL_SECONDS,
        id="check_movie",
        name="BookMyShow Movie Check",
        next_run_time=__import__("datetime").datetime.now(),  # run immediately on start
        max_instances=1,  # prevent overlap if a job runs long
        coalesce=True,
    )

    logger.info(
        "Scheduler started. Checking every %ds for '%s' in %s.",
        config.CHECK_INTERVAL_SECONDS,
        config.MOVIE_NAME,
        config.CITY,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
