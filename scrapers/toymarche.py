"""
scrapers/toymarche.py
NEW ARRIVALS scraper for toymarche.com (StoreHippo Angular SPA).

Uses Playwright to scrape brand/category listing pages. The site is a
StoreHippo Angular app — product cards are rendered client-side and are
invisible in raw HTML.

Expected URL format:
  /brand/{brand-slug}       e.g. /brand/matchbox
  /category/{slug}
"""
import logging
from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

WAIT_TIMEOUT_MS = 30_000
BASE_URL = "https://www.toymarche.com"


class ToyMarcheScraper(BaseScraper):
    """
    Playwright scraper for toymarche.com (StoreHippo) listing pages.

    Navigates to a brand/category page, waits for Angular hydration,
    then extracts product cards from the main content grid only.
    Nav links are excluded by scoping the selector to the product grid.
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

        logger.info(f"[ToyMarche] Launching browser for listing: {url}")
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    viewport={"width": 1280, "height": 2000},
                )
                pg = context.new_page()

                # Block heavy assets to speed up load
                pg.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,mp4,mp3}",
                    lambda route: route.abort(),
                )

                pg.goto(url, wait_until="networkidle", timeout=45_000)

                # Scroll to trigger lazy-loaded products
                pg.evaluate("""async () => {
                    const delay = ms => new Promise(r => setTimeout(r, ms));
                    for (let i = 0; i < 15; i++) {
                        window.scrollBy(0, 600);
                        await delay(350);
                    }
                }""")
                pg.wait_for_timeout(2500)

                # StoreHippo renders product cards in the #th2uiview container.
                # We search within that scope to avoid nav/footer links.
                raw_products = pg.evaluate("""() => {
                    const results = [];
                    const seen = new Set();

                    // Primary container used by StoreHippo Angular SPA
                    const container = document.querySelector('#th2uiview') || document.body;

                    // Product detail links follow /product/{slug} or /{slug} patterns
                    // StoreHippo uses hrefs like /brand-slug/product-slug or /p/slug
                    const links = container.querySelectorAll('a[href]');

                    for (const a of links) {
                        const href = a.href;
                        // StoreHippo product URLs: /[category]/[product-slug]/p/[id]
                        // or simpler /[slug] — filter to links that look like products
                        // by excluding known non-product paths
                        if (!href || seen.has(href)) continue;
                        const path = new URL(href).pathname;
                        // Skip known navigation paths
                        if (
                            path === '/' ||
                            path.startsWith('/brand') ||
                            path.startsWith('/category') ||
                            path.startsWith('/cart') ||
                            path.startsWith('/login') ||
                            path.startsWith('/account') ||
                            path.startsWith('/order') ||
                            path.startsWith('/wishlist') ||
                            path.startsWith('/search') ||
                            path.startsWith('/page') ||
                            path.includes('#')
                        ) continue;

                        // Get text from the link or its nearest card
                        let productName = a.innerText.trim();
                        if (productName.length < 3) {
                            const card = a.closest(
                                '[class*="product"], [class*="card"], [class*="item"], li'
                            );
                            if (card) {
                                const nameEl = card.querySelector(
                                    'h2, h3, h4, h5, .name, .title, [class*="name"], [class*="title"]'
                                );
                                productName = nameEl
                                    ? nameEl.innerText.trim()
                                    : card.innerText.trim().split('\\n')[0];
                            }
                        }
                        if (productName.length > 2) {
                            seen.add(href);
                            results.push({name: productName.substring(0, 200), url: href});
                        }
                    }
                    return results;
                }""")

                browser.close()

                products = [
                    ProductEntry(name=p["name"], url=p["url"])
                    for p in raw_products
                ]
                logger.info(f"[ToyMarche] Found {len(products)} products on {url}")
                return ListingResult(page_name=name, page_url=url, products=products)

        except Exception as e:
            logger.exception(f"[ToyMarche] Error scraping {url}: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
