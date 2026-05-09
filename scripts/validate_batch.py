#!/usr/bin/env python3
"""
Validates a single batch file before it is merged into cards.json.

Usage:
    python3 scripts/validate_batch.py batches/cards_batch_001.json

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

import argparse
import json
import sys
from pathlib import Path

VALID_SPECIAL_TYPES = {
    "normal", "full_art", "illustration_rare", "special_art",
    "immersive", "crown_gold", "shiny", "rainbow",
    "promo", "special_trainer", "alternate_art", "unknown",
}
VALID_CONFIDENCES = {"high", "medium", "low"}
REQUIRED_FIELDS = [
    "id", "card_name", "quantity", "card_category", "pokemon_type",
    "stage", "hp", "is_ex", "special_type", "rarity", "set_or_pack",
    "variant_notes", "source_screenshot", "source_row", "source_column",
    "confidence", "needs_review", "review_reason",
]


def load_batch(path: Path) -> tuple[list | None, str | None]:
    if not path.exists():
        return None, f"FAIL file not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"FAIL not valid JSON: {exc}"
    if not isinstance(data, list):
        return None, "FAIL top-level value is not an array"
    return data, None


def check_required_fields(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        missing = [f for f in REQUIRED_FIELDS if f not in card]
        if missing:
            errors.append(f"  entry[{i}] id={card.get('id', '?')} missing fields: {missing}")
    return errors


def check_quantities(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        q = card.get("quantity")
        if not isinstance(q, int) or q < 0:
            errors.append(f"  entry[{i}] id={card.get('id', '?')} invalid quantity: {q!r}")
    return errors


def check_special_types(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        st = card.get("special_type")
        if st not in VALID_SPECIAL_TYPES:
            errors.append(f"  entry[{i}] id={card.get('id', '?')} invalid special_type: {st!r}")
    return errors


def check_confidences(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        conf = card.get("confidence")
        if conf not in VALID_CONFIDENCES:
            errors.append(f"  entry[{i}] id={card.get('id', '?')} invalid confidence: {conf!r}")
    return errors


def check_needs_review_is_bool(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        nr = card.get("needs_review")
        if not isinstance(nr, bool):
            errors.append(f"  entry[{i}] id={card.get('id', '?')} needs_review is not boolean: {nr!r}")
    return errors


def check_review_reasons(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        if card.get("needs_review") is True:
            reason = card.get("review_reason", "")
            if not reason or not reason.strip():
                errors.append(
                    f"  entry[{i}] id={card.get('id', '?')} needs_review=true but review_reason is empty"
                )
    return errors


def check_low_confidence_flagged(cards: list) -> list[str]:
    errors = []
    for i, card in enumerate(cards):
        if card.get("confidence") == "low" and card.get("needs_review") is not True:
            errors.append(
                f"  entry[{i}] id={card.get('id', '?')} confidence=low but needs_review is not true"
            )
    return errors


def run_check(label: str, errors: list[str]) -> bool:
    if errors:
        print(f"FAIL  {label}")
        for e in errors:
            print(e)
        return False
    print(f"PASS  {label}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate a single batch JSON file")
    parser.add_argument("batch_file", type=Path, help="Path to the batch file to validate")
    args = parser.parse_args()

    cards, load_error = load_batch(args.batch_file)
    if load_error:
        print(load_error)
        sys.exit(1)

    print(f"PASS  loaded {args.batch_file} ({len(cards)} entries)")

    failures = 0
    checks = [
        ("required fields present",         check_required_fields(cards)),
        ("quantity is non-negative integer", check_quantities(cards)),
        ("special_type values valid",        check_special_types(cards)),
        ("confidence values valid",          check_confidences(cards)),
        ("needs_review is boolean",          check_needs_review_is_bool(cards)),
        ("needs_review=true has reason",     check_review_reasons(cards)),
        ("low confidence => needs_review",   check_low_confidence_flagged(cards)),
    ]

    for label, errors in checks:
        if not run_check(label, errors):
            failures += 1

    total = sum(
        c.get("quantity", 0) for c in cards if isinstance(c.get("quantity"), int)
    )
    print(f"\nEntries : {len(cards)}")
    print(f"Total quantity : {total}")

    print()
    if failures == 0:
        print(f"ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print(f"{failures} CHECK(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
