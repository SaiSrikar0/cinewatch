"""
Targeted explore page test:
1. Navigate to /explore/home/hyderabad (confirmed working)
2. Dump all movie anchor links
3. Click a real movie link and see if its page loads
   (click = real browser navigation, not direct goto)

Usage: python test_explore_page.py
"""

import time
from playwright.sync_api import sync_playwright, Response
from playwright_stealth import Stealth

BMS_HOME = "https://in.bookmyshow.com"

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
        page = context.new_page()
        page.set_default_timeout(30_000)

        def on_response(response: Response):
            url = response.url
            if "bookmyshow.com/api" in url:
                status = response.status
                if status not in (200,):
                    print(f"[API {status}] {url[:100]}")

        page.on("response", on_response)

        # ---- Step 1: Navigate to explore page ----
        explore_url = f"{BMS_HOME}/explore/home/hyderabad"
        print(f"[1] Navigating to {explore_url}")
        page.goto(explore_url, wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path="explore_test_1.png")
        print(f"    Title: {page.title()}")

        # ---- Step 2: Dump ALL movie anchor links ----
        print("\n[2] All movie/event anchor links:")
        movie_links = []
        for a in page.query_selector_all("a"):
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip().replace("\n", " ")
            if href and text and any(
                kw in href for kw in ["/movies/", "/events/", "/buytickets/", "/explore/"]
            ) and href not in ("/explore/home/hyderabad",):
                movie_links.append({"text": text[:60], "href": href})
                print(f"    [{text[:60]}] -> {href[:100]}")

        # ---- Step 3: Find a clickable movie and click it ----
        # Pick the first real movie link (not a utility link)
        target_link = None
        for link in movie_links:
            href = link["href"]
            text = link["text"]
            if "/movies/" in href and text and len(text) > 3:
                target_link = link
                break

        if target_link:
            print(f"\n[3] Clicking movie link: [{target_link['text']}] -> {target_link['href']}")
            # Find the anchor and click it (real browser navigation)
            anchor = page.query_selector(f"a[href='{target_link['href']}']")
            if anchor:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
                    anchor.click()
                time.sleep(4)
                page.screenshot(path="explore_test_2_movie_page.png")
                body = page.inner_text("body")
                print(f"    URL after click: {page.url}")
                print(f"    Title: {page.title()}")
                if "bug-ging" in body.lower() or "blocked" in body.lower():
                    print("    BLOCKED/BUG PAGE after click")
                elif "book" in body.lower() or "ticket" in body.lower():
                    print("    MOVIE PAGE LOADED!")
                    print(f"    Preview: {body[:400]}")
                else:
                    print(f"    Other page: {body[:300]}")
            else:
                print("    Could not find anchor element for click")
        else:
            print("\n[3] No movie links found to click")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
