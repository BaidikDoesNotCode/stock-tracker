"""
scrapers/keraladiecastcars.py
NEW ARRIVALS scraper for keraladiecastcars.com (Wix).

Uses Playwright because the Wix site renders product content entirely via JS.
Static HTML only contains the navigation shell.
"""
import logging
from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

WAIT_TIMEOUT_MS = 25_000


class KeralaDialcastCarsScraper(BaseScraper):
    """
    Playwright scraper for keraladiecastcars.com listing/home page.

    Navigates to the page, waits for Wix hydration, scrolls to load
    all products, then extracts product names and links.
    """

    def scrape_listing(self, page: dict) -> ListingResult:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            return ListingResult(
                page_name=page["name"], page_url=page["url"],
                error="Playwright not installed.",
            )

        name = page["name"]
        url = page["url"]

        logger.info(f"[KeralaDiecast] Launching browser for: {url}")
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    viewport={"width": 1280, "height": 2000},
                )
                pg = context.new_page()

                pg.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,mp4}",
                    lambda route: route.abort(),
                )

                pg.goto(url, wait_until="networkidle", timeout=40_000)

                # Scroll to load lazy content
                pg.evaluate("""async () => {
                    const delay = ms => new Promise(r => setTimeout(r, ms));
                    for (let i = 0; i < 12; i++) {
                        window.scrollBy(0, 500);
                        await delay(400);
                    }
                }""")
                pg.wait_for_timeout(2000)

                # Extract products — Wix structures vary, so we use multiple selectors
                raw_products = pg.evaluate("""() => {
                    const results = [];
                    const seen = new Set();
                    const baseUrl = window.location.origin;

                    // Find all internal links that could be products
                    const links = document.querySelectorAll('a[href]');
                    for (const a of links) {
                        const href = a.href;
                        // Skip nav links, policy links, and external
                        if (!href.startsWith(baseUrl)) continue;
                        const path = new URL(href).pathname;
                        if (['/', '/brands', '/pre-order', '/tracking', '/contact',
                             '/privacy-policy', '/refund-policy', '/terms-and-conditions'].includes(path)) continue;
                        if (path.length < 3) continue;
                        if (seen.has(href)) continue;
                        seen.add(href);

                        // Product links on Wix usually have descriptive text
                        let text = a.innerText.trim();
                        if (text === 'Buy Now' || text === 'See More...') {
                            // Try to get text from parent section
                            const parent = a.closest('section, div[class]');
                            if (parent) {
                                const heading = parent.querySelector('h1, h2, h3, h4, h5, h6');
                                if (heading) text = heading.innerText.trim();
                            }
                        }
                        if (text.length > 2 && text.length < 200) {
                            results.push({name: text, url: href});
                        }
                    }
                    return results;
                }""")

                browser.close()

                products = [
                    ProductEntry(name=p["name"], url=p["url"])
                    for p in raw_products
                ]
                logger.info(f"[KeralaDiecast] Found {len(products)} products on {url}")
                return ListingResult(page_name=name, page_url=url, products=products)

        except Exception as e:
            logger.exception(f"[KeralaDiecast] Error scraping {url}: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
