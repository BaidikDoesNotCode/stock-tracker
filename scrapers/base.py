"""
scrapers/base.py
Core data structures and abstract base class for NEW ARRIVALS detection.

Architecture:
  Every scraper watches a LISTING PAGE (category, collection, or homepage).
  Instead of checking a single product's stock status, it extracts ALL
  visible product entries (name + URL) from the listing and returns them
  as a ListingResult.

  The checker module then compares this list against a persisted snapshot
  to identify NEW products that weren't there before.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProductEntry:
    """One product found on a listing page."""
    name: str   # Product title as displayed on the listing
    url: str    # Full URL to the product detail page
    price: str = ""  # Price string (optional, for display in email)


@dataclass
class ListingResult:
    """Result of scraping one listing/category page."""
    page_name: str              # Human-readable name (from watchlist.yaml)
    page_url: str               # URL that was scraped
    products: List[ProductEntry] = field(default_factory=list)
    error: Optional[str] = None  # Error message if scrape failed


class BaseScraper(ABC):
    """
    Abstract base for all listing-page scrapers.

    Subclasses must implement:
        scrape_listing(page: dict) -> ListingResult

    'page' is one entry from watchlist.yaml, already parsed into a dict:
        {"name": "...", "url": "...", "scraper": "..."}
    """

    # Reasonable browser-like headers
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    @abstractmethod
    def scrape_listing(self, page: dict) -> ListingResult:
        """
        Scrape a listing page and return ALL product entries found on it.

        Args:
            page: dict with keys: name, url, scraper (+ any extra fields)

        Returns:
            ListingResult with the list of ProductEntry items
        """
        ...
