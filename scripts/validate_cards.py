#!/usr/bin/env python3
"""
Validates cards.json against the schema and business rules defined in CLAUDE.md.

Hard checks (exit 1 on failure):
    - total quantity equals expected total
    - required fields exist
    - quantities are positive integers
    - IDs are unique
    - no missing/blank card_name
    - special_type values are valid
    - confidence values are valid
    - needs_review is boolean
    - needs_review=true cards have review_reason
    - low confidence cards have needs_review=true
    - ambiguous cards appear in ambiguous_cards.md

Warnings (printed but not blocking):
    - metadata_confidence values if present
    - is_ex is boolean if present
    - source_reference present when metadata_confidence is high
    - unknown metadata fields noted but not blocking

Usage:
    python3 scripts/validate_cards.py --expected-total 329
    python3 scripts/validate_cards.py --expected-total 331 || true   # informational only

Exit codes:
    0  All hard checks passed
    1  One or more hard checks failed
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
AMBIGUOUS_MD = ROOT / "ambiguous_cards.md"

VALID_SPECIAL_TYPES = {
    "normal", "full_art", "illustration_rare", "special_art",
    "immersive", "crown_gold", "shiny", "rainbow",
    "promo", "special_trainer", "alternate_art", "unknown",
}
VALID_CONFIDENCES = {"high", "medium", "low"}
VALID_METADATA_CONFIDENCES = {"high", "medium", "low", "unknown"}
REQUIRED_FIELDS = [
    "id", "card_name", "quantity", "card_category", "pokemon_type",
    "stage", "hp", "is_ex", "special_type", "rarity", "set_or_pack",
    "variant_notes", "source_screenshot", "source_row", "source_column",
    "confidence", "needs_review", "review_reason",
]


def load_cards():
    if not CARDS_JSON.exists():
        return None, f"FAIL cards.json not found at {CARDS_JSON}"
    try:
        data = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"FAIL cards.json is not valid JSON: {exc}"
    if not isinstance(data, list):
        return None, "FAIL top-level value of cards.json is not an array"
    return data, None


def load_ambiguous_text():
    if not AMBIGUOUS_MD.exists():
        return ""
    return AMBIGUOUS_MD.read_text(encoding="utf-8")


def check_required_fields(cards):
    errors = []
    for i, card in enumerate(cards):
        missing = [f for f in REQUIRED_FIELDS if f not in card]
        if missing:
            errors.append(f"  card[{i}] id={card.get('id', '?')} missing fields: {missing}")
    return errors


def check_unique_ids(cards):
    seen = {}
    dupes = []
    for i, card in enumerate(cards):
        cid = card.get("id")
        if cid in seen:
            dupes.append(f"  duplicate id '{cid}' at index {i} and {seen[cid]}")
        else:
            seen[cid] = i
    return dupes


def check_quantities(cards):
    errors = []
    for i, card in enumerate(cards):
        q = card.get("quantity")
        if not isinstance(q, int) or q < 0:
            errors.append(f"  card[{i}] id={card.get('id', '?')} invalid quantity: {q!r}")
    return errors


def check_special_types(cards):
    errors = []
    for i, card in enumerate(cards):
        st = card.get("special_type")
        if st not in VALID_SPECIAL_TYPES:
            errors.append(f"  card[{i}] id={card.get('id', '?')} invalid special_type: {st!r}")
    return errors


def check_confidences(cards):
    errors = []
    for i, card in enumerate(cards):
        conf = card.get("confidence")
        if conf not in VALID_CONFIDENCES:
            errors.append(f"  card[{i}] id={card.get('id', '?')} invalid confidence: {conf!r}")
    return errors


def check_needs_review_is_bool(cards):
    errors = []
    for i, card in enumerate(cards):
        nr = card.get("needs_review")
        if not isinstance(nr, bool):
            errors.append(f"  card[{i}] id={card.get('id', '?')} needs_review is not boolean: {nr!r}")
    return errors


def check_review_reasons(cards):
    errors = []
    for i, card in enumerate(cards):
        if card.get("needs_review") is True:
            reason = card.get("review_reason", "")
            if not reason or not reason.strip():
                errors.append(f"  card[{i}] id={card.get('id', '?')} needs_review=true but review_reason is empty")
    return errors


def check_low_confidence_flagged(cards):
    errors = []
    for i, card in enumerate(cards):
        if card.get("confidence") == "low" and card.get("needs_review") is not True:
            errors.append(f"  card[{i}] id={card.get('id', '?')} confidence=low but needs_review is not true")
    return errors


def check_card_names(cards):
    errors = []
    for i, card in enumerate(cards):
        name = card.get("card_name", None)
        if name == "" or (isinstance(name, str) and name.strip() == "" and name != "unknown"):
            errors.append(f"  card[{i}] id={card.get('id', '?')} card_name is blank (use 'unknown' if unreadable)")
    return errors


def check_ambiguous_logged(cards, ambiguous_text):
    errors = []
    for i, card in enumerate(cards):
        if card.get("needs_review") is True or card.get("confidence") == "low":
            cid = card.get("id", "")
            if cid and cid not in ambiguous_text:
                errors.append(
                    f"  card[{i}] id={cid!r} needs_review/low-confidence but not found in ambiguous_cards.md"
                )
    return errors


def warn_metadata_confidence(cards):
    """Non-blocking: warn if metadata_confidence has an unexpected value."""
    warnings = []
    for i, card in enumerate(cards):
        mc = card.get("metadata_confidence")
        if mc is not None and mc not in VALID_METADATA_CONFIDENCES:
            warnings.append(
                f"  card[{i}] id={card.get('id', '?')} unexpected metadata_confidence: {mc!r}"
            )
    return warnings


def warn_is_ex_type(cards):
    """Non-blocking: warn if is_ex is not boolean."""
    warnings = []
    for i, card in enumerate(cards):
        iex = card.get("is_ex")
        if iex is not None and not isinstance(iex, bool):
            warnings.append(
                f"  card[{i}] id={card.get('id', '?')} is_ex is not boolean: {iex!r}"
            )
    return warnings


def warn_high_confidence_missing_source(cards):
    """Non-blocking: warn if metadata_confidence=high but source_reference is absent."""
    warnings = []
    for i, card in enumerate(cards):
        if card.get("metadata_confidence") == "high":
            sr = card.get("source_reference")
            if not sr or str(sr).strip().lower() in ("", "unknown", "none"):
                warnings.append(
                    f"  card[{i}] id={card.get('id', '?')} metadata_confidence=high but source_reference missing"
                )
    return warnings


def warn_unknown_metadata(cards):
    """Non-blocking: count and summarize unknown metadata fields."""
    unknown_fields = {}
    metadata_fields = ["card_category", "pokemon_type", "stage", "rarity", "set_or_pack", "special_type"]
    for card in cards:
        for f in metadata_fields:
            v = card.get(f)
            if v is None or str(v).strip().lower() in ("unknown", "none", "null", ""):
                unknown_fields[f] = unknown_fields.get(f, 0) + 1
    return [f"  {f}: {cnt}/{len(cards)} entries still unknown" for f, cnt in sorted(unknown_fields.items())]


def check_total(cards, expected_total):
    total = sum(c.get("quantity", 0) for c in cards if isinstance(c.get("quantity"), int))
    return total, total == expected_total


def run_check(label, errors):
    if errors:
        print(f"FAIL  {label}")
        for e in errors:
            print(e)
        return False
    print(f"PASS  {label}")
    return True


def run_warning(label, warnings):
    if warnings:
        print(f"WARN  {label} ({len(warnings)} items)")
        for w in warnings:
            print(w)
    else:
        print(f"OK    {label}")


def main():
    parser = argparse.ArgumentParser(description="Validate cards.json")
    parser.add_argument("--expected-total", type=int, required=True,
                        help="Expected sum of all card quantities")
    args = parser.parse_args()

    failures = 0

    cards, load_error = load_cards()
    if load_error:
        print(load_error)
        sys.exit(1)

    print(f"PASS  cards.json loaded ({len(cards)} entries)")

    ambiguous_text = load_ambiguous_text()

    checks = [
        ("required fields present",          check_required_fields(cards)),
        ("all IDs are unique",               check_unique_ids(cards)),
        ("quantity is non-negative integer", check_quantities(cards)),
        ("special_type values valid",        check_special_types(cards)),
        ("confidence values valid",          check_confidences(cards)),
        ("needs_review is boolean",          check_needs_review_is_bool(cards)),
        ("needs_review=true has reason",     check_review_reasons(cards)),
        ("low confidence => needs_review",   check_low_confidence_flagged(cards)),
        ("no blank card_name",               check_card_names(cards)),
        ("ambiguous cards logged in .md",    check_ambiguous_logged(cards, ambiguous_text)),
    ]

    for label, errors in checks:
        if not run_check(label, errors):
            failures += 1

    total, total_ok = check_total(cards, args.expected_total)
    label = f"total quantity {total} == expected {args.expected_total}"
    if total_ok:
        print(f"PASS  {label}")
    else:
        print(f"FAIL  {label}")
        failures += 1

    # Non-blocking metadata warnings
    print()
    print("--- Metadata warnings (informational, not blocking) ---")
    run_warning("metadata_confidence values", warn_metadata_confidence(cards))
    run_warning("is_ex is boolean",           warn_is_ex_type(cards))
    run_warning("high-confidence source ref", warn_high_confidence_missing_source(cards))
    run_warning("unknown metadata fields",    warn_unknown_metadata(cards))

    print()
    if failures == 0:
        print(f"ALL CHECKS PASSED  ({len(cards)} cards, total={total})")
        sys.exit(0)
    else:
        print(f"{failures} CHECK(S) FAILED  ({len(cards)} cards, total={total})")
        sys.exit(1)


if __name__ == "__main__":
    main()
