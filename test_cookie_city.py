"""
Cookie-based city test: set city cookie manually and navigate directly
to avoid city picker interaction which triggers discover API call.

Also tests non-headless mode to verify scraper logic is sound.

Usage: python test_cookie_city.py
"""

import time
import json
from playwright.sync_api import sync_playwright, Response
from playwright_stealth import Stealth

BMS_HOME = "https://in.bookmyshow.com"
intercepted = []

def run():
    with Stealth().use_sync(sync_playwright()) as pw:
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
            viewport={"width": 1280, "height": 800},
        )

        # ---- Pre-set city cookie to bypass city picker ----
        # BMS stores city selection as a cookie on the domain
        context.add_cookies([
            {
                "name": "Hyderabad",
                "value": "Hyderabad",
                "domain": ".bookmyshow.com",
                "path": "/",
            },
            {
                "name": "selectedCity",
                "value": "Hyderabad",
                "domain": ".bookmyshow.com",
                "path": "/",
            },
            {
                "name": "city",
                "value": "Hyderabad",
                "domain": ".bookmyshow.com",
                "path": "/",
            },
        ])

        page = context.new_page()

        def on_response(response: Response):
            url = response.url
            if "bookmyshow.com/api" in url and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        intercepted.append({"url": url, "body": body})
                        body_str = json.dumps(body)
                        spider_flag = " ***SPIDER-MAN***" if "spider" in body_str.lower() else ""
                        print(f"[API 200] {url[:100]}{spider_flag}")
                except Exception:
                    pass
            elif "bookmyshow.com/api" in url and response.status != 200:
                print(f"[API {response.status}] {url[:100]}")

        page.on("response", on_response)
        page.set_default_timeout(30_000)

        # Strategy 1: Navigate directly to explore/home/hyderabad
        print("[1] Direct navigate to /explore/home/hyderabad ...")
        page.goto(f"{BMS_HOME}/explore/home/hyderabad", wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path="cookie_test_1.png")
        body = page.inner_text("body")
        print(f"    Title: {page.title()}")
        if "bug-ging" in body.lower():
            print("    BUG PAGE")
        else:
            print(f"    OK. Preview: {body[:300]}")

        # Strategy 2: Navigate to /movies/hyderabad directly
        print("\n[2] Direct navigate to /movies/hyderabad ...")
        page.goto(f"{BMS_HOME}/movies/hyderabad", wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path="cookie_test_2.png")
        body2 = page.inner_text("body")
        print(f"    Title: {page.title()}")
        if "bug-ging" in body2.lower():
            print("    BUG PAGE")
        elif "unavailable" in body2.lower():
            print("    UNAVAILABLE PAGE")
        else:
            print(f"    OK. Preview: {body2[:300]}")

        # Strategy 3: Check if actual movie pages load (any currently showing movie)
        # Try a known current movie
        print("\n[3] Testing a known movie page (Minions & Monsters) ...")
        page.goto(f"{BMS_HOME}/movies/minions-and-monsters/ET00414677", wait_until="domcontentloaded")
        time.sleep(4)
        page.screenshot(path="cookie_test_3_known_movie.png")
        body3 = page.inner_text("body")
        print(f"    Title: {page.title()}")
        if "bug-ging" in body3.lower():
            print("    BUG PAGE")
        elif "book" in body3.lower() or "ticket" in body3.lower():
            print("    MOVIE PAGE LOADED CORRECTLY!")
            print(f"    Preview: {body3[:400]}")
        else:
            print(f"    Other: {body3[:300]}")

        print(f"\n[4] Total intercepted APIs: {len(intercepted)}")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
