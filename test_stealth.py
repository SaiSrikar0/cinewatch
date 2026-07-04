"""
Stealth test — verify playwright-stealth bypasses BMS bot detection.
Usage: python test_stealth.py
"""

import time
import json
from playwright.sync_api import sync_playwright, Response
from playwright_stealth import Stealth

BMS_HOME = "https://in.bookmyshow.com"
intercepted = []

def run():
    # Use Stealth().use_sync() to wrap the entire playwright context
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
        page = context.new_page()

        def on_response(response: Response):
            url = response.url
            if "bookmyshow.com/api" in url and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        intercepted.append({"url": url, "body": body})
                        print(f"[API 200] {url[:100]}")
                except Exception:
                    pass

        page.on("response", on_response)
        page.set_default_timeout(30_000)

        print("[1] Navigating to BMS Hyderabad (stealth mode)...")
        page.goto(f"{BMS_HOME}/Hyderabad", wait_until="domcontentloaded")
        time.sleep(4)
        page.screenshot(path="stealth_test_1.png")
        print(f"    Title: {page.title()}")

        # Click city picker
        print("[2] Clicking Hyderabad...")
        hyd = page.query_selector("text=Hyderabad")
        if hyd:
            hyd.click()
            time.sleep(3)
        page.screenshot(path="stealth_test_2_after_city.png")
        body_text = page.inner_text("body")
        print(f"    Title: {page.title()}")

        if "bug-ging" in body_text.lower():
            print("    STILL SHOWING BUG PAGE")
        elif "spider" in body_text.lower():
            print("    *** Spider-Man found on page! ***")
        else:
            print("    Page OK — movie not listed yet (expected)")
            print(f"    Preview: {body_text[:400]}")

        # Click Movies
        print("\n[3] Clicking Movies nav...")
        movies = page.query_selector("a:has-text('Movies')")
        if movies:
            movies.click()
            time.sleep(4)
        page.screenshot(path="stealth_test_3_movies.png")
        body3 = page.inner_text("body")
        print(f"    Title: {page.title()}")
        if "bug-ging" in body3.lower():
            print("    BUG PAGE on movies section")
        else:
            print("    Movies page OK")
            print(f"    Preview: {body3[:400]}")

        # Show intercepted APIs
        print(f"\n[4] Intercepted {len(intercepted)} JSON API responses:")
        for r in intercepted:
            body_str = json.dumps(r["body"])
            spider_flag = " *** SPIDER-MAN ***" if "spider" in body_str.lower() else ""
            print(f"    {r['url'][:100]}{spider_flag}")

        browser.close()
        print("\nDone. Check stealth_test_*.png")

if __name__ == "__main__":
    run()
