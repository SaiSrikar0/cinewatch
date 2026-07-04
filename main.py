"""
CineWatch — Entry Point

Usage:
    python main.py
    docker compose up
"""

import sys

from logger import get_logger
from scheduler import start_scheduler

logger = get_logger()


def main() -> None:
    logger.info("CineWatch starting up.")
    logger.info("Monitoring: %s", _import_config())
    start_scheduler()


def _import_config() -> str:
    import config
    return (
        f"movie='{config.MOVIE_NAME}' | city='{config.CITY}' | "
        f"interval={config.CHECK_INTERVAL_SECONDS}s | headless={config.HEADLESS}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)
