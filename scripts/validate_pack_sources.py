#!/usr/bin/env python3
"""
Validates data/reference/pack_sources.json against pack_sources.schema.json.

If pack_sources.json does not exist, reports clearly and exits 0 (not an error).
If it exists, validates structure and content.

Usage:
    python3 scripts/validate_pack_sources.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
PACK_SOURCES_SCHEMA = ROOT / "data" / "reference" / "pack_sources.schema.json"

VALID_SET_CODES = {"A4b", "B1", "B1a", "B2", "B2a", "B2b", "B3"}
VALID_RARITIES = {
    "one_diamond", "two_diamond", "three_diamond", "four_diamond",
    "one_star", "double_star", "triple_star", "crown", None,
}
VALID_CONFIDENCES = {"high", "medium", "low"}
REQUIRED_FIELDS = ["set_code", "card_number", "card_name", "pack_name", "expansion"]


def main():
    if not PACK_SOURCES_JSON.exists():
        print("INFO  pack_sources.json does not exist — this is expected and not an error.")
        print(f"      Expected path: {PACK_SOURCES_JSON}")
        print("      Build pack_sources.json using the plan in review/pack_source_mapping_plan.md")
        print("      Schema: data/reference/pack_sources.schema.json")
        sys.exit(0)

    print(f"Found: {PACK_SOURCES_JSON}")
    try:
        data = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL  pack_sources.json is not valid JSON: {exc}")
        sys.exit(1)

    if not isinstance(data, list):
        print("FAIL  pack_sources.json top-level must be an array")
        sys.exit(1)

    print(f"PASS  pack_sources.json loaded ({len(data)} entries)")

    failures = 0
    warnings = 0
    seen_keys = set()

    for i, entry in enumerate(data):
        card_key = f"{entry.get('set_code')}_{entry.get('card_number')}"

        # Required fields
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            print(f"FAIL  entry[{i}] missing required fields: {missing}")
            failures += 1
            continue

        # set_code
        sc = entry.get("set_code")
        if sc not in VALID_SET_CODES:
            print(f"WARN  entry[{i}] unknown set_code: {sc!r} (not in known set list)")
            warnings += 1

        # card_number
        cn = entry.get("card_number")
        if not isinstance(cn, int) or cn < 1:
            print(f"FAIL  entry[{i}] card_number must be a positive integer, got: {cn!r}")
            failures += 1

        # card_name
        name = entry.get("card_name", "")
        if not name or not name.strip():
            print(f"FAIL  entry[{i}] card_name is blank")
            failures += 1

        # rarity
        rarity = entry.get("rarity")
        if rarity is not None and rarity not in VALID_RARITIES:
            print(f"WARN  entry[{i}] unexpected rarity: {rarity!r}")
            warnings += 1

        # confidence
        conf = entry.get("confidence")
        if conf is not None and conf not in VALID_CONFIDENCES:
            print(f"WARN  entry[{i}] unexpected confidence: {conf!r}")
            warnings += 1

        # duplicate key
        if card_key in seen_keys:
            print(f"WARN  entry[{i}] duplicate set_code+card_number key: {card_key!r}")
            warnings += 1
        else:
            seen_keys.add(card_key)

    print()
    if failures == 0:
        print(f"ALL CHECKS PASSED  ({len(data)} entries, {warnings} warnings)")
        sys.exit(0)
    else:
        print(f"{failures} CHECK(S) FAILED  ({len(data)} entries, {warnings} warnings)")
        sys.exit(1)


if __name__ == "__main__":
    main()
