"""
Diagnostic script — navigates to BMS search page, takes a screenshot,
dumps all anchor tags and page text so we can reverse-engineer the selectors.

Usage: python diagnose_bms.py
"""

import json
import time
from playwright.sync_api import sync_playwright

MOVIE = "Spider-Man: Brand New Day"
CITY = "Hyderabad"
BMS_BASE = "https://in.bookmyshow.com"

def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        # Step 1: City homepage
        print("\n[1] Loading city homepage...")
        page.goto(f"{BMS_BASE}/{CITY}", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="screenshot_city.png", full_page=False)
        print("    Screenshot saved: screenshot_city.png")
        print(f"    Title: {page.title()}")

        # Step 2: Search page
        search_url = f"{BMS_BASE}/search?q={MOVIE.replace(' ', '%20')}&category=movies"
        print(f"\n[2] Loading search page: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(4)  # give React time to render
        page.screenshot(path="screenshot_search.png", full_page=True)
        print("    Screenshot saved: screenshot_search.png")
        print(f"    Title: {page.title()}")
        print(f"    URL: {page.url}")

        # Step 3: Dump ALL anchor hrefs + visible text
        print("\n[3] All anchor tags on search page:")
        anchors = page.query_selector_all("a")
        found = []
        for a in anchors:
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip().replace("\n", " ")
            if href:
                found.append({"text": text[:80], "href": href[:120]})
        for item in found:
            print(f"    [{item['text']}] → {item['href']}")

        # Step 4: Look for Spider-Man specifically
        print(f"\n[4] Anchors containing 'spider':")
        for item in found:
            if "spider" in item["text"].lower() or "spider" in item["href"].lower():
                print(f"    MATCH: [{item['text']}] → {item['href']}")

        # Step 5: Dump page body text (first 3000 chars)
        print("\n[5] Page body text (first 3000 chars):")
        body_text = page.inner_text("body")
        print(body_text[:3000])

        # Step 6: Try the "explore" / "movies" page for Hyderabad
        movies_url = f"{BMS_BASE}/movies/hyderabad"
        print(f"\n[6] Loading movies listing: {movies_url}")
        page.goto(movies_url, wait_until="domcontentloaded")
        time.sleep(4)
        page.screenshot(path="screenshot_movies.png", full_page=False)
        print("    Screenshot saved: screenshot_movies.png")
        print(f"    Title: {page.title()}")

        anchors2 = page.query_selector_all("a")
        print("\n[7] Anchors containing 'spider' on movies page:")
        for a in anchors2:
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip().replace("\n", " ")
            if "spider" in text.lower() or "spider" in href.lower():
                print(f"    MATCH: [{text[:80]}] → {href[:120]}")

        # Step 7: Save all search page anchors to JSON for analysis
        with open("bms_anchors.json", "w", encoding="utf-8") as f:
            json.dump(found, f, indent=2, ensure_ascii=False)
        print("\n    All search anchors saved to bms_anchors.json")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
