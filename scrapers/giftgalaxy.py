"""
scrapers/giftgalaxy.py
NEW ARRIVALS scraper for giftgalaxy.in (Shopify).

Uses /products.json?sort_by=created-descending to get the latest products.
No Playwright needed — pure HTTP request to a free Shopify JSON endpoint.
"""
import logging
import requests

from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

BASE_URL = "https://www.giftgalaxy.in"
REQUEST_TIMEOUT = 15
# Max products to fetch per page (Shopify max is 250)
PAGE_LIMIT = 250


class GiftGalaxyScraper(BaseScraper):
    """
    Fetches the latest products from giftgalaxy.in via Shopify JSON API.
    Sorted by newest first so new additions appear at the top.
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self.DEFAULT_HEADERS)
        self._session.headers["Accept"] = "application/json"

    def scrape_listing(self, page: dict) -> ListingResult:
        name = page["name"]
        url = page["url"]

        api_url = f"{BASE_URL}/products.json?sort_by=created-descending&limit={PAGE_LIMIT}"

        try:
            logger.info(f"[GiftGalaxy] Fetching products JSON: {api_url}")
            resp = self._session.get(api_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            products = []
            for p in data.get("products", []):
                title = p.get("title", "Untitled")
                handle = p.get("handle", "")
                price = ""
                variants = p.get("variants", [])
                if variants:
                    price = f"₹{variants[0].get('price', '?')}"

                product_url = f"{BASE_URL}/products/{handle}" if handle else url
                products.append(ProductEntry(name=title, url=product_url, price=price))

            logger.info(f"[GiftGalaxy] Found {len(products)} products")
            return ListingResult(page_name=name, page_url=url, products=products)

        except requests.exceptions.RequestException as e:
            logger.error(f"[GiftGalaxy] Request error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
        except Exception as e:
            logger.exception(f"[GiftGalaxy] Unexpected error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
