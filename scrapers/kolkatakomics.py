"""
scrapers/kolkatakomics.py
NEW ARRIVALS scraper for kolkatakomics.com (Wix SSR).

Uses requests + BS4 because Wix server-side renders the product listing
pages with all product names, prices, and links visible in the raw HTML.
"""
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
BASE_URL = "https://www.kolkatakomics.com"


class KolkataKomicsScraper(BaseScraper):
    """
    Static-HTML scraper for kolkatakomics.com shop/category listing pages.

    Parses product entries that Wix renders server-side in the HTML.
    Product cards on this site contain:
      - Product name (in heading elements)
      - Price (₹xxx.00)
      - "Add to Cart" or "Out of Stock"
      - Link to /product-page/{slug}
    """

    def scrape_listing(self, page: dict) -> ListingResult:
        name = page["name"]
        url = page["url"]

        try:
            logger.info(f"[KolkataKomics] Fetching listing: {url}")
            resp = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            products = []
            seen_urls = set()

            # Strategy: Find all links to /product-page/ detail pages
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/product-page/" not in href:
                    continue

                full_url = urljoin(BASE_URL, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract product name from the link text or nearby heading
                product_name = a_tag.get_text(strip=True)

                # Clean up — Wix often prepends "Quick View" badges to link text
                for prefix in ["Quick View", "NEW ARRIVAL", "BESTSELLER",
                               "LAST 2 PIECES", "LAST PIECE", "OUT OF STOCK"]:
                    product_name = product_name.replace(prefix, "").strip()

                # Extract price if embedded in the text
                price = ""
                if "₹" in product_name:
                    # Split name and price — format: "Product NamePrice₹xxx.00"
                    parts = product_name.split("Price")
                    if len(parts) == 2:
                        product_name = parts[0].strip()
                        price = parts[1].strip()
                    elif "₹" in product_name:
                        # Price at the end
                        idx = product_name.rfind("₹")
                        price = product_name[idx:].strip()
                        product_name = product_name[:idx].strip()

                if product_name and len(product_name) > 3:
                    products.append(ProductEntry(
                        name=product_name,
                        url=full_url,
                        price=price,
                    ))

            logger.info(f"[KolkataKomics] Found {len(products)} products on {url}")
            return ListingResult(page_name=name, page_url=url, products=products)

        except requests.exceptions.RequestException as e:
            logger.error(f"[KolkataKomics] Request error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
        except Exception as e:
            logger.exception(f"[KolkataKomics] Unexpected error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
