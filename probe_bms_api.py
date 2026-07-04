"""
API probe — call BMS internal APIs directly to see what they return
and find the right endpoints for movie + venue listing.

Usage: python probe_bms_api.py
"""

import json
import time
from playwright.sync_api import sync_playwright

BMS_BASE = "https://in.bookmyshow.com"

# Endpoints to probe
ENDPOINTS = [
    # Home discovery feed for Hyderabad
    "/api/explore/v1/discover/home/hyderabad?region=HYD&embedded=true",
    # Movies listing for Hyderabad
    "/api/explore/v1/discover/movies/hyderabad?region=HYD",
    # Now showing movies
    "/api/v2/movies?region=HYD",
    # Movie-specific event listing
    "/api/movies-data-service/v1/movie/list?region=HYD",
]

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

        # First: load homepage to get cookies/session
        page = context.new_page()
        page.set_default_timeout(30_000)
        print("[0] Loading homepage to establish session + cookies...")
        page.goto(f"{BMS_BASE}/Hyderabad", wait_until="domcontentloaded")
        time.sleep(3)
        print(f"    Cookies set: {len(context.cookies())}")

        # Now call each API endpoint using page.evaluate (runs in browser context, has cookies)
        results = {}
        for endpoint in ENDPOINTS:
            url = f"{BMS_BASE}{endpoint}"
            print(f"\n[API] GET {url[:100]}")
            try:
                response = page.evaluate(f"""
                    async () => {{
                        const r = await fetch('{url}', {{
                            headers: {{
                                'Accept': 'application/json',
                                'x-region-code': 'HYD',
                                'x-region-slug': 'hyderabad',
                            }}
                        }});
                        const text = await r.text();
                        return {{ status: r.status, body: text.substring(0, 5000) }};
                    }}
                """)
                print(f"    Status: {response['status']}")
                body = response['body']
                print(f"    Body preview (500 chars):\n    {body[:500]}")

                # Check if Spider-Man is mentioned
                if "spider" in body.lower() or "brand new day" in body.lower():
                    print("    *** SPIDER-MAN FOUND IN THIS RESPONSE ***")
                    results[endpoint] = body
            except Exception as e:
                print(f"    Error: {e}")

        # Also try the autocomplete/search API
        print("\n[API] Testing autocomplete endpoint...")
        try:
            autocomplete_url = f"{BMS_BASE}/api/search/v1/suggest?query=Spider-Man&region=HYD"
            response = page.evaluate(f"""
                async () => {{
                    const r = await fetch('{autocomplete_url}', {{
                        headers: {{ 'Accept': 'application/json' }}
                    }});
                    const text = await r.text();
                    return {{ status: r.status, body: text.substring(0, 3000) }};
                }}
            """)
            print(f"    Status: {response['status']}")
            print(f"    Body: {response['body'][:1000]}")
        except Exception as e:
            print(f"    Autocomplete error: {e}")

        # Try another search variant
        print("\n[API] Testing search suggest v2...")
        try:
            url2 = f"{BMS_BASE}/api/search/v2/suggest?q=Spider-Man&region=HYD&category=movies"
            response2 = page.evaluate(f"""
                async () => {{
                    const r = await fetch('{url2}', {{
                        headers: {{ 'Accept': 'application/json' }}
                    }});
                    const text = await r.text();
                    return {{ status: r.status, body: text.substring(0, 3000) }};
                }}
            """)
            print(f"    Status: {response2['status']}")
            print(f"    Body: {response2['body'][:1000]}")
        except Exception as e:
            print(f"    Error: {e}")

        # Save full results
        if results:
            with open("bms_api_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("\nSpider-Man API results saved to bms_api_results.json")

        browser.close()
        print("\nDone.")

if __name__ == "__main__":
    run()
