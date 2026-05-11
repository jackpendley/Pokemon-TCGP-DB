#!/usr/bin/env python3
"""
Applies confirmed pack assignments from the skipped multi-value review CSV to cards.json.

Reads:
    data/exports/skipped_multi_value_review.csv
    data/reference/pack_sources.json
    cards.json

Supported confirmed_action values:
    apply_single   — single version; requires confirmed_set_code + confirmed_card_number.
                     Updates existing card entry with source_packs, set_code, card_number,
                     source_pack_confidence=user_confirmed.
    split_record   — two owned versions; requires split_1_* and split_2_* fields.
                     Splits the existing card into two separate entries.
                     Split quantities must sum to existing card quantity UNLESS
                     --allow-quantity-increase is passed (for cases where both versions
                     were genuinely undercounted at 1+1 from a qty=1 base).
    leave_unresolved — skipped with an informational message.

Safety rules:
    - Default is --dry-run; never writes without --apply.
    - Never changes total collection quantity (without --allow-quantity-increase).
    - Never invents records.
    - Verifies set_code + card_number exists in pack_sources.json before applying.
    - Will not overwrite a prior user_confirmed assignment.
    - Does not rename cards; does not implement --allow-rename; that flag is reserved
      for a future explicit phase.

Usage:
    python3 scripts/apply_skipped_multi_value_confirmations.py --dry-run   (default)
    python3 scripts/apply_skipped_multi_value_confirmations.py --apply
    python3 scripts/apply_skipped_multi_value_confirmations.py --apply --allow-quantity-increase
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
REVIEW_CSV = ROOT / "data" / "exports" / "skipped_multi_value_review.csv"


def load_pack_sources():
    raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = raw["records"] if isinstance(raw, dict) else raw
    index = {}
    for r in records:
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            index[key] = r
    return index


def parse_int(s, label=""):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


def is_truthy(s):
    return str(s or "").strip().lower() in ("yes", "y", "true", "1")


def load_csv_rows():
    if not REVIEW_CSV.exists():
        print(f"ERROR: {REVIEW_CSV} not found. Run create_skipped_multi_value_review.py first.",
              file=sys.stderr)
        sys.exit(1)
    rows = []
    with REVIEW_CSV.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            action = row.get("confirmed_action", "").strip().lower()
            if not action or action == "leave_unresolved":
                if action == "leave_unresolved":
                    print(f"  INFO row {i} ({row.get('card_name','')}): confirmed_action=leave_unresolved — skipped")
                continue
            rows.append((i, row))
    return rows


def validate_apply_single(i, row, ps_index):
    """Returns (set_code, card_number, ps_record) or None on failure."""
    card_id = row.get("owned_card_id", "").strip()
    sc = row.get("confirmed_set_code", "").strip()
    cn = parse_int(row.get("confirmed_card_number", ""))
    name = row.get("card_name", "")

    if not sc:
        print(f"  WARN row {i} ({name}): apply_single but confirmed_set_code is blank — skipped")
        return None
    if cn is None:
        print(f"  WARN row {i} ({name}): apply_single but confirmed_card_number is not a valid integer — skipped")
        return None

    ps_rec = ps_index.get((sc, cn))
    if ps_rec is None:
        print(f"  ERROR row {i} ({name}): ({sc}, {cn}) not found in pack_sources.json — skipped")
        return None

    return sc, cn, ps_rec


def validate_split(i, row, ps_index, existing_qty, allow_qty_increase):
    """Returns (s1_sc, s1_cn, s1_qty, s1_ps, s2_sc, s2_cn, s2_qty, s2_ps) or None."""
    name = row.get("card_name", "")

    s1_sc = row.get("split_1_set_code", "").strip()
    s1_cn = parse_int(row.get("split_1_card_number", ""))
    s1_qty = parse_int(row.get("split_1_quantity", ""))

    s2_sc = row.get("split_2_set_code", "").strip()
    s2_cn = parse_int(row.get("split_2_card_number", ""))
    s2_qty = parse_int(row.get("split_2_quantity", ""))

    missing = []
    if not s1_sc: missing.append("split_1_set_code")
    if s1_cn is None: missing.append("split_1_card_number")
    if s1_qty is None: missing.append("split_1_quantity")
    if not s2_sc: missing.append("split_2_set_code")
    if s2_cn is None: missing.append("split_2_card_number")
    if s2_qty is None: missing.append("split_2_quantity")
    if missing:
        print(f"  WARN row {i} ({name}): split_record missing fields: {missing} — skipped")
        return None

    # Quantity check
    split_total = s1_qty + s2_qty
    if split_total != existing_qty:
        if not allow_qty_increase:
            print(
                f"  ERROR row {i} ({name}): split quantities ({s1_qty}+{s2_qty}={split_total}) "
                f"do not equal existing quantity ({existing_qty}). "
                f"Re-run with --allow-quantity-increase to override."
            )
            return None
        else:
            print(
                f"  WARN row {i} ({name}): split quantities ({s1_qty}+{s2_qty}={split_total}) "
                f"differ from existing quantity ({existing_qty}). "
                f"--allow-quantity-increase set; proceeding."
            )

    # Verify both keys in pack_sources
    ps1 = ps_index.get((s1_sc, s1_cn))
    if ps1 is None:
        print(f"  ERROR row {i} ({name}): split_1 ({s1_sc}, {s1_cn}) not in pack_sources — skipped")
        return None
    ps2 = ps_index.get((s2_sc, s2_cn))
    if ps2 is None:
        print(f"  ERROR row {i} ({name}): split_2 ({s2_sc}, {s2_cn}) not in pack_sources — skipped")
        return None

    return s1_sc, s1_cn, s1_qty, ps1, s2_sc, s2_cn, s2_qty, ps2


def make_pack_note(sc, cn):
    return f"Manually confirmed by user: {sc}/{cn}"


def normalize_id(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", "_", s).strip("_")


def next_free_id(cards, base_id):
    existing = {c["id"] for c in cards}
    # Try base_id first, then base_id_v2, _v3, ...
    if base_id not in existing:
        return base_id
    i = 2
    while True:
        candidate = f"{base_id}_split{i}"
        if candidate not in existing:
            return candidate
        i += 1


def apply_single(card, sc, cn, ps_rec, dry_run, mode_label):
    pack_name = ps_rec.get("pack_name")
    expansion = ps_rec.get("expansion", "")
    print(
        f"  {mode_label} {card['card_name']} (id={card['id']}): "
        f"set_code={sc}, card_number={cn}, pack_name={pack_name!r}, expansion={expansion!r}"
    )
    if not dry_run:
        card["source_packs"] = [pack_name] if pack_name else []
        card["source_expansion"] = expansion
        card["source_set_code"] = sc
        card["source_pack_confidence"] = "user_confirmed"
        card["source_pack_notes"] = make_pack_note(sc, cn)
        card["set_code"] = sc
        card["card_number"] = cn


def apply_split(cards, card_idx, card, s1_sc, s1_cn, s1_qty, ps1,
                s2_sc, s2_cn, s2_qty, ps2, dry_run, mode_label):
    p1 = ps1.get("pack_name")
    p2 = ps2.get("pack_name")
    e1 = ps1.get("expansion", "")
    e2 = ps2.get("expansion", "")

    print(
        f"  {mode_label} SPLIT {card['card_name']} (id={card['id']}) qty={card['quantity']}:\n"
        f"    → keep: {s1_sc}/{s1_cn} qty={s1_qty} pack={p1!r}\n"
        f"    → new:  {s2_sc}/{s2_cn} qty={s2_qty} pack={p2!r}"
    )
    if not dry_run:
        # Update existing entry to be the first split
        card["quantity"] = s1_qty
        card["source_packs"] = [p1] if p1 else []
        card["source_expansion"] = e1
        card["source_set_code"] = s1_sc
        card["source_pack_confidence"] = "user_confirmed"
        card["source_pack_notes"] = make_pack_note(s1_sc, s1_cn)
        card["set_code"] = s1_sc
        card["card_number"] = s1_cn

        # Build new entry for the second split
        new_id_base = normalize_id(card["id"])
        new_id = next_free_id(cards, new_id_base)
        new_card = dict(card)
        new_card["id"] = new_id
        new_card["quantity"] = s2_qty
        new_card["source_packs"] = [p2] if p2 else []
        new_card["source_expansion"] = e2
        new_card["source_set_code"] = s2_sc
        new_card["source_pack_confidence"] = "user_confirmed"
        new_card["source_pack_notes"] = make_pack_note(s2_sc, s2_cn)
        new_card["set_code"] = s2_sc
        new_card["card_number"] = s2_cn
        new_card["variant_notes"] = f"Split from {card['id']}"

        # Insert after the existing entry
        cards.insert(card_idx + 1, new_card)
        print(f"    New entry id: {new_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply skipped multi-value confirmations to cards.json"
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write changes. Default is dry-run (no writes).")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run_flag",
                        help="Preview without writing (default, explicit flag accepted).")
    parser.add_argument("--allow-quantity-increase", action="store_true",
                        help="Allow split quantities to exceed existing card quantity.")
    args = parser.parse_args()
    dry_run = not args.apply
    allow_qty_increase = args.allow_quantity_increase

    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"\n=== apply_skipped_multi_value_confirmations.py [{mode}] ===")

    for p in (PACK_SOURCES_JSON, CARDS_JSON):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(1)

    ps_index = load_pack_sources()
    print(f"  pack_sources: {len(ps_index)} records")

    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    cards_by_id = {c["id"]: (i, c) for i, c in enumerate(cards)}
    print(f"  cards.json: {len(cards)} entries")

    print("\nLoading confirmed rows...")
    confirmed_rows = load_csv_rows()
    print(f"  {len(confirmed_rows)} actionable row(s)")

    if not confirmed_rows:
        print("\nNothing to apply. Fill confirmed_action in the CSV and re-run.")
        sys.exit(0)

    applied_single = 0
    applied_split = 0
    skipped = 0
    errors = 0
    mode_label = "DRY-RUN" if dry_run else "APPLY"

    for i, row in confirmed_rows:
        action = row.get("confirmed_action", "").strip().lower()
        card_id = row.get("owned_card_id", "").strip()
        name = row.get("card_name", "")

        if card_id not in cards_by_id:
            print(f"  ERROR row {i} ({name}): card_id {card_id!r} not in cards.json — skipped")
            errors += 1
            continue

        card_idx, card = cards_by_id[card_id]

        if card.get("source_pack_confidence") == "user_confirmed":
            print(f"  SKIP row {i} ({name}): already user_confirmed — not overwriting")
            skipped += 1
            continue

        if action == "apply_single":
            result = validate_apply_single(i, row, ps_index)
            if result is None:
                errors += 1
                continue
            sc, cn, ps_rec = result
            apply_single(card, sc, cn, ps_rec, dry_run, mode_label)
            applied_single += 1

        elif action == "split_record":
            existing_qty = card.get("quantity", 0)
            result = validate_split(i, row, ps_index, existing_qty, allow_qty_increase)
            if result is None:
                errors += 1
                continue
            s1_sc, s1_cn, s1_qty, ps1, s2_sc, s2_cn, s2_qty, ps2 = result
            apply_split(cards, card_idx, card, s1_sc, s1_cn, s1_qty, ps1,
                        s2_sc, s2_cn, s2_qty, ps2, dry_run, mode_label)
            applied_split += 1

        else:
            print(f"  WARN row {i} ({name}): unknown confirmed_action {action!r} — skipped")
            skipped += 1

    total_applied = applied_single + applied_split
    print(f"\n=== Results ===")
    print(f"  apply_single:  {applied_single}")
    print(f"  split_record:  {applied_split}")
    print(f"  Skipped:       {skipped}")
    print(f"  Errors:        {errors}")

    if not dry_run and total_applied > 0:
        CARDS_JSON.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWritten: {CARDS_JSON} ({total_applied} change(s) applied)")
        print("Run: python3 scripts/validate_cards.py --expected-total 329")
    elif dry_run and total_applied > 0:
        print(f"\nDRY RUN: would apply {total_applied} change(s). Re-run with --apply to write.")
    else:
        print("\nNo changes to apply.")


if __name__ == "__main__":
    main()
