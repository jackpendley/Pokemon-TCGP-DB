#!/usr/bin/env python3
"""
Exports cards.json to cards.csv.

Usage:
    python scripts/export_cards_csv.py

Do not manually edit cards.csv — regenerate it by running this script.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
CARDS_CSV = ROOT / "cards.csv"

FIELD_ORDER = [
    "id",
    "card_name",
    "quantity",
    "card_category",
    "pokemon_type",
    "stage",
    "hp",
    "is_ex",
    "special_type",
    "rarity",
    "set_or_pack",
    "variant_notes",
    "source_screenshot",
    "source_row",
    "source_column",
    "confidence",
    "needs_review",
    "review_reason",
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
    with CARDS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_ORDER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cards)
    return len(cards)


def main():
    cards = load_cards()
    count = export(cards)
    print(f"Exported {count} rows to cards.csv")


if __name__ == "__main__":
    main()
