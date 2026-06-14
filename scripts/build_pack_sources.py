#!/usr/bin/env python3
"""
Builds data/reference/pack_sources.json from cached Limitless TCG Pocket HTML.

Input (in priority order):
    1. data/reference/external/html_cache/card_<SET>_<NUM>.html  (primary)
    2. data/reference/external/external_card_reference.json      (supplemental metadata)

Output:
    data/reference/pack_sources.json

Pack assignment rules derived from Limitless HTML:
    Multi-pack sets (A1, A2, A3, A4, B1):
        Cards with a "· PackName pack" label are pack-specific (confidence=high).
        Cards without a pack label are shared across all packs (pack_name=null, confidence=medium).

    Single-pack sets (A1a, A2a, A2b, A3a, A3b, A4a, A4b, B1a, B2, B2a, B2b, B3, B3A):
        All cards are in the one expansion pack.
        pack_name = cleaned expansion name (confidence=medium).

Confidence rules:
    high   — pack_name comes directly from the "· PackName pack" HTML label.
    medium — single-pack expansion or shared pool (pack_name inferred).
    low    — pack unknown / could not be determined.

Usage:
    python3 scripts/build_pack_sources.py            # use cached HTML
    python3 scripts/build_pack_sources.py --dry-run  # show stats only, no file write
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (SINGLE_PACK_SETS, MULTI_PACK_SETS, RARITY_SYMBOLS,
                             canonical_set_code, ROOT, REFERENCE_DIR,
                             EXT_REF_JSON, PACK_SOURCES_JSON as OUT_JSON)

HTML_CACHE = REFERENCE_DIR / "external" / "html_cache"

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 required. Install: python3 -m pip install beautifulsoup4 lxml")
    sys.exit(1)

RARITY_MAP = RARITY_SYMBOLS


def clean_expansion_name(raw: str) -> str:
    """Remove set code suffix like ' (B1)' or ' (B2a)' from expansion name."""
    cleaned = re.sub(r"\s*\([A-Z0-9a-z]+\)\s*$", "", raw)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_card_html(html: str, set_code: str, number: int) -> dict | None:
    """
    Parse a Limitless card detail page.

    Returns a dict with:
        name, expansion, pack_name, rarity, confidence, notes, source_url
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None

    # --- Card name ---
    name_el = soup.select_one("span.card-text-name")
    if name_el:
        name = name_el.get_text(strip=True)
    else:
        title_el = soup.find("title")
        if title_el:
            raw = title_el.get_text(strip=True)
            name = re.split(r"\s*[•–]\s*", raw)[0].strip()
        else:
            name = ""
    if not name or len(name) < 2:
        return None

    # --- Source URL ---
    source_url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{number}"

    # --- prints-current-details: expansion + pack ---
    expansion = ""
    pack_name = None
    rarity = "unknown"
    confidence = "low"
    notes = ""

    details = soup.select_one(".prints-current-details")
    if details:
        spans = details.find_all("span")

        if len(spans) >= 1:
            expansion_raw = spans[0].get_text(separator=" ", strip=True)
            expansion = clean_expansion_name(expansion_raw)

        if len(spans) >= 2:
            second_text = spans[1].get_text(separator=" ", strip=True)

            # Extract rarity
            for symbol, label in RARITY_MAP.items():
                if symbol in second_text:
                    rarity = label
                    break

            # Extract pack name (only present for multi-pack sets)
            pack_match = re.search(
                r"·\s*(.+?)\s+pack\b", second_text, re.IGNORECASE
            )
            if pack_match:
                pack_name = pack_match.group(1).strip()
                confidence = "high"
                notes = f"Pack label from Limitless HTML: '{pack_name} pack'"
            else:
                if set_code in SINGLE_PACK_SETS:
                    # Single-pack expansion: pack_name = expansion name
                    pack_name = expansion if expansion else None
                    confidence = "medium"
                    notes = f"Single-pack expansion; all cards in '{expansion}'"
                elif set_code in MULTI_PACK_SETS:
                    # Multi-pack set but no pack label → shared pool
                    pack_name = None
                    confidence = "medium"
                    notes = "No pack label in Limitless HTML; shared across all packs in this expansion"
                else:
                    pack_name = expansion if expansion else None
                    confidence = "medium"
                    notes = f"Pack structure unknown for set {set_code}; using expansion name"
    else:
        notes = "No .prints-current-details element found in cached HTML"

    return {
        "name": name,
        "expansion": expansion,
        "pack_name": pack_name,
        "rarity": rarity,
        "confidence": confidence,
        "notes": notes,
        "source_url": source_url,
    }


def load_ext_ref():
    """Load external reference for supplemental metadata lookup."""
    if not EXT_REF_JSON.exists():
        return {}
    try:
        data = json.loads(EXT_REF_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    index = {}
    for entry in data:
        key = (entry.get("set_code"), entry.get("number"))
        if key[0] and key[1] is not None:
            index[key] = entry
    return index


def build_records(ext_index: dict, dry_run: bool) -> list[dict]:
    """Parse all cached HTML files and build pack source records."""
    if not HTML_CACHE.exists():
        print(f"ERROR: HTML cache not found at {HTML_CACHE}", file=sys.stderr)
        sys.exit(1)

    # Collect all card HTML files
    card_files = sorted(
        f for f in HTML_CACHE.iterdir()
        if re.match(r"card_[A-Za-z0-9]+_\d+\.html", f.name)
    )

    if not card_files:
        print("ERROR: No card HTML files found in cache.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(card_files)} cached card HTML files.")

    records = []
    stats = {
        "total": 0,
        "parsed": 0,
        "skipped": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "by_set": {},
        "by_pack": {},
        "pack_specific": 0,
        "shared_pool": 0,
        "single_pack": 0,
        "warnings": [],
    }

    for fpath in card_files:
        m = re.match(r"card_([A-Za-z0-9]+)_(\d+)\.html", fpath.name)
        if not m:
            continue
        set_code = canonical_set_code(m.group(1))
        number = int(m.group(2))
        stats["total"] += 1

        html = fpath.read_text(encoding="utf-8")
        parsed = parse_card_html(html, set_code, number)

        if not parsed:
            stats["skipped"] += 1
            stats["warnings"].append(f"Could not parse {fpath.name}")
            continue

        if set_code not in SINGLE_PACK_SETS and set_code not in MULTI_PACK_SETS:
            warn = (f"Unknown set structure for {set_code}; assumed single-pack. "
                    "Add to SINGLE_PACK_SETS or MULTI_PACK_SETS if incorrect.")
            if warn not in stats["warnings"]:
                stats["warnings"].append(warn)

        # Supplemental metadata from ext_ref
        ext = ext_index.get((set_code, number), {})
        card_category = ext.get("card_category")
        pokemon_type = ext.get("pokemon_type")
        is_ex = ext.get("is_ex")

        record = {
            "set_code": set_code,
            "card_number": number,
            "card_name": parsed["name"],
            "pack_name": parsed["pack_name"],
            "expansion": parsed["expansion"],
            "rarity": parsed["rarity"] if parsed["rarity"] != "unknown" else None,
            "card_category": card_category,
            "pokemon_type": pokemon_type,
            "is_ex": is_ex,
            "source_url": parsed["source_url"],
            "source": "limitless",
            "confidence": parsed["confidence"],
            "notes": parsed["notes"],
        }

        stats["parsed"] += 1
        stats["by_set"][set_code] = stats["by_set"].get(set_code, 0) + 1

        pack_key = f"{set_code}:{parsed['pack_name'] or 'shared'}"
        stats["by_pack"][pack_key] = stats["by_pack"].get(pack_key, 0) + 1

        if parsed["confidence"] == "high":
            stats["high_confidence"] += 1
            stats["pack_specific"] += 1
        elif parsed["confidence"] == "medium":
            stats["medium_confidence"] += 1
            if parsed["pack_name"] is None:
                stats["shared_pool"] += 1
            else:
                stats["single_pack"] += 1
        else:
            stats["low_confidence"] += 1

        records.append(record)

    # Sort by set_code, card_number
    records.sort(key=lambda r: (r["set_code"], r["card_number"]))

    return records, stats


def print_stats(stats: dict):
    print(f"\n=== Build Stats ===")
    print(f"  Total HTML files:    {stats['total']}")
    print(f"  Parsed:              {stats['parsed']}")
    print(f"  Skipped (errors):    {stats['skipped']}")
    print(f"  High confidence:     {stats['high_confidence']} (pack label in HTML)")
    print(f"  Medium confidence:   {stats['medium_confidence']} (single-pack or shared)")
    print(f"    Pack-specific:     {stats['pack_specific']}")
    print(f"    Single-pack exp:   {stats['single_pack']}")
    print(f"    Shared pool:       {stats['shared_pool']}")
    print(f"  Low confidence:      {stats['low_confidence']}")
    print(f"\n  By set:")
    for set_code, count in sorted(stats["by_set"].items()):
        print(f"    {set_code}: {count}")
    print(f"\n  By pack (top entries):")
    for pack_key, count in sorted(stats["by_pack"].items(), key=lambda x: -x[1])[:20]:
        print(f"    {pack_key}: {count}")
    if stats["warnings"]:
        print(f"\n  Warnings ({len(stats['warnings'])}):")
        for w in stats["warnings"][:10]:
            print(f"    - {w}")


def main():
    parser = argparse.ArgumentParser(description="Build pack_sources.json from cached Limitless HTML")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without writing output")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "DRY RUN" if args.dry_run else "BUILD"
    print(f"\n=== build_pack_sources.py [{mode}] ===")
    print(f"Generated: {now}")

    print(f"\nLoading external reference...")
    ext_index = load_ext_ref()
    print(f"  Loaded {len(ext_index)} ext_ref entries")

    print(f"\nParsing HTML cache...")
    records, stats = build_records(ext_index, args.dry_run)

    print_stats(stats)

    if not args.dry_run:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        output = {
            "_meta": {
                "generated_at": now,
                "source": "Limitless TCG Pocket (cached HTML)",
                "total_records": len(records),
                "note": (
                    "Pack data extracted from Limitless TCG Pocket card pages. "
                    "confidence=high: pack label in HTML. "
                    "confidence=medium: single-pack expansion or shared pool. "
                    "pack_name=null: shared across all packs in expansion."
                ),
            },
            "records": records,
        }
        OUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWritten: {OUT_JSON} ({len(records)} records)")
    else:
        print(f"\nDRY RUN: would write {len(records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
