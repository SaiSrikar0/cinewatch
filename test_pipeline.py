"""
Full pipeline test — runs one complete cycle without scheduler:
scrape → parse → compare → (would notify) → save

Does NOT send a real Telegram message. Just validates the whole flow.
Usage: python test_pipeline.py
"""

import json
from scraper import scrape_movie
from parser import build_snapshot
from comparator import compare_snapshots
from storage import load_snapshot, save_snapshot
import config

print("=" * 60)
print("CineWatch — Full Pipeline Test")
print("=" * 60)

# 1. Scrape
print("\n[1] Scraping...")
raw = scrape_movie(config.MOVIE_NAME, config.CITY)

# 2. Parse
print("\n[2] Building snapshot...")
current = build_snapshot(raw)

# 3. Compare
print("\n[3] Comparing with previous snapshot...")
previous = load_snapshot()
events = compare_snapshots(previous, current)

print("\n--- EVENTS ---")
for e in events:
    print(f"  {e.event_type}: {e.detail}")

# 4. Save
print("\n[4] Saving snapshot...")
save_snapshot(current)

print("\n--- FINAL SNAPSHOT ---")
print(json.dumps(current, indent=2))

print("\nPipeline test complete.")
