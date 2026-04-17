"""
scrapers/notatoy.py
Stub scraper for notatoy.com — DNS unreachable as of April 2026.
"""
import logging
from .base import BaseScraper, ListingResult

logger = logging.getLogger(__name__)


class NotAToyStubScraper(BaseScraper):

    def scrape_listing(self, page: dict) -> ListingResult:
        logger.warning(f"[NotAToy] Skipping — notatoy.com is DNS-unreachable.")
        return ListingResult(
            page_name=page["name"], page_url=page["url"],
            error="notatoy.com: DNS resolution failure — site offline.",
        )
