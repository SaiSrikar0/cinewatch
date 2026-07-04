"""
Network interceptor — captures all API calls BMS makes internally
so we can identify the right endpoints to query directly.

Usage: python intercept_bms.py
"""

import json
import time
from playwright.sync_api import sync_playwright, Route, Request

CITY = "Hyderabad"
BMS_BASE = "https://in.bookmyshow.com"

captured_requests = []

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

        # Intercept all network requests
        def on_request(request: Request):
            url = request.url
            # Only capture API / XHR / JSON calls (not images/fonts/CSS)
            if any(x in url for x in [
                "api.", "/api/", "graphql", "/v1/", "/v2/", "/movies",
                "booking", "shows", "venues", "ticketing", "bms"
            ]):
                captured_requests.append({
                    "method": request.method,
                    "url": url,
                    "resource_type": request.resource_type,
                })

        page.on("request", on_request)
        page.set_default_timeout(30_000)

        # --- Load city page ---
        print(f"[1] Loading {BMS_BASE}/{CITY} ...")
        page.goto(f"{BMS_BASE}/{CITY}", wait_until="domcontentloaded")
        time.sleep(4)

        # --- Click Hyderabad city if city picker is open ---
        try:
            hyd_btn = page.query_selector("text=Hyderabad")
            if hyd_btn:
                hyd_btn.click()
                time.sleep(3)
                print("    Clicked Hyderabad")
        except Exception:
            pass

        page.screenshot(path="screenshot_after_city.png")
        print(f"    Title: {page.title()}")
        print(f"    URL: {page.url}")

        # --- Try clicking the search bar and typing the movie ---
        print("\n[2] Trying search bar interaction...")
        try:
            # Click the search icon/input
            search_selectors = [
                "input[placeholder*='Search']",
                "input[placeholder*='search']",
                "[data-testid='search-input']",
                ".search-bar input",
                "input[type='search']",
                "input[type='text']",
            ]
            clicked = False
            for sel in search_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    time.sleep(1)
                    el.type("Spider-Man", delay=80)  # human-like typing
                    time.sleep(3)  # wait for autocomplete
                    page.screenshot(path="screenshot_autocomplete.png", full_page=False)
                    print(f"    Typed in selector: {sel}")
                    print(f"    Screenshot: screenshot_autocomplete.png")
                    clicked = True
                    break

            if not clicked:
                # Try clicking the search icon
                icons = page.query_selector_all("svg, [class*='search']")
                print(f"    No input found. Found {len(icons)} SVG/search elements.")

        except Exception as e:
            print(f"    Search interaction failed: {e}")

        # --- Dump autocomplete anchors ---
        time.sleep(2)
        print("\n[3] Anchors with 'spider' after typing:")
        for a in page.query_selector_all("a"):
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip().replace("\n", " ")
            if "spider" in text.lower() or "spider" in href.lower():
                print(f"    [{text[:80]}] -> {href[:120]}")

        # --- Dump all captured API calls ---
        print(f"\n[4] Captured {len(captured_requests)} API requests:")
        for r in captured_requests:
            print(f"    [{r['method']}] {r['url'][:140]}")

        # Save for analysis
        with open("bms_api_calls.json", "w", encoding="utf-8") as f:
            json.dump(captured_requests, f, indent=2, ensure_ascii=False)
        print("    Saved to bms_api_calls.json")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
