"""
Quick scraper test — run once, print raw output, exit.
Usage: python test_scraper.py
"""

import json
from scraper import scrape_movie
from parser import build_snapshot

print("=" * 60)
print("CineWatch — Scraper Test")
print("=" * 60)

raw = scrape_movie("Spider-Man: Brand New Day", "Hyderabad")

print("\n--- RAW SCRAPER OUTPUT ---")
print(json.dumps(raw, indent=2))

snapshot = build_snapshot(raw)
print("\n--- PARSED SNAPSHOT ---")
print(json.dumps(snapshot, indent=2))
