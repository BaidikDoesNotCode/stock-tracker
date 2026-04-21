"""
scrapers/tooneywheels.py
NEW ARRIVALS scraper for tooneywheels.in (WordPress / WooCommerce).

The site is server-rendered, so product listings are fully present in the
raw HTML — no JavaScript execution required. Uses requests + BeautifulSoup
with pagination support.

Expected URL format (category page):
  /product-category/{path}/?orderby=date
  e.g. /product-category/diecast-vehicles/scale-model-cars/164-scale/?orderby=date
"""
import logging
import requests
from urllib.parse import urlparse, urljoin, urlencode, parse_qs, urlunparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
BASE_URL = "https://tooneywheels.in"


class TooneyWheelsScraper(BaseScraper):
    """
    Requests + BeautifulSoup scraper for tooneywheels.in WooCommerce pages.

    Iterates through paginated category pages and collects all
    product detail links from the product grid (ul.products li a.woocommerce-loop-product__link).
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self.DEFAULT_HEADERS)

    @staticmethod
    def _page_url(base_url: str, page_num: int) -> str:
        """Build the paginated URL: appends /page/N/ before the query string."""
        parsed = urlparse(base_url)
        # Strip trailing slash from path, add /page/N/
        path = parsed.path.rstrip("/")
        if page_num > 1:
            path = f"{path}/page/{page_num}/"
        else:
            path = f"{path}/"
        return urlunparse(parsed._replace(path=path))

    def scrape_listing(self, page: dict) -> ListingResult:
        if BeautifulSoup is None:
            return ListingResult(
                page_name=page["name"], page_url=page["url"],
                error="beautifulsoup4 not installed. Run: pip install beautifulsoup4 lxml",
            )

        name = page["name"]
        url = page["url"]

        all_products: list[ProductEntry] = []
        seen_urls: set[str] = set()
        page_num = 1

        while True:
            fetch_url = self._page_url(url, page_num)
            logger.info(f"[TooneyWheels] Fetching page {page_num}: {fetch_url}")

            try:
                resp = self._session.get(fetch_url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 404:
                    # No more pages
                    break
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"[TooneyWheels] Request error on page {page_num}: {e}")
                return ListingResult(page_name=name, page_url=url,
                                     products=all_products, error=str(e))

            soup = BeautifulSoup(resp.text, "lxml")

            # WooCommerce product grid: ul.products > li.product
            product_items = soup.select("ul.products li.product")
            if not product_items:
                # Try alternate selector for some WooCommerce themes
                product_items = soup.select(".products .product")

            if not product_items:
                logger.info(f"[TooneyWheels] No products found on page {page_num} — stopping.")
                break

            found_on_page = 0
            for item in product_items:
                # Primary product link (WooCommerce standard)
                link_el = item.select_one("a.woocommerce-loop-product__link")
                if not link_el:
                    # Fallback: first anchor pointing to a /product/ URL
                    link_el = item.select_one('a[href*="/product/"]')
                if not link_el:
                    continue

                product_url = link_el.get("href", "").strip()
                if not product_url or product_url in seen_urls:
                    continue

                # Product name: prefer the dedicated title element
                title_el = (
                    item.select_one(".woocommerce-loop-product__title")
                    or item.select_one("h2")
                    or item.select_one("h3")
                )
                product_name = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)
                if not product_name:
                    continue

                # Price (optional)
                price_el = item.select_one(".price .woocommerce-Price-amount")
                price = price_el.get_text(strip=True) if price_el else ""

                seen_urls.add(product_url)
                all_products.append(ProductEntry(
                    name=product_name[:200],
                    url=product_url,
                    price=price,
                ))
                found_on_page += 1

            logger.info(
                f"[TooneyWheels] Page {page_num}: {found_on_page} products "
                f"(total so far: {len(all_products)})"
            )

            # Check for a "next page" link
            next_link = soup.select_one("a.next.page-numbers")
            if not next_link:
                break
            page_num += 1

        logger.info(f"[TooneyWheels] Done — {len(all_products)} total products from {url}")
        return ListingResult(page_name=name, page_url=url, products=all_products)
