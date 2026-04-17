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
from collections import defaultdict

from .base import BaseScraper, ListingResult, ProductEntry

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
BASE_URL = "https://www.kolkatakomics.com"

# Text badges Wix appends to link text — stripped before name extraction
BADGE_PREFIXES = [
    "Quick View", "NEW ARRIVAL", "BESTSELLER",
    "LAST 2 PIECES", "LAST PIECE", "OUT OF STOCK",
    "SOLD OUT", "LAST 3 PIECES",
]


class KolkataKomicsScraper(BaseScraper):
    """
    Static-HTML scraper for kolkatakomics.com shop/category listing pages.

    Product cards on this site have MULTIPLE <a> tags sharing the same href:
      - First <a>: badge text only ("Quick ViewNEW ARRIVAL")
      - Second <a>: product name + price ("Combo of X+YPrice₹334.00")
    We collect ALL text from all <a> tags with the same /product-page/ URL
    and pick the best candidate for the product name.
    """

    def scrape_listing(self, page: dict) -> ListingResult:
        name = page["name"]
        url = page["url"]

        try:
            logger.info(f"[KolkataKomics] Fetching listing: {url}")
            resp = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Collect ALL text fragments from all <a> tags sharing the same product URL
            url_texts: dict[str, list[str]] = defaultdict(list)
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/product-page/" not in href:
                    continue
                full_url = urljoin(BASE_URL, href)
                text = a_tag.get_text(strip=True)
                if text:
                    url_texts[full_url].append(text)

            logger.info(f"[KolkataKomics] Found {len(url_texts)} unique product URLs")

            products = []
            for product_url, texts in url_texts.items():
                # Pick the longest text fragment — it's the one with the actual product name
                # (badge-only fragments like "Quick ViewNEW ARRIVAL" are shorter)
                best_text = max(texts, key=len)

                # Strip badge prefixes
                product_name = best_text
                for prefix in BADGE_PREFIXES:
                    product_name = product_name.replace(prefix, "").strip()

                # Extract price if embedded — format: "Product NamePrice₹xxx.00"
                price = ""
                if "Price" in product_name and "\u20b9" in product_name:
                    parts = product_name.split("Price", 1)
                    product_name = parts[0].strip()
                    price = parts[1].strip()
                elif "\u20b9" in product_name:
                    idx = product_name.rfind("\u20b9")
                    price = product_name[idx:].strip()
                    product_name = product_name[:idx].strip()

                if product_name and len(product_name) > 3:
                    products.append(ProductEntry(
                        name=product_name,
                        url=product_url,
                        price=price,
                    ))

            logger.info(f"[KolkataKomics] Extracted {len(products)} products from {url}")
            return ListingResult(page_name=name, page_url=url, products=products)

        except requests.exceptions.RequestException as e:
            logger.error(f"[KolkataKomics] Request error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
        except Exception as e:
            logger.exception(f"[KolkataKomics] Unexpected error: {e}")
            return ListingResult(page_name=name, page_url=url, error=str(e))
