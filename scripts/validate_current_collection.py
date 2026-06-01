#!/usr/bin/env python3
"""
Validate collection.json as the current active collection baseline.

Supports JSONC-style // line comments.

Usage:
    python3 scripts/validate_current_collection.py
    python3 scripts/validate_current_collection.py --expected-total 380
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import strip_comments, is_ex_from_name, TRAINER_SUBTYPE_MAP

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"

VALID_CARD_TYPES = {"Pokemon", "Trainer"}
VALID_POKEMON_TYPES = {
    "Fire", "Grass", "Water", "Lightning", "Psychic",
    "Fighting", "Darkness", "Metal", "Dragon", "Colorless",
}
# Valid trainer_subtype values, derived from the shared category map (single source).
VALID_TRAINER_SUBTYPES = set(TRAINER_SUBTYPE_MAP.values())


def load_collection():
    if not COLLECTION_JSON.exists():
        print(f"ERROR: {COLLECTION_JSON} not found", file=sys.stderr)
        sys.exit(1)
    raw = COLLECTION_JSON.read_text(encoding="utf-8")
    cleaned = strip_comments(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"ERROR: collection.json is not valid JSON (after stripping comments): {e}", file=sys.stderr)
        sys.exit(1)


def validate(data, expected_total):
    failures = []
    warnings = []

    # --- Meta validation ---
    meta = data.get("meta")
    if not isinstance(meta, dict):
        failures.append("meta field is missing or not an object")
        meta = {}

    meta_total = meta.get("total_cards")
    if meta_total is None:
        failures.append("meta.total_cards is missing")
    elif not isinstance(meta_total, int):
        failures.append(f"meta.total_cards is not an integer: {meta_total!r}")

    last_updated = meta.get("last_updated")
    if not last_updated:
        warnings.append("meta.last_updated is missing")

    fmt = meta.get("format")
    if not fmt:
        warnings.append("meta.format is missing")

    # --- Collection array ---
    collection = data.get("collection")
    if not isinstance(collection, list):
        failures.append("collection field is missing or not an array")
        return failures, warnings, {}, 0

    if len(collection) == 0:
        failures.append("collection array is empty")
        return failures, warnings, {}, 0

    # --- Per-entry validation ---
    type_counts = Counter()
    pokemon_type_counts = Counter()
    ex_entry_count = 0
    ex_card_count = 0
    name_totals = Counter()
    total_quantity = 0
    missing_optional = Counter()

    for i, entry in enumerate(collection, start=1):
        name = entry.get("name", "")
        if not name or not name.strip():
            failures.append(f"Entry {i}: name is missing or empty")

        count = entry.get("count")
        if count is None:
            failures.append(f"Entry {i} ({name!r}): count is missing")
        elif not isinstance(count, int) or count < 1:
            failures.append(f"Entry {i} ({name!r}): count must be a positive integer, got {count!r}")
        else:
            total_quantity += count
            name_totals[name] += count

        card_type = entry.get("card_type")
        if not card_type:
            failures.append(f"Entry {i} ({name!r}): card_type is missing")
        elif card_type not in VALID_CARD_TYPES:
            warnings.append(f"Entry {i} ({name!r}): unknown card_type {card_type!r}")
        else:
            type_counts[card_type] += (count or 0)

        if card_type == "Pokemon":
            ptype = entry.get("type")
            if not ptype:
                warnings.append(f"Entry {i} ({name!r}): Pokemon entry missing type")
            elif ptype not in VALID_POKEMON_TYPES:
                warnings.append(f"Entry {i} ({name!r}): unknown type {ptype!r}")
            else:
                pokemon_type_counts[ptype] += (count or 0)

            stage = entry.get("stage")
            if stage is None:
                missing_optional["stage"] += 1

            # Detect EX cards by the canonical " ex" name suffix (the is_ex field
            # is no longer stored on collection entries). Shared helper keeps this
            # consistent with normalize/report.
            is_ex = is_ex_from_name(name)
            if is_ex:
                ex_entry_count += 1
                ex_card_count += (count or 0)

        if card_type == "Trainer":
            subtype = entry.get("trainer_subtype")
            if not subtype:
                warnings.append(f"Entry {i} ({name!r}): Trainer entry missing trainer_subtype")
            elif subtype not in VALID_TRAINER_SUBTYPES:
                warnings.append(f"Entry {i} ({name!r}): unknown trainer_subtype {subtype!r}")

    # --- Quantity total check ---
    meta_declared = meta.get("total_cards", 0)
    if total_quantity != meta_declared:
        failures.append(
            f"QUANTITY MISMATCH: sum of all count values = {total_quantity}, "
            f"but meta.total_cards = {meta_declared}. "
            f"Difference of {abs(total_quantity - meta_declared)} cards unaccounted for."
        )
    if expected_total != meta_declared and total_quantity != expected_total:
        failures.append(
            f"TOTAL MISMATCH: actual quantity sum {total_quantity} != expected {expected_total}"
        )

    # --- Duplicate name report ---
    duplicates = {name: total for name, total in name_totals.items()
                  if sum(1 for e in collection if e.get("name") == name) > 1}

    stats = {
        "unique_entries": len(collection),
        "total_quantity": total_quantity,
        "meta_total": meta_declared,
        "expected_total": expected_total,
        "by_card_type": dict(type_counts),
        "by_pokemon_type": dict(pokemon_type_counts),
        "ex_entries": ex_entry_count,
        "ex_cards": ex_card_count,
        "duplicate_names": duplicates,
        "missing_optional": dict(missing_optional),
    }

    return failures, warnings, stats, total_quantity


def print_stats(stats):
    print(f"\n--- Collection Statistics ---")
    print(f"  Unique entries:      {stats['unique_entries']}")
    print(f"  Total quantity:      {stats['total_quantity']}")
    print(f"  Meta total_cards:    {stats['meta_total']}")
    print(f"  Expected total:      {stats['expected_total']}")

    print(f"\n  By card_type:")
    for k, v in sorted(stats["by_card_type"].items()):
        print(f"    {k}: {v}")

    print(f"\n  By Pokemon type (card count):")
    for k, v in sorted(stats["by_pokemon_type"].items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")

    print(f"\n  Ex Pokémon: {stats['ex_entries']} entries, {stats['ex_cards']} cards")

    if stats["duplicate_names"]:
        print(f"\n  Entries with same name (variants):")
        for name, total in sorted(stats["duplicate_names"].items(), key=lambda x: -x[1]):
            print(f"    {name}: {total} total")

    if stats["missing_optional"]:
        print(f"\n  Missing optional fields:")
        for k, v in stats["missing_optional"].items():
            print(f"    {k}: {v} entries missing")


def main():
    parser = argparse.ArgumentParser(
        description="Validate collection.json as the current active collection baseline"
    )
    parser.add_argument(
        "--expected-total", type=int, default=None,
        help="Expected total card count (default: meta.total_cards from collection.json)"
    )
    args = parser.parse_args()

    print(f"\n=== validate_current_collection.py ===")
    print(f"  File: {COLLECTION_JSON}")

    data = load_collection()

    meta_total = data.get("meta", {}).get("total_cards", 0)
    expected_total = args.expected_total if args.expected_total is not None else meta_total

    print(f"  Expected total: {expected_total}")

    failures, warnings, stats, total_quantity = validate(data, expected_total)

    print_stats(stats)

    if warnings:
        print(f"\n--- Warnings ({len(warnings)}) ---")
        for w in warnings:
            print(f"  WARN: {w}")

    if failures:
        print(f"\n--- FAILURES ({len(failures)}) ---")
        for f in failures:
            print(f"  FAIL: {f}")
        print(f"\nVALIDATION FAILED ({len(failures)} failure(s))")
        sys.exit(1)
    else:
        print(f"\nVALIDATION PASSED  ({stats['unique_entries']} entries, total={total_quantity})")


if __name__ == "__main__":
    main()
