"""
checker.py
Compares current listing scrape results against a persisted snapshot
to identify NEW products that weren't seen in previous runs.

Snapshot format (snapshot.json):
{
    "<page_url>": {
        "known_urls": ["url1", "url2", ...],
        "last_checked": "2026-04-18T01:30:00"
    }
}
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from scrapers.base import ListingResult, ProductEntry

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).parent / "snapshot.json"


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict:
    """Load the snapshot from disk. Returns empty dict if file doesn't exist."""
    if not path.exists():
        logger.info("No snapshot.json found — this is the first run.")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load snapshot: {e} — starting fresh.")
        return {}


def save_snapshot(data: dict, path: Path = SNAPSHOT_PATH) -> None:
    """Save the snapshot to disk."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Snapshot saved to {path}")


def find_new_products(
    results: List[ListingResult],
    snapshot: dict,
) -> Tuple[Dict[str, List[ProductEntry]], dict]:
    """
    Compare scraped listings against the snapshot.

    Returns:
        new_by_page: dict mapping page_name → list of NEW ProductEntry objects
        updated_snapshot: the updated snapshot dict to save

    First-run behavior:
        If a page has no entry in the snapshot, ALL products are treated as
        "already known" (saved silently). This avoids a spam flood on the
        first deployment. New items will be detected starting from the 2nd run.
    """
    new_by_page: Dict[str, List[ProductEntry]] = {}
    updated_snapshot = dict(snapshot)  # shallow copy

    for result in results:
        if result.error:
            logger.warning(f"[ERROR]      {result.page_name} | {result.error}")
            continue

        page_key = result.page_url
        current_urls = {p.url for p in result.products}

        if page_key not in snapshot:
            # First run for this page — save all as known, alert nothing
            logger.info(
                f"[FIRST RUN]  {result.page_name} | "
                f"Saving {len(result.products)} products as baseline (no alert)"
            )
            updated_snapshot[page_key] = {
                "known_urls": list(current_urls),
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
            continue

        known_urls = set(snapshot[page_key].get("known_urls", []))
        new_urls = current_urls - known_urls

        if new_urls:
            new_items = [p for p in result.products if p.url in new_urls]
            new_by_page[result.page_name] = new_items
            for item in new_items:
                logger.info(f"[NEW]        {result.page_name} | {item.name} | {item.url}")
        else:
            logger.info(f"[OK]         {result.page_name} | {len(result.products)} products unchanged")

        # Update snapshot: merge new URLs into known set
        updated_snapshot[page_key] = {
            "known_urls": list(known_urls | current_urls),
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

    return new_by_page, updated_snapshot


def summarize(results: List[ListingResult], new_by_page: Dict[str, List[ProductEntry]]) -> str:
    """Plain-text summary for console output."""
    lines = ["=" * 60, "NEW ARRIVALS CHECK SUMMARY", "=" * 60]
    for r in results:
        if r.error:
            lines.append(f"  [ERROR] {r.page_name:<35} {r.error}")
        else:
            new_count = len(new_by_page.get(r.page_name, []))
            if new_count:
                lines.append(f"  [NEW]   {r.page_name:<35} {new_count} NEW product(s)!")
            else:
                lines.append(f"  [OK]    {r.page_name:<35} {len(r.products)} products (no new)")
    lines.append("=" * 60)

    if new_by_page:
        lines.append("")
        lines.append("NEW PRODUCTS DETECTED:")
        lines.append("-" * 60)
        for page_name, items in new_by_page.items():
            lines.append(f"\n  {page_name}:")
            for item in items:
                price_str = f" ({item.price})" if item.price else ""
                lines.append(f"    - {item.name}{price_str}")
                lines.append(f"      {item.url}")
        lines.append("")

    return "\n".join(lines)
