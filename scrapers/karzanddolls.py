"""
scrapers/karzanddolls.py
NEW ARRIVALS scraper for karzanddolls.com (Angular SPA).

Uses Playwright to scrape listing/category pages. The site is a custom Angular
app — product cards are rendered client-side and invisible in raw HTML.

Expected URL format (category listing):
  /details/{category}/{subcategory}/{categoryId}
  e.g. /details/mini+gt+/mini-gt/MTY1
"""
import logging
from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

WAIT_TIMEOUT_MS = 25_000


class KarzAndDollsScraper(BaseScraper):
    """
    Playwright scraper for karzanddolls.com listing pages.

    Navigates to a category listing, waits for Angular hydration,
    then extracts all product cards (name + URL + price).
    """

    def scrape_listing(self, page: dict) -> ListingResult:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            return ListingResult(
                page_name=page["name"], page_url=page["url"],
                error="Playwright not installed. Run: pip install playwright && playwright install chromium",
            )

        name = page["name"]
        url = page["url"]

        logger.info(f"[KarzAndDolls] Launching browser for listing: {url}")
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    viewport={"width": 1280, "height": 2000},
                )
                pg = context.new_page()

                # Block heavy assets
                pg.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,mp4,mp3}",
                    lambda route: route.abort(),
                )

                pg.goto(url, wait_until="networkidle", timeout=40_000)

                # Scroll to bottom to trigger lazy-loaded products
                pg.evaluate("""async () => {
                    const delay = ms => new Promise(r => setTimeout(r, ms));
                    for (let i = 0; i < 15; i++) {
                        window.scrollBy(0, 600);
                        await delay(400);
                    }
                }""")
                pg.wait_for_timeout(2000)

                # Extract product cards — Angular renders them as divs/cards with
                # a product name, image, and link. We look for anchor tags that
                # point to /product/ detail pages.
                raw_products = pg.evaluate("""() => {
                    const results = [];
                    // Strategy 1: Find all links containing '/product/' in href
                    const links = document.querySelectorAll('a[href*="/product/"]');
                    const seen = new Set();
                    for (const a of links) {
                        const href = a.href;
                        if (seen.has(href)) continue;
                        seen.add(href);

                        // Get the text — product name is typically in the card
                        let name = a.innerText.trim();
                        // If the link text is too short, try parent card
                        if (name.length < 3) {
                            const card = a.closest('.product-card, .card, .item, [class*="product"]');
                            if (card) name = card.innerText.trim().split('\\n')[0];
                        }
                        if (name.length > 2) {
                            results.push({name: name.substring(0, 200), url: href});
                        }
                    }

                    // Strategy 2: If no /product/ links, try generic product cards
                    if (results.length === 0) {
                        const cards = document.querySelectorAll('[class*="product"], [class*="card"], [class*="item"]');
                        for (const card of cards) {
                            const a = card.querySelector('a');
                            const nameEl = card.querySelector('h2, h3, h4, .name, .title, [class*="name"], [class*="title"]');
                            if (a && nameEl) {
                                const n = nameEl.innerText.trim();
                                if (n.length > 2 && !seen.has(a.href)) {
                                    seen.add(a.href);
                                    results.push({name: n.substring(0, 200), url: a.href});
                                }
                            }
                        }
                    }
                    return results;
                }""")

                browser.close()

                products = [
                    ProductEntry(name=p["name"], url=p["url"])
                    for p in raw_products
                ]
                logger.info(f"[KarzAndDolls] Found {len(products)} products on {url}")
                return ListingResult(page_name=name, page_url=url, products=products)

        except Exception as e:
            logger.exception(f"[KarzAndDolls] Error scraping {url}: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
