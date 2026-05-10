#!/usr/bin/env python3
"""
Exports cards.json to data/exports/cards_collection.csv.

Usage:
    python3 scripts/export_cards_csv.py

Do not manually edit the output CSV — regenerate it by running this script.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
EXPORT_CSV = ROOT / "data" / "exports" / "cards_collection.csv"

FIELD_ORDER = [
    "id",
    "card_name",
    "quantity",
    "special_type",
    "is_ex",
    "card_category",
    "pokemon_type",
    "stage",
    "hp",
    "rarity",
    "set_or_pack",
    "source_screenshot",
    "source_row",
    "source_column",
    "needs_review",
    "review_reason",
    "variant_notes",
]


def load_cards():
    if not CARDS_JSON.exists():
        print(f"ERROR cards.json not found at {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR cards.json is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)


def export(cards):
    EXPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_ORDER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cards)
    return len(cards)


def main():
    cards = load_cards()
    count = export(cards)
    print(f"Exported {count} rows to {EXPORT_CSV}")


if __name__ == "__main__":
    main()
