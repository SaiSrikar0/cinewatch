"""
BMS Navigation Strategy Test

Since Cloudflare blocks:
  - Direct /search URL navigation
  - JS fetch() calls from headless browser

Strategy: Navigate via the UI naturally.
  1. Go to /movies/hyderabad (movies listing page)
  2. Intercept API responses at network level (before Cloudflare JS challenge)
  3. Find movie in page HTML
  4. Navigate to movie page
  5. Extract show data from page HTML

Usage: python test_navigation.py
"""

import json
import time
from playwright.sync_api import sync_playwright

BMS_BASE = "https://in.bookmyshow.com"
MOVIE = "Spider-Man: Brand New Day"

# Intercept API responses at network level
intercepted_api_responses = []

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

        # Intercept all responses containing JSON from BMS APIs
        def handle_response(response):
            url = response.url
            if "bookmyshow.com/api" in url and response.status == 200:
                try:
                    body = response.text()
                    if body and len(body) > 10:
                        intercepted_api_responses.append({
                            "url": url,
                            "status": response.status,
                            "body_preview": body[:300],
                            "has_spider": "spider" in body.lower() or "brand new day" in body.lower(),
                        })
                except Exception:
                    pass

        page.on("response", handle_response)

        # ----------------------------------------------------------------
        # Step 1: Load movies page for Hyderabad
        # ----------------------------------------------------------------
        movies_url = f"{BMS_BASE}/movies/hyderabad"
        print(f"[1] Navigating to: {movies_url}")
        page.goto(movies_url, wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path="nav_test_1_movies.png", full_page=False)
        print(f"    Title: {page.title()}")
        print(f"    URL: {page.url}")

        # Check if Spider-Man appears anywhere
        body_text = page.inner_text("body")
        if "spider" in body_text.lower():
            print("    *** Spider-Man found on movies page! ***")
        else:
            print("    Spider-Man NOT found on movies page (not released yet?)")
            print(f"    Page text preview (500 chars): {body_text[:500]}")

        # List all movie links found
        print("\n    Movie links found:")
        for a in page.query_selector_all("a"):
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip().replace("\n", " ")
            if "/movies/" in href and text:
                print(f"      [{text[:60]}] -> {href[:80]}")

        # ----------------------------------------------------------------
        # Step 2: Try direct movie URL patterns
        # ----------------------------------------------------------------
        print("\n[2] Trying direct movie URL patterns...")
        candidate_urls = [
            f"{BMS_BASE}/movies/spider-man-brand-new-day/ET00",
            f"{BMS_BASE}/buytickets/spider-man-brand-new-day/hyderabad",
            f"{BMS_BASE}/movies/spider-man-brand-new-day",
        ]

        for url in candidate_urls:
            print(f"    Trying: {url}")
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                title = page.title()
                current_url = page.url
                text_preview = page.inner_text("body")[:200] if "Cloudflare" not in title else "BLOCKED"
                print(f"    Status: {response.status if response else 'N/A'} | Title: {title}")
                print(f"    URL: {current_url}")
                if "Cloudflare" not in title and "404" not in title:
                    page.screenshot(path=f"nav_test_movie_{candidate_urls.index(url)}.png")
                    print(f"    Body preview: {text_preview[:200]}")
                    break
            except Exception as e:
                print(f"    Error: {e}")

        # ----------------------------------------------------------------
        # Step 3: Report intercepted API responses
        # ----------------------------------------------------------------
        print(f"\n[3] Intercepted {len(intercepted_api_responses)} BMS API responses:")
        for r in intercepted_api_responses:
            spider_flag = " [*** SPIDER-MAN ***]" if r["has_spider"] else ""
            print(f"    [{r['status']}]{spider_flag} {r['url'][:100]}")
            if r["has_spider"]:
                print(f"    Body: {r['body_preview']}")

        with open("intercepted_responses.json", "w", encoding="utf-8") as f:
            json.dump(intercepted_api_responses, f, indent=2, ensure_ascii=False)

        browser.close()
        print("\nDone. Check nav_test_*.png screenshots.")

if __name__ == "__main__":
    run()
