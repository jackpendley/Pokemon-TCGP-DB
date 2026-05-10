#!/usr/bin/env python3
"""
Generates a collection summary from cards.json.

Writes:
    review/collection_summary.md
    data/exports/collection_summary.json

Usage:
    python3 scripts/collection_summary.py
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
SUMMARY_MD = ROOT / "review" / "collection_summary.md"
SUMMARY_JSON = ROOT / "data" / "exports" / "collection_summary.json"

METADATA_WARNING = (
    "Metadata enrichment is incomplete. Fields such as card_category, pokemon_type, "
    "stage, hp, rarity, and set_or_pack are unknown for many entries. "
    "Enrichment from Limitless TCG Pocket reference data is planned for a future phase."
)


def main():
    if not CARDS_JSON.exists():
        print(f"ERROR cards.json not found at {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    try:
        cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR cards.json invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    total_entries = len(cards)
    total_quantity = sum(
        c.get("quantity", 0) for c in cards if isinstance(c.get("quantity"), int)
    )
    unique_names = len({
        c.get("card_name", "") for c in cards
        if c.get("card_name", "") not in ("", "unknown")
    })
    ex_count = sum(1 for c in cards if c.get("is_ex") is True)
    needs_review_count = sum(1 for c in cards if c.get("needs_review") is True)
    unknown_special_type = sum(1 for c in cards if c.get("special_type") == "unknown")

    top_dupes = sorted(
        [
            (c.get("card_name", "unknown"), c.get("quantity", 0))
            for c in cards if isinstance(c.get("quantity"), int) and c.get("quantity", 0) > 1
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    category_counts = Counter(c.get("card_category", "Unknown") for c in cards)
    type_counts = Counter(c.get("pokemon_type", "Unknown") for c in cards)
    screenshot_counts = Counter(c.get("source_screenshot", "unknown") for c in cards)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    summary = {
        "generated_at": now,
        "total_entries": total_entries,
        "total_quantity": total_quantity,
        "unique_card_names": unique_names,
        "total_ex_cards": ex_count,
        "total_needs_review": needs_review_count,
        "special_type_unknown_count": unknown_special_type,
        "top_duplicate_quantities": [
            {"card_name": n, "quantity": q} for n, q in top_dupes
        ],
        "counts_by_card_category": dict(category_counts.most_common()),
        "counts_by_pokemon_type": dict(type_counts.most_common()),
        "counts_by_source_screenshot": dict(sorted(screenshot_counts.items())),
        "metadata_warning": METADATA_WARNING,
    }

    md_lines = [
        "# Collection Summary",
        "",
        f"Generated: {now}",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total entries | {total_entries} |",
        f"| Total quantity | {total_quantity} |",
        f"| Unique card names | {unique_names} |",
        f"| ex cards | {ex_count} |",
        f"| Cards needing review | {needs_review_count} |",
        f"| special_type = unknown | {unknown_special_type} |",
        "",
        f"> **Note:** {METADATA_WARNING}",
        "",
        "## Top Cards by Quantity (> 1 copy)",
        "",
        "| Card Name | Quantity |",
        "|---|---|",
    ]
    for name, qty in top_dupes:
        md_lines.append(f"| {name} | {qty} |")

    md_lines += [
        "",
        "## Counts by Card Category",
        "",
        "| Category | Count |",
        "|---|---|",
    ]
    for cat, count in category_counts.most_common():
        md_lines.append(f"| {cat} | {count} |")

    md_lines += [
        "",
        "## Counts by Pokémon Type",
        "",
        "| Type | Count |",
        "|---|---|",
    ]
    for ptype, count in type_counts.most_common():
        md_lines.append(f"| {ptype} | {count} |")

    md_lines += [
        "",
        "## Entries by Source Screenshot",
        "",
        "| Screenshot | Entries |",
        "|---|---|",
    ]
    for ss, count in sorted(screenshot_counts.items()):
        md_lines.append(f"| {ss} | {count} |")

    md_text = "\n".join(md_lines) + "\n"

    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text(md_text, encoding="utf-8")

    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Written: {SUMMARY_MD}")
    print(f"Written: {SUMMARY_JSON}")
    print(f"Total entries: {total_entries}, total quantity: {total_quantity}")


if __name__ == "__main__":
    main()
