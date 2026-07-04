"""
Scraper — monitors BookMyShow for Spider-Man: Brand New Day.

Confirmed working strategy (as of 2026-07-04):

  URL: https://in.bookmyshow.com/explore/home/hyderabad
  ✓ Loads reliably without Cloudflare blocks
  ✓ Contains SSR movie list including Spider-Man (ET00502600)
  ✓ Section header "Movies Now Showing in Hyderabad" is in the DOM

  Section detection: the explore page has a div with class sc-7wuoxb-3 (iyIzJ)
  containing the section heading text. Spider-Man's anchor is a sibling of
  this heading inside the same parent container.

  Booking logic:
    - If movie is inside a "Now Showing" container → booking_open = True
    - If movie is inside an "Upcoming" container → booking_open = False

  Movie page: accessible via anchor click from explore page.
  APIs on movie page may be blocked if IP is rate-limited.
  That's OK — the explore page section is the primary booking signal.
"""

import re
import time
from typing import Any

from playwright.sync_api import sync_playwright, Page, Response, TimeoutError as PWTimeoutError
from playwright_stealth import Stealth

import config
from logger import get_logger

logger = get_logger()

BMS_HOME = "https://in.bookmyshow.com"
EXPLORE_URL = f"{BMS_HOME}/explore/home/hyderabad"

# These phrases appear as section headings on the explore page
NOW_SHOWING_SECTION_PHRASES = [
    "now showing",
    "movies now showing",
    "now playing",
    "recommended movies",
    "recommended",
    "book tickets",
]

UPCOMING_SECTION_PHRASES = [
    "upcoming",
    "coming soon",
    "releasing",
    "advance booking",
]


def scrape_movie(movie_name: str, city: str) -> dict[str, Any]:
    """
    Main entry point. Returns raw scraped data dict with keys:
        booking_open  (bool)
        movie_found   (bool)
        movie_section (str)   — "now_showing" | "upcoming" | "listed" | "not_listed"
        formats       (list[str])   — from movie card on explore page
        theatres      (list[str])   — from movie page (if accessible)
        shows         (list[dict])  — from movie page (if accessible)
        raw_url       (str)
    """
    result: dict[str, Any] = {
        "booking_open": False,
        "movie_found": False,
        "movie_section": "not_listed",
        "theatres": [],
        "formats": [],
        "shows": [],
        "raw_url": EXPLORE_URL,
    }

    pw_ctx = Stealth().use_sync(sync_playwright()) if config.STEALTH else sync_playwright()

    with pw_ctx as pw:
        logger.info("Launching browser (headless=%s, stealth=%s)", config.HEADLESS, config.STEALTH)
        browser = pw.chromium.launch(
            headless=config.HEADLESS,
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
        page.set_default_timeout(config.PAGE_TIMEOUT_MS)

        # Capture intercepted API responses (bonus data, not primary source)
        api_data: dict[str, Any] = {}

        def on_response(response: Response) -> None:
            if response.status != 200:
                return
            if "bookmyshow.com/api" not in response.url:
                return
            try:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    api_data[response.url] = response.json()
            except Exception:
                pass

        page.on("response", on_response)

        try:
            result = _run_scrape(page, api_data, movie_name, city)
        except PWTimeoutError as exc:
            logger.warning("Page timeout: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error: %s", exc, exc_info=True)
        finally:
            browser.close()
            logger.info("Browser closed.")

    return result


def _run_scrape(
    page: Page,
    api_data: dict[str, Any],
    movie_name: str,
    city: str,
) -> dict[str, Any]:
    """Core scrape flow."""

    # ----------------------------------------------------------------
    # Step 1: Load the explore page (confirmed Cloudflare-safe)
    # ----------------------------------------------------------------
    logger.info("Loading explore page: %s", EXPLORE_URL)
    page.goto(EXPLORE_URL, wait_until="domcontentloaded")
    time.sleep(5)

    page_title = page.title()
    logger.info("Page title: %s", page_title)

    if "cloudflare" in page_title.lower() or "attention required" in page_title.lower():
        logger.warning("Cloudflare block on explore page. Retrying after 10s...")
        time.sleep(10)
        page.reload(wait_until="domcontentloaded")
        time.sleep(5)

    # ----------------------------------------------------------------
    # Step 2: Find movie and determine section using confirmed DOM structure
    # ----------------------------------------------------------------
    movie_href, movie_section, card_formats = _find_movie_and_section(page)

    if not movie_href:
        logger.info("Movie '%s' not found on explore page.", movie_name)
        return {
            "booking_open": False,
            "movie_found": False,
            "movie_section": "not_listed",
            "theatres": [],
            "formats": card_formats,
            "shows": [],
            "raw_url": page.url,
        }

    logger.info(
        "Movie found | href=%s | section=%s | formats_on_card=%s",
        movie_href, movie_section, card_formats,
    )

    # Determine booking status from section
    booking_open = movie_section == "now_showing"

    # ----------------------------------------------------------------
    # Step 3: Try to get more detail from movie page (best effort)
    #         On a fresh VM IP this will fully work.
    #         On a rate-limited IP it may fail — that's OK.
    # ----------------------------------------------------------------
    theatres, more_formats, shows = _try_movie_page(page, movie_href)

    # Merge formats
    all_formats = list(dict.fromkeys(card_formats + more_formats))  # dedup, preserve order

    # If movie page confirmed booking open, trust it
    if theatres or more_formats:
        booking_open = True

    return {
        "booking_open": booking_open,
        "movie_found": True,
        "movie_section": movie_section,
        "theatres": theatres,
        "formats": all_formats,
        "shows": shows,
        "raw_url": page.url,
    }


def _find_movie_and_section(page: Page) -> tuple[str | None, str, list[str]]:
    """
    Find Spider-Man's link on the explore page and determine its section.

    Returns (href, section_name, formats_from_card)
    section_name: "now_showing" | "upcoming" | "listed"

    Approach: use JavaScript to walk the DOM and find the section heading
    that is a sibling of (or ancestor-sibling of) the movie anchor.
    This is robust to BMS class name changes.
    """
    event_code = config.BMS_EVENT_CODE
    slug = config.BMS_MOVIE_SLUG

    result = page.evaluate(f"""
        () => {{
            const eventCode = '{event_code}';
            const slugPart = '{slug.split("-")[0]}';

            // Find the movie anchor
            let movieAnchor = null;
            for (const a of document.querySelectorAll('a[href]')) {{
                const href = a.getAttribute('href') || '';
                if (href.includes(eventCode) || href.toLowerCase().includes(slugPart.toLowerCase())) {{
                    movieAnchor = a;
                    break;
                }}
            }}

            if (!movieAnchor) return {{ found: false, href: '', section: 'not_listed', section_text: '', formats: [] }};

            const href = movieAnchor.getAttribute('href');

            // Strategy: walk UP ancestors and look for a container div whose
            // DIRECT children include a heading element (no <a> tag) with
            // 'showing' or 'upcoming' text.
            const nowKeywords = ['now showing', 'now playing', 'recommended movies', 'recommended'];
            const upcomingKeywords = ['upcoming', 'coming soon', 'releasing', 'advance booking'];

            let section = 'listed';
            let sectionText = '';

            let node = movieAnchor.parentElement;
            for (let depth = 0; depth < 12 && node; depth++) {{
                // Check EVERY text-containing child that has NO anchor descendants
                for (const child of node.children) {{
                    if (child.querySelector('a')) continue; // skip containers with links
                    const txt = (child.innerText || '').toLowerCase().trim();
                    if (txt.length < 5 || txt.length > 200) continue;

                    for (const kw of nowKeywords) {{
                        if (txt.includes(kw)) {{
                            section = 'now_showing';
                            sectionText = txt;
                            break;
                        }}
                    }}
                    if (section !== 'listed') break;

                    for (const kw of upcomingKeywords) {{
                        if (txt.includes(kw)) {{
                            section = 'upcoming';
                            sectionText = txt;
                            break;
                        }}
                    }}
                    if (section !== 'listed') break;
                }}
                if (section !== 'listed') break;
                node = node.parentElement;
            }}

            // If still 'listed', do a broader sweep: check ALL text in ancestors
            if (section === 'listed') {{
                let n = movieAnchor.parentElement;
                for (let depth = 0; depth < 15 && n; depth++) {{
                    const fullText = (n.innerText || '').toLowerCase();
                    for (const kw of nowKeywords) {{
                        if (fullText.includes(kw)) {{
                            section = 'now_showing';
                            sectionText = kw;
                            break;
                        }}
                    }}
                    if (section !== 'listed') break;
                    for (const kw of upcomingKeywords) {{
                        if (fullText.includes(kw)) {{
                            section = 'upcoming';
                            sectionText = kw;
                            break;
                        }}
                    }}
                    if (section !== 'listed') break;
                    n = n.parentElement;
                }}
            }}

            // Extract formats from ancestor text
            let formats = [];
            const fmtKeywords = ['3D','IMAX','Dolby','Barco','EPIQ','4DX','PCX','ScreenX','Screen X','HDR','2D'];
            let cardNode = movieAnchor.parentElement;
            for (let d = 0; d < 6 && cardNode; d++) {{
                const cardText = cardNode.innerText || '';
                for (const fmt of fmtKeywords) {{
                    if (cardText.includes(fmt) && !formats.includes(fmt)) {{
                        formats.push(fmt);
                    }}
                }}
                cardNode = cardNode.parentElement;
            }}

            return {{
                found: true,
                href: href,
                section: section,
                section_text: sectionText,
                formats: formats
            }};
        }}
    """)

    if not result or not result.get("found"):
        return None, "not_listed", []

    section = result.get("section", "listed")
    section_text = result.get("section_text", "")
    formats = result.get("formats", [])
    href = result.get("href", "")

    logger.info("Section heading found: '%s' -> section='%s'", section_text, section)

    return href, section, formats


def _try_movie_page(
    page: Page,
    movie_href: str,
) -> tuple[list[str], list[str], list[dict]]:
    """
    Try to navigate to the movie page and extract theatre/format/show data.
    Handles Cloudflare/bug-page gracefully — returns empty lists on failure.
    This is supplementary; the explore page is the primary data source.
    """
    movie_url = movie_href if movie_href.startswith("http") else f"{BMS_HOME}{movie_href}"
    logger.info("Attempting movie page: %s", movie_url)

    # Find anchor and click it
    anchor = page.query_selector(f"a[href*='{config.BMS_EVENT_CODE}']")
    if not anchor:
        anchor = page.query_selector(f"a[href='{movie_href}']")

    navigated = False
    if anchor:
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=20_000):
                anchor.click()
            navigated = True
        except Exception as exc:
            logger.debug("Click navigation failed: %s", exc)

    if not navigated:
        try:
            page.goto(movie_url, wait_until="domcontentloaded")
        except Exception as exc:
            logger.debug("goto navigation failed: %s", exc)

    time.sleep(4)

    body_text = page.inner_text("body")
    page_title = page.title()

    # Detect failure states
    if (
        "cloudflare" in page_title.lower()
        or "attention required" in page_title.lower()
        or "bug-ging" in body_text.lower()
        or "blocked" in body_text[:200].lower()
    ):
        logger.warning("Movie page inaccessible (rate-limited). Using explore page data only.")
        return [], [], []

    logger.info("Movie page loaded: %s", page.url)

    # Extract formats from the visible format pills (e.g. "2D, EPIQ, DOLBY CINEMA 3D, 3D, +7")
    formats = _extract_formats_from_movie_page(page)

    # Extract theatres and show times
    theatres = _extract_theatres(page)
    shows = _extract_shows(page)

    return theatres, formats, shows


def _extract_formats_from_movie_page(page: Page) -> list[str]:
    """Extract format pills visible on movie detail page."""
    formats: list[str] = []

    # BMS shows formats as clickable pills/tags
    format_selectors = [
        "[class*='format']",
        "[class*='Format']",
        "[class*='screen-type']",
        "[class*='screenType']",
        "[class*='tag']",
        "[class*='pill']",
        "[class*='badge']",
    ]
    for sel in format_selectors:
        for el in page.query_selector_all(sel):
            txt = (el.inner_text() or "").strip()
            format_keywords = ["3D", "2D", "IMAX", "Dolby", "Barco", "EPIQ", "4DX",
                               "PCX", "Screen X", "ScreenX", "HDR", "Atmos", "DTS"]
            if any(kw.lower() in txt.lower() for kw in format_keywords):
                if txt not in formats:
                    formats.append(txt)

    # Also scan page text for format pattern
    body_text = page.inner_text("body")
    format_pattern = re.compile(
        r'\b(2D|3D|IMAX|Dolby(?:\s+\w+)*|HDR By Barco|Barco|EPIQ\s*3D|EPIQ|4DX\s*3D|4DX|'
        r'PCX|Screen\s*X|ScreenX|Dolby Cinema\s*3D|Dolby Atmos|DTS:X)\b',
        re.IGNORECASE,
    )
    for m in format_pattern.finditer(body_text):
        fmt = m.group(0).strip()
        if fmt and fmt not in formats:
            formats.append(fmt)

    return formats


def _extract_theatres(page: Page) -> list[str]:
    """Extract venue names from movie page DOM."""
    theatres: list[str] = []
    selectors = [
        "[class*='venue-name']", "[class*='theatre-name']",
        "[class*='cinema-name']", "[class*='cinemaName']",
        "[class*='venueName']", "[class*='cine-name']",
        "[data-testid*='venue']", "[data-testid*='theatre']",
    ]
    for sel in selectors:
        for el in page.query_selector_all(sel):
            name = (el.inner_text() or "").strip()
            if name and name not in theatres:
                theatres.append(name)
    return theatres


def _extract_shows(page: Page) -> list[dict]:
    """Extract show time slots from movie page DOM."""
    shows: list[dict] = []
    selectors = [
        "[class*='show-time']", "[class*='showTime']",
        "[class*='time-slot']", "[class*='timeSlot']",
        "[data-testid*='show-time']",
    ]
    for sel in selectors:
        for el in page.query_selector_all(sel):
            t = (el.inner_text() or "").strip()
            if t and re.match(r'\d{1,2}:\d{2}', t):
                shows.append({"theatre": "", "time": t, "format": ""})
    return shows
