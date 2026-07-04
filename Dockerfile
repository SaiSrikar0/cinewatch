# ---- Build stage ----
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy AS base

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers are already installed in the base image.
# If using a plain python image, you'd run:
#   RUN playwright install --with-deps chromium

# Copy application code
COPY *.py ./

# Data directory (snapshot + log files land here via volume mount)
VOLUME ["/app/data"]

# Default env — override in docker-compose or docker run -e
ENV PYTHONUNBUFFERED=1 \
    HEADLESS=true \
    CHECK_INTERVAL_SECONDS=300 \
    SNAPSHOT_FILE=/app/data/snapshot.json

CMD ["python", "main.py"]
