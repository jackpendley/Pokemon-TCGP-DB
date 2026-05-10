#!/usr/bin/env python3
"""
Convert a manually confirmed card CSV into a batch JSON file.

Usage:
    python3 scripts/create_batch_from_confirmation.py \
        --input  review/confirmed/IMG_1525_confirmed.csv \
        --screenshot IMG_1525.PNG \
        --output batches/cards_batch_002.json \
        [--allow-fewer]

The input CSV must have columns:
    screenshot, row, column, card_name, quantity, special_type, is_ex, notes

Rows with special_type=unknown or notes containing 'uncertain' or 'review'
are automatically flagged needs_review=true.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

VALID_SPECIAL_TYPES = {
    "normal", "full_art", "illustration_rare", "special_art", "immersive",
    "crown_gold", "shiny", "rainbow", "promo", "special_trainer",
    "alternate_art", "unknown",
}

VALID_ROWS = {"1", "2", "3"}
VALID_COLS = {"1", "2", "3"}

REVIEW_NOTES_KEYWORDS = {"uncertain", "review", "unclear", "unknown", "verify"}


def normalize_for_id(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def make_id(card_name: str, special_type: str, existing_ids: set) -> str:
    base = f"{normalize_for_id(card_name)}_{normalize_for_id(special_type)}_unknown"
    candidate = f"{base}_v1"
    version = 1
    while candidate in existing_ids:
        version += 1
        candidate = f"{base}_v{version}"
    return candidate


def parse_bool(value: str, field: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "yes", "1"):
        return True
    if v in ("false", "no", "0", ""):
        return False
    print(f"ERROR: '{field}' must be true or false, got: '{value}'")
    sys.exit(1)


def parse_quantity(value: str) -> int:
    v = value.strip()
    if not v:
        print("ERROR: 'quantity' is required and must be a non-negative integer.")
        sys.exit(1)
    try:
        q = int(v)
    except ValueError:
        print(f"ERROR: 'quantity' must be an integer, got: '{v}'")
        sys.exit(1)
    if q < 0:
        print(f"ERROR: 'quantity' must be non-negative, got: {q}")
        sys.exit(1)
    return q


def main():
    parser = argparse.ArgumentParser(
        description="Convert a confirmed card CSV into a batch JSON file."
    )
    parser.add_argument("--input", required=True, help="Path to confirmed CSV")
    parser.add_argument("--screenshot", required=True, help="Screenshot filename, e.g. IMG_1525.PNG")
    parser.add_argument("--output", required=True, help="Output batch JSON path")
    parser.add_argument(
        "--allow-fewer", action="store_true",
        help="Allow fewer than 9 rows (for final screenshot with partial grid)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        sys.exit(1)

    if output_path.exists():
        print(f"ERROR: output file already exists: {output_path}")
        print("Delete it first or choose a different --output path.")
        sys.exit(1)

    # Read CSV
    with input_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {"screenshot", "row", "column", "card_name", "quantity",
                         "special_type", "is_ex", "notes"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            missing = required_cols - set(reader.fieldnames or [])
            print(f"ERROR: CSV missing required columns: {missing}")
            sys.exit(1)
        rows = list(reader)

    # Row count check
    if len(rows) == 0:
        print("ERROR: CSV has no data rows.")
        sys.exit(1)
    if len(rows) != 9 and not args.allow_fewer:
        print(f"ERROR: expected exactly 9 rows, got {len(rows)}.")
        print("Use --allow-fewer if this screenshot has fewer than 9 fully visible cards.")
        sys.exit(1)
    if len(rows) > 9:
        print(f"ERROR: CSV has {len(rows)} rows — max is 9 (one 3×3 grid).")
        sys.exit(1)

    entries = []
    existing_ids: set = set()
    errors = []

    for i, row in enumerate(rows, start=1):
        row_num = row.get("row", "").strip()
        col_num = row.get("column", "").strip()
        card_name = row.get("card_name", "").strip()
        qty_raw = row.get("quantity", "").strip()
        special_type_raw = row.get("special_type", "").strip()
        is_ex_raw = row.get("is_ex", "").strip()
        notes = row.get("notes", "").strip()
        screenshot = row.get("screenshot", "").strip()

        # Validate row/column
        if row_num not in VALID_ROWS:
            errors.append(f"Row {i}: 'row' must be 1, 2, or 3 — got '{row_num}'")
        if col_num not in VALID_COLS:
            errors.append(f"Row {i}: 'column' must be 1, 2, or 3 — got '{col_num}'")

        # card_name required
        if not card_name:
            errors.append(f"Row {i} (r{row_num}c{col_num}): 'card_name' is required. Use 'unknown' if not identifiable.")

        if errors:
            continue

        quantity = parse_quantity(qty_raw)

        special_type = special_type_raw if special_type_raw else "unknown"
        if special_type not in VALID_SPECIAL_TYPES:
            errors.append(
                f"Row {i} (r{row_num}c{col_num}): invalid special_type '{special_type}'. "
                f"Valid: {sorted(VALID_SPECIAL_TYPES)}"
            )
            continue

        is_ex = parse_bool(is_ex_raw, f"row {i} is_ex")

        # needs_review logic
        notes_lower = notes.lower()
        notes_flag = any(kw in notes_lower for kw in REVIEW_NOTES_KEYWORDS)
        needs_review = special_type == "unknown" or notes_flag

        review_parts = []
        if special_type == "unknown":
            review_parts.append("special_type not confirmed; visual review needed")
        if notes_flag:
            review_parts.append(f"notes indicate uncertainty: {notes}")
        review_reason = "; ".join(review_parts) if review_parts else ""

        confidence = "medium"

        card_id = make_id(card_name, special_type, existing_ids)
        existing_ids.add(card_id)

        entry = {
            "id": card_id,
            "card_name": card_name,
            "quantity": quantity,
            "card_category": "Unknown",
            "pokemon_type": "Unknown",
            "stage": "Unknown",
            "hp": None,
            "is_ex": is_ex,
            "special_type": special_type,
            "rarity": "unknown",
            "set_or_pack": "unknown",
            "variant_notes": notes,
            "source_screenshot": args.screenshot,
            "source_row": int(row_num),
            "source_column": int(col_num),
            "confidence": confidence,
            "needs_review": needs_review,
            "review_reason": review_reason,
        }
        entries.append(entry)

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total_qty = sum(e["quantity"] for e in entries)
    needs_review_count = sum(1 for e in entries if e["needs_review"])
    print(f"Written: {output_path}")
    print(f"Entries : {len(entries)}")
    print(f"Total quantity : {total_qty}")
    print(f"Needs review   : {needs_review_count}")


if __name__ == "__main__":
    main()
