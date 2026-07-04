"""
CineWatch — Entry Point

Usage:
    python main.py
    docker compose up
"""

import sys
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

from logger import get_logger
from scheduler import start_scheduler

logger = get_logger()


def start_health_check_server() -> None:
    """Run a basic HTTP server to pass Render's health checks."""
    port = int(os.getenv("PORT", "8080"))
    server_address = ('', port)
    
    class HealthHandler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args) -> None:
            # Suppress default server logs to keep output clean
            pass

    try:
        httpd = HTTPServer(server_address, HealthHandler)
        logger.info("Health check server started on port %d", port)
        httpd.serve_forever()
    except Exception as e:
        logger.error("Failed to start health check server: %s", e)


def main() -> None:
    logger.info("CineWatch starting up.")
    logger.info("Monitoring: %s", _import_config())
    
    # Start health check server in a background thread
    server_thread = threading.Thread(target=start_health_check_server, daemon=True)
    server_thread.start()
    
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
