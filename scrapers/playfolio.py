"""
scrapers/playfolio.py
NEW ARRIVALS scraper for playfolio.in (Shopify).

Uses /collections/{handle}/products.json to get all products in a collection.
The watchlist URL may contain price filter and sort params; these are ignored
in favour of the JSON API which fetches the full collection.
"""
import logging
import requests
from urllib.parse import urlparse

from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

BASE_URL = "https://playfolio.in"
REQUEST_TIMEOUT = 15
PAGE_LIMIT = 250


class PlayfolioScraper(BaseScraper):
    """
    Fetches all products from a playfolio.in Shopify collection via JSON API.
    Supports automatic pagination.
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self.DEFAULT_HEADERS)
        self._session.headers["Accept"] = "application/json"

    @staticmethod
    def _extract_collection_handle(url: str) -> str:
        """Extract collection handle from URL like /collections/hot-wheels."""
        parts = urlparse(url).path.strip("/").split("/")
        try:
            idx = parts.index("collections")
            return parts[idx + 1]
        except (ValueError, IndexError):
            return ""

    def scrape_listing(self, page: dict) -> ListingResult:
        name = page["name"]
        url = page["url"]

        handle = self._extract_collection_handle(url)
        if not handle:
            return ListingResult(page_name=name, page_url=url,
                                 error=f"Could not extract collection handle from URL: {url}")

        all_products = []
        page_num = 1

        while True:
            api_url = (
                f"{BASE_URL}/collections/{handle}/products.json"
                f"?limit={PAGE_LIMIT}&page={page_num}"
            )
            try:
                logger.info(f"[Playfolio] Fetching: {api_url}")
                resp = self._session.get(api_url, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                batch = data.get("products", [])
                if not batch:
                    break  # No more pages

                for p in batch:
                    title = p.get("title", "Untitled")
                    p_handle = p.get("handle", "")
                    price = ""
                    variants = p.get("variants", [])
                    if variants:
                        price = f"₹{variants[0].get('price', '?')}"

                    product_url = f"{BASE_URL}/products/{p_handle}" if p_handle else url
                    all_products.append(ProductEntry(name=title, url=product_url, price=price))

                if len(batch) < PAGE_LIMIT:
                    break  # Last page
                page_num += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"[Playfolio] Request error on page {page_num}: {e}")
                return ListingResult(page_name=name, page_url=url,
                                     products=all_products, error=str(e))
            except Exception as e:
                logger.exception(f"[Playfolio] Unexpected error: {e}")
                return ListingResult(page_name=name, page_url=url,
                                     products=all_products, error=str(e))

        logger.info(f"[Playfolio] Found {len(all_products)} products in '{handle}'")
        return ListingResult(page_name=name, page_url=url, products=all_products)
