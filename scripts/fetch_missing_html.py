#!/usr/bin/env python3
"""
Fetches cached Limitless TCG Pocket HTML for set/card pages that are not yet cached.

Reads the set list from the cached limitless_index.html and the expected card count
per set from that same index. Skips sets and cards already present in the HTML cache.

Outputs HTML files to:
    data/reference/external/html_cache/grid_<SET>.html       — set grid pages
    data/reference/external/html_cache/card_<SET>_<NUM>.html — individual card pages

Usage:
    python3 scripts/fetch_missing_html.py               # fetch all missing files
    python3 scripts/fetch_missing_html.py --dry-run     # list what would be fetched
    python3 scripts/fetch_missing_html.py --set A1      # only one set
    python3 scripts/fetch_missing_html.py --max 50      # stop after N fetches (testing)
"""

import argparse
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' required. Install: python3 -m pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: 'beautifulsoup4' required. Install: python3 -m pip install beautifulsoup4 lxml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
HTML_CACHE = ROOT / "data" / "reference" / "external" / "html_cache"
INDEX_HTML = HTML_CACHE / "limitless_index.html"

BASE_URL = "https://pocket.limitlesstcg.com"
FETCH_DELAY = 0.6  # seconds between requests (polite rate limiting)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PTCGP-DB-Research/1.0; "
        "personal collection tool; contact jackpendley9@gmail.com)"
    )
}


def fetch_and_cache(url: str, cache_file: Path, dry_run: bool) -> bool:
    """
    Fetch a URL and save to cache_file. Returns True if fetched, False if skipped/failed.
    Skips if cache_file already exists.
    """
    if cache_file.exists():
        return False  # Already cached

    if dry_run:
        print(f"  [DRY RUN] would fetch: {url}")
        return True

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            print(f"  WARN 404: {url}")
            return False
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"  WARN fetch failed: {url}: {exc}")
        return False

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(resp.text, encoding="utf-8")
    return True


def parse_set_list(index_html: str) -> list[dict]:
    """
    Parse the cached Limitless index page for set codes and card counts.
    Returns deduplicated list of {code, card_count} dicts, ordered newest-first.
    """
    soup = BeautifulSoup(index_html, "lxml")
    seen: dict[str, int | None] = {}

    links = soup.find_all("a", href=re.compile(r"/cards/[A-Z][0-9]"))
    for link in links:
        href = link.get("href", "")
        m = re.search(r"/cards/([A-Z][A-Za-z0-9]*)\s*$", href)
        if not m:
            continue
        code = m.group(1)
        if code in seen:
            continue  # Deduplicate — take first occurrence (newest in index)

        # Card count: the <tr> grandparent contains the count as the last number
        row = link.find_parent("tr")
        count_text = row.get_text(separator=" ", strip=True) if row else ""
        # Count is the last 3-digit number in the row (date format is D Mon YY)
        count_matches = re.findall(r"\b(\d{2,3})\b", count_text)
        # Filter to numbers that look like card counts (>= 50, <= 999)
        card_counts = [int(x) for x in count_matches if 50 <= int(x) <= 999]
        card_count = card_counts[-1] if card_counts else None

        seen[code] = card_count

    return [{"code": code, "card_count": count} for code, count in seen.items()]


def get_card_count_from_grid(grid_html: str, set_code: str) -> int | None:
    """Parse card count from a cached grid page."""
    soup = BeautifulSoup(grid_html, "lxml")
    links = soup.find_all("a", href=re.compile(rf"/cards/{re.escape(set_code)}/\d+"))
    numbers = []
    for link in links:
        m = re.search(rf"/cards/{re.escape(set_code)}/(\d+)", link.get("href", ""))
        if m:
            numbers.append(int(m.group(1)))
    return max(numbers) if numbers else None


def main():
    parser = argparse.ArgumentParser(description="Fetch missing Limitless card HTML into cache")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched; no writes")
    parser.add_argument("--set", dest="only_set", metavar="SET_CODE",
                        help="Restrict fetch to one set code (e.g. A1)")
    parser.add_argument("--max", type=int, default=None, metavar="N",
                        help="Stop after N fetch operations (for testing)")
    args = parser.parse_args()

    if not INDEX_HTML.exists():
        print(f"ERROR: cached index not found at {INDEX_HTML}")
        print("Run: python3 scripts/build_external_reference.py --use-cache")
        sys.exit(1)

    print(f"\n=== fetch_missing_html.py {'[DRY RUN]' if args.dry_run else '[FETCH]'} ===")

    index_html = INDEX_HTML.read_text(encoding="utf-8")
    sets = parse_set_list(index_html)
    if not sets:
        print("ERROR: No sets found in cached index.")
        sys.exit(1)

    print(f"Found {len(sets)} sets in index.")

    if args.only_set:
        sets = [s for s in sets if s["code"] == args.only_set]
        if not sets:
            print(f"ERROR: Set {args.only_set!r} not found in index.")
            sys.exit(1)

    total_fetched = 0
    total_skipped = 0
    total_failed = 0

    for s in sets:
        code = s["code"]
        card_count = s["card_count"]

        # 1. Grid page
        grid_file = HTML_CACHE / f"grid_{code}.html"
        grid_url = f"{BASE_URL}/cards/{code}"
        fetched = fetch_and_cache(grid_url, grid_file, args.dry_run)
        if fetched:
            print(f"\nSet {code}: fetched grid")
            if not args.dry_run:
                time.sleep(FETCH_DELAY)
            total_fetched += 1
            if args.max and total_fetched >= args.max:
                print(f"\nReached --max {args.max}. Stopping.")
                break
        else:
            if not grid_file.exists():
                total_failed += 1
            else:
                total_skipped += 1

        # 2. Determine card count from grid if index count was None
        if card_count is None and grid_file.exists():
            card_count = get_card_count_from_grid(grid_file.read_text(encoding="utf-8"), code)

        if not card_count:
            print(f"  WARN: Could not determine card count for {code}; skipping cards")
            continue

        print(f"Set {code}: {card_count} cards expected", end="")

        # Count how many are already cached
        cached = sum(
            1 for n in range(1, card_count + 1)
            if (HTML_CACHE / f"card_{code}_{n:04d}.html").exists()
        )
        missing_count = card_count - cached
        print(f", {cached} cached, {missing_count} missing")

        # 3. Fetch missing card pages
        for num in range(1, card_count + 1):
            cache_file = HTML_CACHE / f"card_{code}_{num:04d}.html"
            card_url = f"{BASE_URL}/cards/{code}/{num}"

            fetched = fetch_and_cache(card_url, cache_file, args.dry_run)
            if fetched:
                total_fetched += 1
                if not args.dry_run:
                    if total_fetched % 25 == 0:
                        print(f"  ... fetched {total_fetched} total ({code} #{num})")
                    time.sleep(FETCH_DELAY)
            elif not cache_file.exists():
                total_failed += 1
            else:
                total_skipped += 1

            if args.max and total_fetched >= args.max:
                print(f"\nReached --max {args.max}. Stopping.")
                break

        if args.max and total_fetched >= args.max:
            break

    print(f"\n=== Summary ===")
    print(f"  Fetched:  {total_fetched}")
    print(f"  Skipped (already cached): {total_skipped}")
    print(f"  Failed/404: {total_failed}")
    if args.dry_run:
        print(f"\nDRY RUN: run without --dry-run to apply.")


if __name__ == "__main__":
    main()
