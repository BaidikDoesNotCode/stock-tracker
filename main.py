"""
main.py
Entry point for the Stock Tracker — NEW ARRIVALS detection mode.

Workflow:
  1. Load watchlist.yaml (listing page URLs to monitor)
  2. Load snapshot.json (previously seen products)
  3. For each listing page, run its scraper → get all products
  4. Compare against snapshot → identify NEW products
  5. If any new products → send email alert
  6. Save updated snapshot.json
  7. Exit 0

Usage:
  python main.py                      # Full run + email
  python main.py --dry-run            # Scrape + compare but skip email
  python main.py --page "Mini GT"     # Only check pages matching this name
  python main.py --reset              # Delete snapshot and start fresh
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List

import yaml

import checker
import notifier
from scrapers import SCRAPER_REGISTRY
from scrapers.base import ListingResult

# ── Fix Windows console encoding (cp1252 can't print ₹, emojis, etc.) ───
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

WATCHLIST_FILE = Path(__file__).parent / "watchlist.yaml"


def load_watchlist() -> List[dict]:
    """Parse watchlist.yaml and return a list of page dicts."""
    if not WATCHLIST_FILE.exists():
        logger.error(f"watchlist.yaml not found at {WATCHLIST_FILE}")
        sys.exit(1)

    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pages = data.get("pages", [])
    if not pages:
        logger.warning("watchlist.yaml contains no pages. Nothing to check.")
    return pages


def run_scrapers(pages: List[dict]) -> List[ListingResult]:
    """Instantiate the right scraper for each page and scrape."""
    results: List[ListingResult] = []
    scraper_cache: dict = {}

    for page in pages:
        scraper_key = page.get("scraper", "").strip()
        scraper_class = SCRAPER_REGISTRY.get(scraper_key)

        if scraper_class is None:
            logger.error(
                f"Unknown scraper '{scraper_key}' for page '{page.get('name')}'. "
                f"Valid: {list(SCRAPER_REGISTRY.keys())}"
            )
            results.append(ListingResult(
                page_name=page.get("name", "Unknown"),
                page_url=page.get("url", ""),
                error=f"Unknown scraper: {scraper_key}",
            ))
            continue

        if scraper_key not in scraper_cache:
            scraper_cache[scraper_key] = scraper_class()

        scraper = scraper_cache[scraper_key]
        result = scraper.scrape_listing(page)
        results.append(result)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stock Tracker — detect new products on e-commerce listing pages."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and compare but skip sending the email notification.",
    )
    parser.add_argument(
        "--page",
        metavar="NAME",
        help="Only check pages whose name contains this substring (case-insensitive).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete snapshot.json and start fresh (first run will save baseline).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Stock Tracker — New Arrivals Detector")
    logger.info("=" * 60)

    if args.reset:
        if checker.SNAPSHOT_PATH.exists():
            checker.SNAPSHOT_PATH.unlink()
            logger.info("Snapshot deleted. Next run will save a fresh baseline.")
        else:
            logger.info("No snapshot to delete.")
        if not args.page:
            sys.exit(0)

    pages = load_watchlist()

    # Optional filter
    if args.page:
        pages = [p for p in pages if args.page.lower() in p.get("name", "").lower()]
        if not pages:
            logger.warning(f"No pages matched filter: '{args.page}'")
            sys.exit(0)
        logger.info(f"Filtered to {len(pages)} page(s) matching '{args.page}'")

    logger.info(f"Checking {len(pages)} listing page(s)…\n")

    # 1. Load snapshot
    snapshot = checker.load_snapshot()

    # 2. Scrape all listing pages
    results = run_scrapers(pages)

    # 3. Find new products
    new_by_page, updated_snapshot = checker.find_new_products(results, snapshot)

    # 4. Print summary
    print("\n" + checker.summarize(results, new_by_page) + "\n")

    # 5. Save updated snapshot (ALWAYS — even if no new items)
    checker.save_snapshot(updated_snapshot)

    # 6. Send email if there are new items
    total_new = sum(len(items) for items in new_by_page.values())
    if total_new == 0:
        logger.info("No new products detected. No email sent.")
    elif args.dry_run:
        logger.info(f"--dry-run: {total_new} new item(s) found but email skipped.")
    else:
        notifier.send_alert(new_by_page)

    logger.info("Done.")


if __name__ == "__main__":
    main()
