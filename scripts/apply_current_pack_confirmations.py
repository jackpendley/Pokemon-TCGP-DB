#!/usr/bin/env python3
"""
Apply user-filled pack-source confirmations from current_pack_source_review.csv.

Writes confirmed mappings to:
    data/current/current_collection_pack_confirmations.json

Does NOT mutate collection.json.
Does NOT change card counts or names.

Safety:
    - Default is --dry-run; never writes without --apply.
    - Verifies (set_code, card_number) exists in pack_sources.json before applying.
    - Only processes rows where confirmed_yes_no is yes/y/true/1.
    - Requires both confirmed_set_code and confirmed_card_number.
    - Will not overwrite an existing confirmed mapping unless --force is passed.

Usage:
    python3 scripts/apply_current_pack_confirmations.py --dry-run   (default)
    python3 scripts/apply_current_pack_confirmations.py --apply
    python3 scripts/apply_current_pack_confirmations.py --apply --force
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW_CSV = ROOT / "data" / "exports" / "current_pack_source_review.csv"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
CONFIRMATIONS_JSON = ROOT / "data" / "current" / "current_collection_pack_confirmations.json"


def load_pack_sources():
    raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = raw["records"] if isinstance(raw, dict) else raw
    index = {}
    for r in records:
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            index[key] = r
    return index


def is_confirmed(row: dict) -> bool:
    return str(row.get("confirmed_yes_no", "")).strip().lower() in ("yes", "y", "true", "1")


def parse_int(s) -> int | None:
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


def load_csv_rows() -> list[tuple[int, dict]]:
    if not REVIEW_CSV.exists():
        print(f"  NOTE: {REVIEW_CSV.relative_to(ROOT)} does not exist — nothing to apply.")
        return []
    rows = []
    with REVIEW_CSV.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if is_confirmed(row):
                rows.append((i, row))
    return rows


def load_existing_confirmations() -> dict:
    if CONFIRMATIONS_JSON.exists():
        return json.loads(CONFIRMATIONS_JSON.read_text(encoding="utf-8"))
    return {"generated_at": None, "note": "Do not edit manually.", "confirmations": {}}


def main():
    parser = argparse.ArgumentParser(
        description="Apply current pack-source confirmations (dry-run by default)"
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write confirmations. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run_flag",
                        help="Preview without writing (default, explicit flag accepted).")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing confirmations.")
    args = parser.parse_args()
    dry_run = not args.apply

    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"\n=== apply_current_pack_confirmations.py [{mode}] ===")

    if not PACK_SOURCES_JSON.exists():
        print(f"ERROR: {PACK_SOURCES_JSON} not found", file=sys.stderr)
        sys.exit(1)

    ps_index = load_pack_sources()
    print(f"  pack_sources: {len(ps_index)} records")

    confirmed_rows = load_csv_rows()
    if not confirmed_rows:
        print(f"\n  No confirmed rows found.")
        print(f"  Fill confirmed_yes_no=yes in data/exports/current_pack_source_review.csv and re-run.")
        sys.exit(0)

    print(f"  Confirmed rows: {len(confirmed_rows)}")

    existing = load_existing_confirmations()
    existing_conf = existing.get("confirmations", {})

    applied = 0
    skipped = 0
    errors = 0
    mode_label = "DRY-RUN" if dry_run else "APPLY"

    new_confirmations = dict(existing_conf)

    for i, row in confirmed_rows:
        entry_id = row.get("entry_id", "").strip()
        name = row.get("name", "").strip()
        sc = row.get("confirmed_set_code", "").strip()
        cn = parse_int(row.get("confirmed_card_number", ""))
        override_pack = row.get("confirmed_pack_name", "").strip() or None

        label = f"{name} (id={entry_id or '?'})"

        if not sc:
            print(f"  WARN row {i} ({name}): confirmed_yes_no=yes but confirmed_set_code is blank — skipped")
            errors += 1
            continue
        if cn is None:
            print(f"  WARN row {i} ({name}): confirmed_yes_no=yes but confirmed_card_number is not a valid integer — skipped")
            errors += 1
            continue

        ps_key = (sc, cn)
        ps_rec = ps_index.get(ps_key)
        if ps_rec is None:
            print(f"  ERROR row {i} ({name}): ({sc}, {cn}) not found in pack_sources.json — skipped")
            errors += 1
            continue

        if entry_id in new_confirmations and not args.force:
            print(f"  SKIP row {i} ({name}): entry_id {entry_id!r} already confirmed — use --force to overwrite")
            skipped += 1
            continue

        pack_name = override_pack or ps_rec.get("pack_name")
        expansion = ps_rec.get("expansion", "")

        print(
            f"  {mode_label} {label}: set_code={sc}, card_number={cn}, "
            f"pack_name={pack_name!r}, expansion={expansion!r}"
        )

        if not dry_run:
            new_confirmations[entry_id] = {
                "entry_id": entry_id,
                "name": name,
                "confirmed_set_code": sc,
                "confirmed_card_number": cn,
                "pack_name": pack_name,
                "expansion": expansion,
                "source_url": ps_rec.get("source_url", ""),
                "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

        applied += 1

    print(f"\n=== Results ===")
    print(f"  Applied:  {applied}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")

    if not dry_run and applied > 0:
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Generated by apply_current_pack_confirmations.py. Do not edit manually.",
            "confirmations": new_confirmations,
        }
        CONFIRMATIONS_JSON.parent.mkdir(parents=True, exist_ok=True)
        CONFIRMATIONS_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWritten: {CONFIRMATIONS_JSON.relative_to(ROOT)} ({applied} confirmation(s))")
    elif dry_run and applied > 0:
        print(f"\nDRY RUN: would write {applied} confirmation(s). Re-run with --apply to persist.")
    else:
        print("\nNo changes to apply.")


if __name__ == "__main__":
    main()
