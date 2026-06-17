#!/usr/bin/env python3
"""
Validates data/reference/reprint_links.json (the A4b reprint -> original link map).

Checks:
  - every link's a4b coord exists in card_reference and is set A4b
  - every link's original coord exists in card_reference and is one of A1–A4
  - linked rarities are equal and are BASE rarities (not rare-plus)
  - linked names agree
  - no A4b coord maps to two different originals (1:1 from the A4b side)
  - DATA QUALITY: every A4b base card the user OWNS that has a same-rarity original is
    linked — an owned dual card must never be silently dropped (else its original-set slot
    would wrongly read unowned in EV)

If reprint_links.json does not exist, reports clearly and exits 0 (not an error).

Usage:
    python3 scripts/validate_reprint_links.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (norm_card_name, normalize_rarity, RARE_PLUS_RARITIES,
                            ROOT, CARD_REF_JSON,
                            REPRINT_LINKS_JSON as LINKS_JSON,
                            COLLECTION_NORMALIZED_JSON as COLLECTION_JSON,
                            A4B_SET_CODE, A4B_ORIGINAL_SETS)

ORIGINAL_SETS = frozenset(A4B_ORIGINAL_SETS)


def main():
    if not LINKS_JSON.exists():
        print("INFO  reprint_links.json does not exist — this is expected and not an error.")
        print(f"      Build it with: python3 scripts/build_reprint_links.py")
        sys.exit(0)

    print(f"Found: {LINKS_JSON}")
    links = json.loads(LINKS_JSON.read_text(encoding="utf-8")).get("links", [])
    print(f"PASS  loaded ({len(links)} links)")

    ref = json.loads(CARD_REF_JSON.read_text(encoding="utf-8"))["records"]
    by_coord = {(str(r.get("set_code", "")).upper(), r.get("card_number")): r for r in ref}

    failures = warnings = 0
    seen_a4b: dict[tuple[str, int], tuple] = {}

    for i, link in enumerate(links):
        a4b_sc, a4b_cn = link["a4b"]
        og_sc, og_cn = link["original"]
        a4b_key = (a4b_sc.upper(), a4b_cn)
        og_key = (og_sc.upper(), og_cn)

        a4b_rec = by_coord.get(a4b_key)
        og_rec = by_coord.get(og_key)

        if a4b_sc.upper() != A4B_SET_CODE:
            print(f"FAIL  link[{i}] a4b set is {a4b_sc!r}, expected A4b"); failures += 1
        if og_sc.upper() not in ORIGINAL_SETS:
            print(f"FAIL  link[{i}] original set {og_sc!r} not in {sorted(ORIGINAL_SETS)}"); failures += 1
        if a4b_rec is None:
            print(f"FAIL  link[{i}] a4b coord {a4b_key} not in card_reference"); failures += 1; continue
        if og_rec is None:
            print(f"FAIL  link[{i}] original coord {og_key} not in card_reference"); failures += 1; continue

        ar, orr = normalize_rarity(a4b_rec.get("rarity")), normalize_rarity(og_rec.get("rarity"))
        if ar != orr:
            print(f"FAIL  link[{i}] {link['name']!r} rarity mismatch: A4b={ar} vs orig={orr}"); failures += 1
        if ar in RARE_PLUS_RARITIES:
            print(f"FAIL  link[{i}] {link['name']!r} links a RARE-PLUS rarity ({ar}); "
                  f"full-arts must stay independent"); failures += 1
        if norm_card_name(a4b_rec.get("name", "")) != norm_card_name(og_rec.get("name", "")):
            print(f"FAIL  link[{i}] name mismatch: {a4b_rec.get('name')!r} vs {og_rec.get('name')!r}")
            failures += 1

        if a4b_key in seen_a4b and seen_a4b[a4b_key] != og_key:
            print(f"FAIL  A4b coord {a4b_key} mapped to two originals: "
                  f"{seen_a4b[a4b_key]} and {og_key}"); failures += 1
        seen_a4b[a4b_key] = og_key

    # ── Data-quality gate: every OWNED A4b dual card must be linked ───────────
    owned_unlinked = 0
    if COLLECTION_JSON.exists():
        orig_by_nr: dict[tuple, list] = {}
        for r in ref:
            if str(r.get("set_code", "")).upper() in ORIGINAL_SETS:
                orig_by_nr.setdefault(
                    (norm_card_name(r.get("name", "")), normalize_rarity(r.get("rarity"))), []
                ).append(r)
        col = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))["collection"]
        for e in col:
            if str(e.get("set_code") or "").upper() != A4B_SET_CODE or e.get("card_number") is None:
                continue
            rec = by_coord.get((A4B_SET_CODE, e["card_number"]))
            if not rec:
                continue
            rar = normalize_rarity(rec.get("rarity"))
            if rar in RARE_PLUS_RARITIES:
                continue  # rare-plus stays independent — fine
            has_original = bool(orig_by_nr.get((norm_card_name(rec.get("name", "")), rar)))
            if has_original and (A4B_SET_CODE, e["card_number"]) not in seen_a4b:
                print(f"FAIL  owned A4b dual card NOT linked: {rec.get('name')!r} A4b/{e['card_number']} "
                      f"({rar}) — its original-set slot would read unowned in EV")
                owned_unlinked += 1
                failures += 1
        print(f"PASS  owned-dual-card linkage check ({owned_unlinked} unlinked)")
    else:
        print("WARN  collection_normalized.json absent — skipped owned-linkage check"); warnings += 1

    print()
    if failures == 0:
        print(f"ALL CHECKS PASSED  ({len(links)} links, {warnings} warnings)")
        sys.exit(0)
    print(f"{failures} CHECK(S) FAILED  ({len(links)} links, {warnings} warnings)")
    sys.exit(1)


if __name__ == "__main__":
    main()
