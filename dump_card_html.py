"""
Dump the full HTML context around the Spider-Man card on the explore page.
This tells us exactly what data is available without hitting the movie page.

Usage: python dump_card_html.py
"""

import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

BMS_HOME = "https://in.bookmyshow.com"
EVENT_CODE = "ET00502600"

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

        print("[1] Loading explore page...")
        page.goto(f"{BMS_HOME}/explore/home/hyderabad", wait_until="domcontentloaded")
        time.sleep(5)
        print(f"    Title: {page.title()}")

        # Find the Spider-Man anchor
        anchor = page.query_selector(f"a[href*='{EVENT_CODE}']")
        if not anchor:
            print("    Spider-Man anchor NOT FOUND")
            browser.close()
            return

        print(f"    Found anchor: {anchor.get_attribute('href')}")
        print(f"    Text: {anchor.inner_text()[:80]}")

        # Dump ancestor HTML going up 6 levels
        print("\n[2] Ancestor HTML (6 levels up from Spider-Man anchor):")
        html = page.evaluate("""
            (el) => {
                let node = el;
                let levels = [];
                for (let i = 0; i < 8; i++) {
                    if (!node) break;
                    levels.push({
                        level: i,
                        tag: node.tagName,
                        className: node.className ? node.className.substring(0, 80) : '',
                        outerHTML: node.outerHTML ? node.outerHTML.substring(0, 2000) : ''
                    });
                    node = node.parentElement;
                }
                return levels;
            }
        """, anchor)

        for level in html:
            print(f"\n  --- Level {level['level']}: <{level['tag']} class='{level['className']}'>")
            print(f"  {level['outerHTML'][:600]}")

        # Also get all text visible in the 4th-level ancestor (the card)
        print("\n[3] Card-level inner text:")
        card_text = page.evaluate("""
            (el) => {
                let node = el;
                for (let i = 0; i < 5; i++) {
                    if (node && node.parentElement) node = node.parentElement;
                }
                return node ? node.innerText : '';
            }
        """, anchor)
        print(card_text[:500])

        # Check: does any element near Spider-Man contain booking/format keywords?
        print("\n[4] Checking for format/booking keywords near Spider-Man card:")
        keywords = ["3D", "DOLBY", "IMAX", "Barco", "EPIQ", "Book", "ticket", "4DX", "PCX", "Screen X"]
        for kw in keywords:
            if kw.lower() in card_text.lower():
                print(f"    FOUND: '{kw}'")

        # Also check the full page text for Spider-Man related content
        print("\n[5] All page text containing Spider-Man context:")
        full_text = page.inner_text("body")
        lines = full_text.split("\n")
        spider_idx = None
        for i, line in enumerate(lines):
            if "spider" in line.lower() or EVENT_CODE in line:
                spider_idx = i
                break

        if spider_idx is not None:
            context_lines = lines[max(0, spider_idx-5):spider_idx+20]
            for line in context_lines:
                if line.strip():
                    print(f"    {line}")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
