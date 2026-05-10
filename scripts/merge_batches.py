#!/usr/bin/env python3
"""
Merges all confirmed batch files into cards.json.

Reads:  batches/cards_batch_[0-9][0-9][0-9].json  (excludes TEMPLATE and DRAFT files)
Writes: cards.json
        merge_report.md

Usage:
    python3 scripts/merge_batches.py [--dry-run] [--force]

Flags:
    --dry-run   Print summary without writing files.
    --force     Overwrite cards.json even if it already contains data.
"""

import argparse
import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCHES_GLOB = str(ROOT / "batches" / "cards_batch_[0-9][0-9][0-9].json")
CARDS_JSON = ROOT / "cards.json"
MERGE_REPORT = ROOT / "merge_report.md"

REQUIRED_FIELDS = [
    "id", "card_name", "quantity", "card_category", "pokemon_type",
    "stage", "hp", "is_ex", "special_type", "rarity", "set_or_pack",
    "variant_notes", "source_screenshot", "source_row", "source_column",
    "confidence", "needs_review", "review_reason",
]


def _norm(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def id_base(entry: dict) -> str:
    """Return the base ID (without _vN) for an entry."""
    existing = entry.get("id", "")
    m = re.match(r"^(.+)_v\d+$", existing)
    if m:
        return m.group(1)
    return (
        f"{_norm(entry.get('card_name', 'unknown'))}"
        f"_{_norm(entry.get('special_type', 'unknown'))}"
        f"_{_norm(entry.get('set_or_pack', 'unknown'))}"
    )


def assign_unique_ids(entries: list) -> list:
    """
    Assign a unique _vN ID to every entry.
    Process entries in order; the first occurrence of each base gets _v1,
    the second gets _v2, etc.  No entries are merged or removed.
    """
    seen: dict[str, int] = {}
    result = []
    for entry in entries:
        base = id_base(entry)
        seen[base] = seen.get(base, 0) + 1
        new_entry = dict(entry)
        new_entry["id"] = f"{base}_v{seen[base]}"
        result.append(new_entry)
    return result


def validate_batch(filename: str, entries: list) -> list:
    errors = []
    for i, entry in enumerate(entries):
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            errors.append(f"  {filename}[{i}] missing fields: {missing}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Merge confirmed batch files into cards.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview summary without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite cards.json even if it already contains data")
    args = parser.parse_args()

    # Safety: refuse to overwrite non-empty cards.json unless --force
    if CARDS_JSON.exists() and not args.force:
        try:
            existing = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
            if isinstance(existing, list) and len(existing) > 0:
                print("ERROR  cards.json already contains data. Pass --force to overwrite.")
                sys.exit(1)
        except json.JSONDecodeError:
            pass  # Empty or corrupt — safe to overwrite

    batch_files = sorted(glob.glob(BATCHES_GLOB))
    if not batch_files:
        print(f"ERROR  No batch files found matching: {BATCHES_GLOB}")
        sys.exit(1)

    print(f"Found {len(batch_files)} batch file(s).")

    all_entries: list = []
    batch_summary: list = []
    validation_errors: list = []

    for bf in batch_files:
        bf_path = Path(bf)
        try:
            data = json.loads(bf_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR  {bf_path.name} is not valid JSON: {exc}")
            sys.exit(1)

        if not isinstance(data, list):
            print(f"ERROR  {bf_path.name} top-level value is not an array")
            sys.exit(1)

        errs = validate_batch(bf_path.name, data)
        validation_errors.extend(errs)

        batch_qty = sum(
            e.get("quantity", 0) for e in data
            if isinstance(e.get("quantity"), int)
        )
        batch_summary.append({
            "file": bf_path.name,
            "entries": len(data),
            "quantity": batch_qty,
        })
        all_entries.extend(data)

    if validation_errors:
        print("ERROR  Batch validation failed:")
        for e in validation_errors:
            print(e)
        sys.exit(1)

    merged = assign_unique_ids(all_entries)

    total_entries = len(merged)
    total_quantity = sum(
        e.get("quantity", 0) for e in merged
        if isinstance(e.get("quantity"), int)
    )

    print(f"Total entries:  {total_entries}")
    print(f"Total quantity: {total_quantity}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_lines = [
        "# Merge Report",
        "",
        f"Generated: {now}",
        "",
        "## Batch Summary",
        "",
        "| Batch File | Entries | Quantity |",
        "|---|---|---|",
    ]
    for b in batch_summary:
        report_lines.append(f"| {b['file']} | {b['entries']} | {b['quantity']} |")
    report_lines += [
        "",
        f"**Total entries: {total_entries}**",
        "",
        f"**Total quantity: {total_quantity}**",
        "",
        "## Merge Notes",
        "",
        "- All entries preserved; no cross-batch deduplication performed.",
        "- IDs reassigned sequentially to ensure uniqueness across the merged set.",
        "- Batch 024 contains only 4 entries (IMG_1547 overlap rows excluded).",
        "- Provisional baseline: 329 cards. Original expected total: 331. Discrepancy: −2.",
        "- See review/final_ingestion_reconciliation.md for discrepancy analysis.",
        "- See review/provisional_baseline.md for baseline rationale.",
    ]
    report_text = "\n".join(report_lines) + "\n"

    if args.dry_run:
        print("\n-- DRY RUN -- No files written.")
        print(report_text)
        return

    CARDS_JSON.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Written: {CARDS_JSON}")

    MERGE_REPORT.write_text(report_text, encoding="utf-8")
    print(f"Written: {MERGE_REPORT}")


if __name__ == "__main__":
    main()
