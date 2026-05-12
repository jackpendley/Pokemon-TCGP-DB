#!/usr/bin/env python3
"""
Structural reconciliation of collection.json against screenshot inventory.

Does NOT perform OCR. Compares:
    - collection entry count and total quantity
    - screenshot file count and expected card slot count

Outputs:
    review/current_collection_reconciliation.md
    data/current/current_collection_reconciliation.json

Usage:
    python3 scripts/reconcile_current_collection_sources.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"
INVENTORY_JSON = ROOT / "data" / "current" / "screenshot_inventory.json"
OUT_MD = ROOT / "review" / "current_collection_reconciliation.md"
OUT_JSON = ROOT / "data" / "current" / "current_collection_reconciliation.json"


def strip_comments(text):
    return re.sub(r"//[^\n]*", "", text)


def load_collection():
    if not COLLECTION_JSON.exists():
        print(f"ERROR: {COLLECTION_JSON} not found", file=sys.stderr)
        sys.exit(1)
    raw = COLLECTION_JSON.read_text(encoding="utf-8")
    data = json.loads(strip_comments(raw))
    meta = data.get("meta", {})
    collection = data.get("collection", [])
    total_quantity = sum(e.get("count", 0) for e in collection)
    unique_entries = len(collection)
    return meta, collection, total_quantity, unique_entries


def load_inventory():
    if not INVENTORY_JSON.exists():
        return None
    return json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))


def assess(meta, total_quantity, unique_entries, inventory):
    issues = []
    warnings = []
    notes = []

    meta_total = meta.get("total_cards", 0)

    # Collection checks
    if total_quantity == meta_total:
        notes.append(f"Collection total quantity ({total_quantity}) matches meta.total_cards ({meta_total}). ✅")
    else:
        issues.append(
            f"Collection quantity mismatch: actual={total_quantity}, meta={meta_total}. "
            f"Difference={abs(total_quantity - meta_total)}"
        )

    if total_quantity == 380:
        notes.append("Collection total is exactly 380. ✅")
    else:
        issues.append(f"Collection total is {total_quantity}, expected 380.")

    # Screenshot checks
    if inventory is None:
        warnings.append("screenshot_inventory.json not found — run inventory_screenshots.py first.")
        total_slots = None
        screenshot_count = None
    else:
        total_slots = inventory.get("total_card_slots", 0)
        screenshot_count = inventory.get("screenshot_count", 0)

        notes.append(f"Screenshots: {screenshot_count} files, {total_slots} expected card slots.")

        # Key structural note: total quantity != unique entries
        # Screenshots show unique card tiles (224 unique entries in collection)
        # total quantity (380) includes duplicates via count field
        notes.append(
            f"Structural note: collection has {unique_entries} unique entries (card tiles) "
            f"and {total_quantity} total quantity (sum of counts). "
            f"Screenshots represent unique card tiles, not 380 separate images."
        )

        # Check slots vs unique entries
        if total_slots >= unique_entries:
            notes.append(
                f"Screenshot slots ({total_slots}) >= unique collection entries ({unique_entries}). "
                f"Structurally consistent. ✅"
            )
        else:
            warnings.append(
                f"Screenshot slots ({total_slots}) < unique collection entries ({unique_entries}). "
                f"Not enough screenshot coverage for all unique entries."
            )

        # Reasonable range check
        expected_min = unique_entries
        expected_max = unique_entries + 15  # allow ~15 overlap/empty slots
        if total_slots < expected_min:
            warnings.append(f"Slot count {total_slots} is less than unique entry count {unique_entries}.")
        elif total_slots > expected_max:
            warnings.append(
                f"Slot count {total_slots} is more than unique_entries + 15 ({expected_max}). "
                f"Some slots may be blank or screenshots overlap."
            )

    return issues, warnings, notes, total_slots, screenshot_count


def write_md(meta, total_quantity, unique_entries, inventory,
             issues, warnings, notes, total_slots, screenshot_count, path):

    meta_total = meta.get("total_cards", "unknown")
    validated = (total_quantity == 380 and not issues)

    lines = [
        "# Current Collection Reconciliation",
        "",
        f"**Status:** {'✅ VALIDATED at 380' if validated else '⚠️ UNRESOLVED — see issues below'}",
        "",
        "## Collection Summary",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Source | `collection.json` |",
        f"| Meta total_cards | {meta_total} |",
        f"| Actual quantity sum | {total_quantity} |",
        f"| Unique entries | {unique_entries} |",
        f"| Validates at 380 | {'Yes ✅' if total_quantity == 380 else 'No ❌'} |",
        "",
    ]

    if inventory:
        lines += [
            "## Screenshot Summary",
            "",
            f"| Field | Value |",
            f"|---|---|",
            f"| Screenshot files | {screenshot_count} |",
            f"| Total card slots | {total_slots} |",
            f"| Slots vs unique entries | {total_slots} slots / {unique_entries} entries |",
            "",
        ]

    lines += ["## Structural Analysis", ""]
    for note in notes:
        lines.append(f"- {note}")

    if warnings:
        lines += ["", "## Warnings", ""]
        for w in warnings:
            lines.append(f"- ⚠️ {w}")

    if issues:
        lines += ["", "## Issues", ""]
        for issue in issues:
            lines.append(f"- ❌ {issue}")

    lines += [
        "",
        "## Interpretation",
        "",
        "The screenshots show the Pokémon TCG Pocket app's card collection grid.",
        "Each visible tile represents a **unique card entry** with a quantity chip showing how many copies are owned.",
        f"The collection has {unique_entries} unique entries summing to {total_quantity} total card copies.",
        f"The screenshots provide {total_slots if total_slots else '?'} expected tile slots across {screenshot_count if screenshot_count else '?'} files.",
        "",
        "To verify individual cards, a future phase can either:",
        "- Use OCR to read card names and quantities from screenshots",
        "- Or manually fill in the blank fields in `review/screenshot_manifest.md`",
        "",
        "Pack and deck recommendations can use `collection.json` as the source of truth,",
        "with screenshots as visual provenance.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print(f"\n=== reconcile_current_collection_sources.py ===")

    meta, collection, total_quantity, unique_entries = load_collection()
    print(f"  Collection: {unique_entries} unique entries, total quantity={total_quantity}")

    inventory = load_inventory()
    if inventory:
        print(f"  Inventory:  {inventory['screenshot_count']} screenshots, {inventory['total_card_slots']} slots")
    else:
        print(f"  Inventory:  not found — run inventory_screenshots.py first")

    issues, warnings, notes, total_slots, screenshot_count = assess(
        meta, total_quantity, unique_entries, inventory
    )

    result = {
        "collection_meta_total": meta.get("total_cards"),
        "collection_actual_total": total_quantity,
        "collection_unique_entries": unique_entries,
        "collection_validates_at_380": total_quantity == 380,
        "screenshot_count": screenshot_count,
        "total_card_slots": total_slots,
        "issues": issues,
        "warnings": warnings,
        "notes": notes,
    }

    (ROOT / "data" / "current").mkdir(parents=True, exist_ok=True)
    (ROOT / "review").mkdir(exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")

    write_md(meta, total_quantity, unique_entries, inventory,
             issues, warnings, notes, total_slots, screenshot_count, OUT_MD)
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    if issues:
        print(f"\n  ❌ {len(issues)} issue(s) found:")
        for iss in issues:
            print(f"    - {iss}")
    elif warnings:
        print(f"\n  ⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print(f"\n  ✅ No issues. Collection and screenshots structurally consistent.")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
