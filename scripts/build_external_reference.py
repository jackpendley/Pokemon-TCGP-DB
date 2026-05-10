#!/usr/bin/env python3
"""
Fetch and cache structured card metadata from external PTCGP reference sources.

Sources:
    limitless  — https://pocket.limitlesstcg.com  (scraped HTML, polite rate limiting)
    game8      — supplemental; future expansion

Outputs:
    data/reference/external/external_card_reference.json  — parsed card objects
    data/reference/external/external_card_names.txt       — one name per line
    data/reference/external/reference_source_report.md    — fetch/parse summary

HTML cache: data/reference/external/html_cache/ (gitignored)

Usage:
    python3 scripts/build_external_reference.py
    python3 scripts/build_external_reference.py --source limitless
    python3 scripts/build_external_reference.py --use-cache          # skip fetch, use cached HTML
    python3 scripts/build_external_reference.py --refresh            # ignore cache, re-fetch all
    python3 scripts/build_external_reference.py --max-cards 50       # stop after N cards (testing)
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' required.  Install: python3 -m pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: 'beautifulsoup4' required.  Install: python3 -m pip install beautifulsoup4 lxml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://pocket.limitlesstcg.com"
CARDS_INDEX = f"{BASE_URL}/cards"

EXTERNAL_DIR = Path("data/reference/external")
HTML_CACHE_DIR = EXTERNAL_DIR / "html_cache"
OUT_REFERENCE = EXTERNAL_DIR / "external_card_reference.json"
OUT_NAMES = EXTERNAL_DIR / "external_card_names.txt"
OUT_REPORT = EXTERNAL_DIR / "reference_source_report.md"

# Polite rate limiting between requests
FETCH_DELAY = 0.5  # seconds between page fetches

# User-agent for polite scraping
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PTCGP-DB-Research/1.0; "
        "personal collection tool; contact jackpendley9@gmail.com)"
    )
}

# Rarity symbol → normalized name mapping
# Characters verified against Limitless HTML (U+25CA = LOZENGE = common diamond)
RARITY_MAP = {
    "◊◊◊◊": "four_diamond",
    "◊◊◊":  "three_diamond",
    "◊◊":   "two_diamond",
    "◊":    "one_diamond",
    "☆☆☆":  "triple_star",
    "☆☆":   "double_star",
    "☆":    "one_star",
    "♛":    "crown",
    "✦":    "promo",
}
# Check longer strings first (order matters in search)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_html(url: str, cache_key: str, use_cache: bool, refresh: bool) -> str | None:
    """
    Fetch HTML for a URL.  If use_cache and not refresh, serve from disk cache.
    Returns HTML string or None on failure.
    """
    cache_file = HTML_CACHE_DIR / f"{cache_key}.html"

    if use_cache and not refresh and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException as exc:
        print(f"  WARN: fetch failed {url}: {exc}")
        return None

    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------------------
# Limitless parsing
# ---------------------------------------------------------------------------

def parse_set_codes(html: str) -> list[dict]:
    """
    Parse the /cards index page → list of {code, name, url, card_count}.
    """
    soup = BeautifulSoup(html, "lxml")
    sets = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Match /cards/A1, /cards/B3, etc. — exactly two path segments
        m = re.match(r"^/cards/([A-Z0-9a-z]+)$", href)
        if not m:
            continue
        code = m.group(1)
        if any(s["code"] == code for s in sets):
            continue

        label = link.get_text(separator=" ", strip=True)
        # Try to extract a card count from the label ("A1 — 286 cards")
        count_m = re.search(r"(\d+)\s*card", label, re.IGNORECASE)
        count = int(count_m.group(1)) if count_m else None

        sets.append({
            "code": code,
            "name": label,
            "url": f"{BASE_URL}/cards/{code}",
            "card_count": count,
        })

    return sets


def parse_card_numbers(html: str, set_code: str) -> list[int]:
    """
    Parse a set grid page → sorted list of card numbers found in href links.
    """
    soup = BeautifulSoup(html, "lxml")
    numbers = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        m = re.match(rf"^/cards/{re.escape(set_code)}/(\d+)$", href)
        if m:
            numbers.add(int(m.group(1)))

    return sorted(numbers)


def parse_card_detail(html: str, set_code: str, number: int, url: str) -> dict | None:
    """
    Parse a card detail page → card dict or None if unparseable.

    Limitless HTML selectors (verified against live pages):
        span.card-text-name  → card name
        p.card-text-title    → "Tangela - Grass  - 80 HP"
        p.card-text-type     → "Pokémon - Basic" or "Trainer - Item"
        div.card-prints-current → "#1 · ◊"  (rarity diamond U+25CA)
    """
    soup = BeautifulSoup(html, "lxml")

    # --- Card name ---
    name_el = soup.select_one("span.card-text-name")
    if name_el:
        name = name_el.get_text(strip=True)
    else:
        # Fallback: <title> strip everything after " • " or " – "
        title_el = soup.find("title")
        if title_el:
            raw = title_el.get_text(strip=True)
            # "Tangela • Pulsing Aura (B3) #1 – Limitless TCG Pocket Database"
            name = re.split(r"\s*[•–]\s*", raw)[0].strip()
        else:
            name = ""

    if not name or len(name) < 2:
        return None

    # --- Type and HP ---
    pokemon_type = None
    hp = None

    title_p = soup.select_one("p.card-text-title")
    if title_p:
        title_text = title_p.get_text(separator=" ", strip=True)
    else:
        title_text = soup.get_text(separator="\n")

    hp_m = re.search(
        r"\b(Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal|Dragon|Colorless)"
        r"[^0-9]{0,20}?(\d+)\s*HP",
        title_text,
        re.IGNORECASE,
    )
    if hp_m:
        pokemon_type = hp_m.group(1).title()
        hp = int(hp_m.group(2))

    # --- Card category and stage ---
    card_category = "Unknown"
    stage = "Unknown"

    type_p = soup.select_one("p.card-text-type")
    type_text = type_p.get_text(separator=" ", strip=True) if type_p else ""

    # "Pokémon - Basic", "Trainer - Item", "Trainer - Supporter", etc.
    cat_m = re.match(
        r"(Pok[eé]mon|Trainer|Item|Supporter|Stadium|Tool|Fossil)\s*[-–]\s*(.*)",
        type_text,
        re.IGNORECASE,
    )
    if cat_m:
        raw_cat = cat_m.group(1).strip()
        raw_stage = cat_m.group(2).strip()
        if re.match(r"pok[eé]mon", raw_cat, re.IGNORECASE):
            card_category = "Pokemon"
            stage_clean = re.sub(r"\s+", " ", raw_stage).title()
            stage = stage_clean if stage_clean else "Unknown"
        else:
            # Trainer sub-type in first group or second group
            for sub in ("Item", "Supporter", "Stadium", "Tool", "Fossil"):
                if re.search(rf"\b{sub}\b", type_text, re.IGNORECASE):
                    card_category = sub
                    break
            else:
                card_category = raw_cat.title()
            stage = "None"
    elif type_text:
        # No dash separator; whole string is category
        for sub in ("Item", "Supporter", "Stadium", "Tool", "Fossil"):
            if re.search(rf"\b{sub}\b", type_text, re.IGNORECASE):
                card_category = sub
                stage = "None"
                break

    # --- Rarity ---
    rarity = "unknown"
    prints_el = soup.select_one(".card-prints-current")
    prints_text = prints_el.get_text(strip=True) if prints_el else ""
    # Check longer patterns first (order in RARITY_MAP matters)
    for symbol, label in RARITY_MAP.items():
        if symbol in prints_text:
            rarity = label
            break

    # --- is_ex ---
    is_ex = bool(
        re.search(r"\bex\b", name, re.IGNORECASE) or
        re.match(r"^mega\s", name, re.IGNORECASE)
    )

    # --- special_type hint (conservative inference from rarity) ---
    special_type = "normal"
    if rarity == "crown":
        special_type = "crown_gold"
    elif rarity == "triple_star":
        special_type = "illustration_rare"
    elif rarity == "double_star":
        special_type = "special_art"
    elif rarity == "one_star" and is_ex:
        special_type = "normal"

    return {
        "set_code": set_code,
        "number": number,
        "name": name,
        "card_category": card_category,
        "pokemon_type": pokemon_type or ("None" if card_category != "Pokemon" else "Unknown"),
        "stage": stage,
        "hp": hp,
        "is_ex": is_ex,
        "rarity": rarity,
        "special_type": special_type,
        "source_url": url,
        "source": "limitless",
    }


# ---------------------------------------------------------------------------
# Main scrape driver
# ---------------------------------------------------------------------------

def scrape_limitless(use_cache: bool, refresh: bool, max_cards: int | None) -> list[dict]:
    """
    Full Limitless scrape:
        1. Fetch /cards index → set codes
        2. For each set, fetch grid → card numbers
        3. For each card, fetch detail → parse metadata

    Returns list of card dicts.
    """
    print(f"Fetching set index: {CARDS_INDEX}")
    index_html = fetch_html(CARDS_INDEX, "limitless_index", use_cache, refresh)
    if not index_html:
        print("ERROR: Could not fetch Limitless card index.")
        return []

    sets = parse_set_codes(index_html)
    if not sets:
        print("WARN: No set codes found on index page.  Check HTML structure.")
        return []

    print(f"  Found {len(sets)} sets: {', '.join(s['code'] for s in sets)}")

    all_cards: list[dict] = []
    total_fetched = 0

    for s in sets:
        code = s["code"]
        grid_url = s["url"]
        print(f"\nSet {code}: {grid_url}")

        grid_html = fetch_html(grid_url, f"grid_{code}", use_cache, refresh)
        if not use_cache:
            time.sleep(FETCH_DELAY)

        if not grid_html:
            print(f"  WARN: Could not fetch grid for {code}")
            continue

        numbers = parse_card_numbers(grid_html, code)

        # If grid parsing found nothing, try sequential up to declared count
        if not numbers and s["card_count"]:
            print(f"  Grid links not found; using declared count {s['card_count']}")
            numbers = list(range(1, s["card_count"] + 1))
        elif not numbers:
            print(f"  No card numbers found for {code}, skipping")
            continue

        print(f"  {len(numbers)} card(s) in {code}")

        for num in numbers:
            if max_cards is not None and total_fetched >= max_cards:
                print(f"  Reached --max-cards {max_cards}, stopping early")
                return all_cards

            card_url = f"{BASE_URL}/cards/{code}/{num}"
            cache_key = f"card_{code}_{num:04d}"
            card_html = fetch_html(card_url, cache_key, use_cache, refresh)

            if not use_cache:
                time.sleep(FETCH_DELAY)

            if not card_html:
                print(f"  WARN: 404 or error for {card_url}")
                continue

            card = parse_card_detail(card_html, code, num, card_url)
            if card:
                all_cards.append(card)
                total_fetched += 1
            else:
                print(f"  WARN: Could not parse {card_url}")

        print(f"  Parsed {len(all_cards)} cards so far")

    return all_cards


# ---------------------------------------------------------------------------
# Deduplication and normalization
# ---------------------------------------------------------------------------

def deduplicate(cards: list[dict]) -> list[dict]:
    """
    Deduplicate by (name, set_code, number).  Later entries overwrite earlier.
    Preserves insertion order of first occurrence.
    """
    seen: dict[tuple, int] = {}
    deduped: list[dict] = []
    for card in cards:
        key = (card.get("set_code"), card.get("number"))
        if key in seen:
            deduped[seen[key]] = card
        else:
            seen[key] = len(deduped)
            deduped.append(card)
    return deduped


def normalize_name(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_outputs(cards: list[dict], sources_used: list[str], errors: list[str]) -> None:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    for card in cards:
        card["normalized_name"] = normalize_name(card["name"])

    OUT_REFERENCE.write_text(
        json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    names = sorted({c["name"] for c in cards})
    OUT_NAMES.write_text("\n".join(names) + "\n", encoding="utf-8")

    # Report
    by_set: dict[str, int] = {}
    for c in cards:
        by_set[c.get("set_code", "?")] = by_set.get(c.get("set_code", "?"), 0) + 1

    lines = [
        "# External Reference Source Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()[:19]}Z",
        f"Sources used: {', '.join(sources_used) if sources_used else 'none'}",
        f"Total cards: {len(cards)}",
        f"Unique names: {len(names)}",
        "",
        "## Cards by Set",
        "",
        "| Set | Count |",
        "|---|---|",
    ]
    for code, count in sorted(by_set.items()):
        lines.append(f"| {code} | {count} |")

    if errors:
        lines += ["", "## Errors / Warnings", ""]
        for e in errors[:50]:
            lines.append(f"- {e}")
        if len(errors) > 50:
            lines.append(f"- … {len(errors) - 50} more")

    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {len(cards)} cards → {OUT_REFERENCE}")
    print(f"Wrote {len(names)} names  → {OUT_NAMES}")
    print(f"Report                  → {OUT_REPORT}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch PTCGP card metadata from external sources."
    )
    parser.add_argument(
        "--source",
        choices=["limitless", "game8", "all"],
        default="all",
        help="Which source(s) to fetch (default: all).",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cached HTML files if present (skip network fetches).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cache and re-fetch everything.",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N cards (for quick tests).",
    )
    args = parser.parse_args()

    if args.use_cache and args.refresh:
        print("ERROR: --use-cache and --refresh are mutually exclusive.")
        sys.exit(1)

    sources_used: list[str] = []
    all_cards: list[dict] = []
    errors: list[str] = []

    do_limitless = args.source in ("limitless", "all")
    do_game8 = args.source in ("game8", "all")

    if do_limitless:
        print("=== Limitless TCG Pocket ===")
        cards = scrape_limitless(
            use_cache=args.use_cache,
            refresh=args.refresh,
            max_cards=args.max_cards,
        )
        if cards:
            all_cards.extend(cards)
            sources_used.append("limitless")
            print(f"Limitless: {len(cards)} cards fetched")
        else:
            errors.append("Limitless: no cards returned")
            print("WARN: Limitless returned no cards")

    if do_game8:
        print("\n=== Game8 (not yet implemented) ===")
        print("  Skipping — Game8 integration planned for a future phase")

    if not all_cards:
        print("\nNo cards collected.  Check network access and source pages.")
        sys.exit(1)

    all_cards = deduplicate(all_cards)
    print(f"\nTotal after deduplication: {len(all_cards)}")

    write_outputs(all_cards, sources_used, errors)


if __name__ == "__main__":
    main()
