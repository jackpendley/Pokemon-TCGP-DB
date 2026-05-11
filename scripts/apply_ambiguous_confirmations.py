#!/usr/bin/env python3
"""
Applies confirmed pack assignments from a filled-in ambiguous review CSV to cards.json.

SCAFFOLD — defaults to --dry-run. Pass --apply to write changes.

Reads:
    data/exports/ambiguous_cards_review.csv     (ambiguous cards, filled by user)
    data/exports/no_match_cards_review.csv      (no-match cards, filled by user)
    data/reference/pack_sources.json            (verifies confirmed set_code + card_number)
    cards.json                                  (updated in place when --apply is used)

Processes only rows where confirmed_yes_no is 'yes', 'y', or 'true' (case-insensitive).
Requires both confirmed_set_code AND confirmed_card_number (as integer) to be present.
Verifies the confirmed set_code + card_number exists in pack_sources.json before applying.
Sets source_pack_confidence to 'user_confirmed' on applied cards.

Usage:
    python3 scripts/apply_ambiguous_confirmations.py --dry-run   # preview only (default)
    python3 scripts/apply_ambiguous_confirmations.py --apply     # write to cards.json

Safety:
    --dry-run is the default. Never writes to cards.json without --apply.
    Does not modify quantity, card_name, or any non-pack field.
    Will not overwrite an existing source_packs if it was previously user_confirmed.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
AMBIG_CSV = ROOT / "data" / "exports" / "ambiguous_cards_review.csv"
NOMATCH_CSV = ROOT / "data" / "exports" / "no_match_cards_review.csv"


def load_pack_sources():
    raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = raw["records"] if isinstance(raw, dict) else raw
    index = {}
    for r in records:
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            index[key] = r
    return index


def is_confirmed(row):
    val = row.get("confirmed_yes_no", "").strip().lower()
    return val in ("yes", "y", "true", "1")


def parse_card_number(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def load_confirmed_rows(csv_path, source_label):
    """
    Reads a filled review CSV and returns rows that are confirmed.
    Skips rows missing required fields and prints warnings.
    """
    if not csv_path.exists():
        print(f"  SKIP {source_label}: file not found ({csv_path})")
        return []

    confirmed = []
    skipped = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not is_confirmed(row):
                continue

            card_id = row.get("card_id", "").strip()
            set_code = row.get("confirmed_set_code", "").strip()
            card_number = parse_card_number(row.get("confirmed_card_number", "").strip())

            if not card_id:
                print(f"  WARN row {i}: missing card_id — skipped")
                skipped += 1
                continue
            if not set_code:
                print(f"  WARN row {i} ({row.get('card_name','')}): confirmed_yes_no=yes but confirmed_set_code is blank — skipped")
                skipped += 1
                continue
            if card_number is None:
                print(f"  WARN row {i} ({row.get('card_name','')}): confirmed_yes_no=yes but confirmed_card_number is not a valid integer — skipped")
                skipped += 1
                continue

            # For no-match CSV, pack_name may be provided directly
            pack_name = row.get("confirmed_pack_name", "").strip() or None

            confirmed.append({
                "source": source_label,
                "csv_row": i,
                "card_id": card_id,
                "card_name": row.get("card_name", ""),
                "confirmed_set_code": set_code,
                "confirmed_card_number": card_number,
                "confirmed_pack_name_override": pack_name,
            })

    return confirmed


def apply_confirmations(confirmed_rows, ps_index, cards, dry_run):
    """
    For each confirmed row:
        1. Verify set_code + card_number exists in pack_sources.
        2. Find the corresponding card in cards.json by card_id.
        3. Set source_packs, source_expansion, source_set_code, source_pack_confidence.
    Returns counts of applied, skipped, and errored rows.
    """
    # Build cards index by id
    cards_by_id = {c["id"]: (i, c) for i, c in enumerate(cards)}

    applied = 0
    skipped = 0
    errors = 0

    for row in confirmed_rows:
        cid = row["card_id"]
        sc = row["confirmed_set_code"]
        cn = row["confirmed_card_number"]
        ps_key = (sc, cn)
        label = f"{row['card_name']} (id={cid})"

        # Verify in pack_sources
        ps_rec = ps_index.get(ps_key)
        if ps_rec is None:
            print(f"  ERROR {label}: confirmed ({sc}, {cn}) not found in pack_sources.json — skipped")
            errors += 1
            continue

        # Find card
        if cid not in cards_by_id:
            print(f"  ERROR {label}: card_id not found in cards.json — skipped")
            errors += 1
            continue

        idx, card = cards_by_id[cid]

        # Safety: don't overwrite a prior user_confirmed
        if card.get("source_pack_confidence") == "user_confirmed":
            print(f"  SKIP {label}: already user_confirmed — not overwriting")
            skipped += 1
            continue

        # Determine pack_name
        pack_name = row.get("confirmed_pack_name_override") or ps_rec.get("pack_name")
        expansion = ps_rec.get("expansion", "")

        action = "APPLY" if not dry_run else "DRY-RUN"
        print(
            f"  {action} {label}: set_code={sc}, card_number={cn}, "
            f"pack_name={pack_name!r}, expansion={expansion!r}"
        )

        if not dry_run:
            cards[idx]["source_packs"] = [pack_name] if pack_name else []
            cards[idx]["source_expansion"] = expansion
            cards[idx]["source_set_code"] = sc
            cards[idx]["source_pack_confidence"] = "user_confirmed"
            cards[idx]["source_pack_notes"] = (
                f"Manually confirmed by user: {sc}/{cn}"
            )

        applied += 1

    return applied, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description="Apply confirmed pack assignments from review CSVs to cards.json"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to cards.json. Default behavior is dry-run (no writes).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run_flag",
        help="Preview changes without writing (default behavior, explicit flag accepted).",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"\n=== apply_ambiguous_confirmations.py [{mode}] ===")

    if not PACK_SOURCES_JSON.exists():
        print(f"ERROR: pack_sources.json not found at {PACK_SOURCES_JSON}", file=sys.stderr)
        sys.exit(1)
    if not CARDS_JSON.exists():
        print(f"ERROR: cards.json not found at {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)

    print("\nLoading pack_sources index...")
    ps_index = load_pack_sources()
    print(f"  {len(ps_index)} records indexed")

    print("\nLoading cards.json...")
    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    print(f"  {len(cards)} cards loaded")

    print("\nLoading confirmed rows from CSVs...")
    confirmed = []
    confirmed += load_confirmed_rows(AMBIG_CSV, "ambiguous")
    confirmed += load_confirmed_rows(NOMATCH_CSV, "no_match")
    print(f"  {len(confirmed)} confirmed row(s) to process")

    if not confirmed:
        print("\nNothing to apply. Fill in the confirmed_* columns in the CSV files and re-run.")
        sys.exit(0)

    print(f"\nApplying ({mode})...")
    applied, skipped, errors = apply_confirmations(confirmed, ps_index, cards, dry_run)

    print(f"\n=== Results ===")
    print(f"  Processed: {len(confirmed)}")
    print(f"  Applied:   {applied}")
    print(f"  Skipped:   {skipped}")
    print(f"  Errors:    {errors}")

    if not dry_run and applied > 0:
        CARDS_JSON.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWritten: {CARDS_JSON} ({applied} card(s) updated)")
        print("Run: python3 scripts/validate_cards.py --expected-total 331")
    elif dry_run and applied > 0:
        print(f"\nDRY RUN: would apply {applied} update(s). Re-run with --apply to write.")
    else:
        print("\nNo changes to apply.")


if __name__ == "__main__":
    main()
