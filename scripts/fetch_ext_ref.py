#!/usr/bin/env python3
"""
Fetch and populate data/reference/external/external_card_reference.json for
all sets that are missing from it.

ext_ref provides per-card metadata (card_category, pokemon_type, stage, hp,
is_ex) that sync_collection.py uses for auto-add. It currently covers only
B-sets; A1–A4a and PROMO sets are absent, forcing heuristic inference.

Usage:
    python3 scripts/fetch_ext_ref.py               # fetch all missing
    python3 scripts/fetch_ext_ref.py --set A4       # one set only
    python3 scripts/fetch_ext_ref.py --dry-run      # show what would be fetched
    python3 scripts/fetch_ext_ref.py --delay 1.5    # seconds between requests

This script fetches card pages from pocket.limitlesstcg.com and parses:
  - card_category  (Pokemon | Item | Supporter | Stadium | Tool)
  - pokemon_type   (Grass | Fire | Water | ... | None for Trainers)
  - stage          (Basic | Stage 1 | Stage 2 | None for Trainers)
  - hp             (integer | None for Trainers)
  - is_ex          (bool, inferred from card name)

Output: updates data/reference/external/external_card_reference.json in-place.
After running, also run: python3 scripts/build_pack_sources.py
to propagate the metadata into pack_sources.json.

Exit codes:
    0  All cards fetched (or nothing to fetch)
    1  Fatal error
    2  Some fetches failed (partial success)
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 required. Install: python3 -m pip install beautifulsoup4 lxml")
    sys.exit(1)

ROOT        = Path(__file__).resolve().parent.parent
EXT_REF     = ROOT / "data" / "reference" / "external" / "external_card_reference.json"
PACK_SOURCES = ROOT / "data" / "reference" / "pack_sources.json"

_BASE_URL = "https://pocket.limitlesstcg.com/cards"

# Limitless card page HTML selectors — adjust if the site layout changes.
# These were derived by inspecting existing ext_ref data and the Limitless HTML
# page structure. Test with: python3 scripts/fetch_ext_ref.py --set B1 --dry-run
_ENERGY_TYPE_ICONS: dict[str, str] = {
    "grass":    "Grass",
    "fire":     "Fire",
    "water":    "Water",
    "lightning":"Lightning",
    "psychic":  "Psychic",
    "fighting": "Fighting",
    "darkness": "Darkness",
    "metal":    "Metal",
    "dragon":   "Dragon",
    "colorless":"Colorless",
    "normal":   "Colorless",
}

_STAGE_KEYWORDS = {
    "basic":   "Basic",
    "stage 1": "Stage 1",
    "stage 2": "Stage 2",
}

_TRAINER_KEYWORDS = {
    "item":          "Item",
    "supporter":     "Supporter",
    "stadium":       "Stadium",
    "pokémon tool":  "Tool",
    "pokemon tool":  "Tool",
    "tool":          "Tool",
}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower().strip()).strip("_")


def _fetch_page(url: str) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


def _parse_card_page(html: str, set_code: str, number: int, source_url: str) -> dict | None:
    """Parse a Limitless card detail page for ext_ref metadata."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None

    # ── Card name ────────────────────────────────────────────────────────
    name_el = (
        soup.select_one("span.card-text-name")
        or soup.select_one(".card-text-title .card-text-name")
        or soup.select_one("h1.card-title")
    )
    if name_el:
        name = name_el.get_text(strip=True)
    else:
        title_el = soup.find("title")
        if title_el:
            raw = title_el.get_text(strip=True)
            name = re.split(r"\s*[•–]\s*", raw)[0].strip()
        else:
            return None
    if not name or len(name) < 2:
        return None

    is_ex = name.lower().endswith(" ex")

    # ── Gather all text blocks for type/stage/category detection ────────
    # Limitless card pages vary slightly in structure; gather all relevant text.
    all_text_blocks: list[str] = []

    # Primary: card-text sections
    for el in soup.select(".card-text-type, .card-text-section, .card-text-title, .card-text-supertype"):
        t = el.get_text(separator=" ", strip=True).lower()
        if t:
            all_text_blocks.append(t)

    # Fallback: any element that looks like a type line
    for el in soup.select("p, span, div"):
        classes = " ".join(el.get("class", []))
        if any(kw in classes for kw in ("type", "super", "subtype", "stage", "category")):
            t = el.get_text(separator=" ", strip=True).lower()
            if t and len(t) < 80:
                all_text_blocks.append(t)

    joined = " ".join(all_text_blocks)

    # ── Determine card_category ──────────────────────────────────────────
    card_category: str | None = None
    trainer_subtype: str | None = None

    # Check for Trainer keywords first (they'd appear in the type line)
    for keyword, subtype in _TRAINER_KEYWORDS.items():
        if keyword in joined:
            card_category = subtype  # Item / Supporter / Stadium / Tool
            trainer_subtype = subtype
            break

    # If no trainer keyword found, check for Pokemon indicators
    if not card_category:
        if any(kw in joined for kw in ("basic pokémon", "basic pokemon", "stage 1", "stage 2", "hp")):
            card_category = "Pokemon"
        elif is_ex:
            card_category = "Pokemon"

    # ── HP ───────────────────────────────────────────────────────────────
    hp: int | None = None
    if card_category == "Pokemon" or card_category is None:
        # Try span.card-text-hp first
        hp_el = soup.select_one("span.card-text-hp, .card-text-hp")
        if hp_el:
            m = re.search(r"(\d+)", hp_el.get_text())
            if m:
                hp = int(m.group(1))
        # Fallback: "HP \d+" pattern anywhere in page text
        if hp is None:
            m = re.search(r"\bHP\s+(\d{2,3})\b", html)
            if m:
                hp = int(m.group(1))

    # ── Stage ────────────────────────────────────────────────────────────
    stage: str | None = None
    if card_category == "Pokemon" or (card_category is None and hp is not None):
        for kw, label in _STAGE_KEYWORDS.items():
            if kw in joined:
                stage = label
                break
        card_category = card_category or "Pokemon"

    # ── Pokemon type (energy type) ────────────────────────────────────────
    pokemon_type: str | None = None
    if card_category == "Pokemon":
        # Try energy type icons: <img alt="Grass"> or <img alt="[Grass]">
        for img in soup.select("img[alt]"):
            alt = img.get("alt", "").strip("[]").strip().lower()
            if alt in _ENERGY_TYPE_ICONS:
                pokemon_type = _ENERGY_TYPE_ICONS[alt]
                break
        # Fallback: CSS classes like "icon-grass"
        if pokemon_type is None:
            for el in soup.select("[class]"):
                for cls in el.get("class", []):
                    cls_lower = cls.lower()
                    for key, val in _ENERGY_TYPE_ICONS.items():
                        if key in cls_lower:
                            pokemon_type = val
                            break
                if pokemon_type:
                    break

    # ── Rarity ───────────────────────────────────────────────────────────
    rarity: str | None = None
    rarity_symbols = {
        "◊◊◊◊": "four_diamond", "◊◊◊": "three_diamond",
        "◊◊": "two_diamond", "◊": "one_diamond",
        "☆☆☆": "triple_star", "☆☆": "double_star", "☆": "one_star",
        "♛": "crown", "✦": "promo",
    }
    details = soup.select_one(".prints-current-details")
    if details:
        raw = details.get_text()
        for sym, label in rarity_symbols.items():
            if sym in raw:
                rarity = label
                break

    if not card_category:
        return None  # Could not determine card type — skip

    return {
        "set_code":      set_code,
        "number":        number,
        "name":          name,
        "card_category": card_category,
        "pokemon_type":  pokemon_type,
        "stage":         stage,
        "hp":            hp,
        "is_ex":         is_ex,
        "rarity":        rarity,
        "source_url":    source_url,
        "source":        "limitless",
        "normalized_name": _normalize(name),
    }


def _load_ext_ref() -> tuple[list[dict], dict[tuple[str, int], int]]:
    """Load ext_ref and return (records_list, {(set_code, number) → index})."""
    if not EXT_REF.exists():
        return [], {}
    records = json.loads(EXT_REF.read_text(encoding="utf-8"))
    index = {(r.get("set_code"), r.get("number")): i for i, r in enumerate(records)}
    return records, index


def _load_pack_sources_missing(ext_index: dict[tuple[str, int], int]) -> list[dict]:
    """Return pack_sources records that have no ext_ref entry (need fetching)."""
    if not PACK_SOURCES.exists():
        return []
    data = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
    records = data.get("records", data) if isinstance(data, dict) else data
    missing = []
    seen: set[tuple[str, int]] = set()
    for r in records:
        sc = str(r.get("set_code", "")).strip()
        cn_raw = r.get("card_number")
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            continue
        key = (sc, cn)
        if key in seen or key in ext_index:
            continue
        seen.add(key)
        missing.append({
            "set_code": sc,
            "number": cn,
            "source_url": r.get("source_url") or f"{_BASE_URL}/{sc}/{cn}",
        })
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and populate ext_ref for missing sets.")
    parser.add_argument("--set",      metavar="SET_CODE",
                        help="Only fetch cards for this set (e.g. A4)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print what would be fetched, no writes")
    parser.add_argument("--delay",    type=float, default=0.5,
                        help="Seconds to wait between requests (default: 0.5)")
    parser.add_argument("--limit",    type=int, default=0,
                        help="Max cards to fetch per run (0 = no limit)")
    args = parser.parse_args()

    ext_records, ext_index = _load_ext_ref()
    missing = _load_pack_sources_missing(ext_index)

    if args.set:
        missing = [m for m in missing if m["set_code"].upper() == args.set.upper()]

    if args.limit:
        missing = missing[:args.limit]

    if not missing:
        print("ext_ref is already complete for the requested scope.")
        return 0

    # Group by set for reporting
    by_set: dict[str, int] = {}
    for m in missing:
        by_set[m["set_code"]] = by_set.get(m["set_code"], 0) + 1
    print(f"\nCards to fetch: {len(missing)} across {len(by_set)} set(s)")
    for sc in sorted(by_set):
        print(f"  {sc}: {by_set[sc]}")

    if args.dry_run:
        print("\nDRY RUN — no fetches performed.")
        return 0

    fetched = 0
    failed  = 0
    for i, card in enumerate(missing):
        sc, num, url = card["set_code"], card["number"], card["source_url"]
        print(f"  [{i+1}/{len(missing)}] {sc}/{num} … ", end="", flush=True)

        html = _fetch_page(url)
        if not html:
            print("FAILED")
            failed += 1
            time.sleep(args.delay)
            continue

        parsed = _parse_card_page(html, sc, num, url)
        if not parsed:
            print(f"could not parse ({url})")
            failed += 1
            time.sleep(args.delay)
            continue

        print(f"OK — {parsed['name']} ({parsed['card_category']})")
        ext_records.append(parsed)
        fetched += 1
        time.sleep(args.delay)

    if fetched:
        ext_records.sort(key=lambda r: (r.get("set_code", ""), r.get("number", 0)))
        EXT_REF.write_text(json.dumps(ext_records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Wrote {len(ext_records)} records to {EXT_REF.relative_to(ROOT)}")
        print("  Next: run  python3 scripts/build_pack_sources.py  to propagate metadata.")
    else:
        print("\n  No records added.")

    if failed:
        print(f"\n  {failed} card(s) failed. Re-run to retry.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
