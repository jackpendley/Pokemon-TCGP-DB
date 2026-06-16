#!/usr/bin/env python3
"""
Propagate the cross-validated rarity from card_reference.json into the two
Limitless-derived reference files that downstream consumers read directly:

  - data/reference/pack_sources.json            (EV pool: build_pull_probability_model)
  - data/reference/external/external_card_reference.json  (sync/assign metadata)

card_reference.json is the authority (TCGdex per-card rarity incl. shiny/crown, plus
the curated SIR override). For every coord present there, the target record's rarity is
set to the authoritative value; coords absent from card_reference fall back to
normalize_rarity() on the existing value (legacy symbol-tier → new vocabulary).

Idempotent. Run after build_card_reference.py. The Limitless HTML cache that originally
produced these files is not retained, so this propagation replaces a full rebuild.

Usage:
    python3 scripts/migrate_reference_rarity.py
    python3 scripts/migrate_reference_rarity.py --dry-run
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (normalize_rarity, card_reference_by_coord,
                            load_records, parse_coord, ROOT, CARD_REF_JSON,
                            PACK_SOURCES_JSON as PACK_SOURCES,
                            EXT_REF_JSON as EXT_REF)


def _coord(rec, num_key):
    return parse_coord(rec.get("set_code"), rec.get(num_key))


def _apply(records, num_key, card_ref):
    """Set each record's rarity from card_ref (authority) or normalize the existing value."""
    changed = 0
    after = Counter()
    for r in records:
        old = r.get("rarity")
        coord = _coord(r, num_key)
        ref = card_ref.get(coord) if coord else None
        new = ref.get("rarity") if (ref and ref.get("rarity")) else normalize_rarity(old)
        if new != old:
            r["rarity"] = new
            changed += 1
        after[r.get("rarity")] += 1
    return changed, after


def main() -> int:
    ap = argparse.ArgumentParser(description="Propagate card_reference rarity into pack_sources / ext_ref.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    card_ref = card_reference_by_coord(CARD_REF_JSON)
    if not card_ref:
        print(f"ERROR: {CARD_REF_JSON} missing/empty — run build_card_reference.py first.", file=sys.stderr)
        return 1
    print(f"Loaded {len(card_ref)} card_reference coords (rarity authority).")

    # pack_sources.json (flat array or {'records': [...]})
    ps_records = load_records(PACK_SOURCES)
    ps_changed, ps_after = _apply(ps_records, "card_number", card_ref)
    print(f"pack_sources: {ps_changed} rarities updated. Distribution: {dict(ps_after.most_common())}")

    # external_card_reference.json (flat array; coord key is 'number')
    ext_records = load_records(EXT_REF)
    ext_changed, ext_after = _apply(ext_records, "number", card_ref)
    print(f"ext_ref: {ext_changed} rarities updated. Distribution: {dict(ext_after.most_common())}")

    if args.dry_run:
        print("--dry-run: no files written.")
        return 0

    PACK_SOURCES.write_text(json.dumps(ps_raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EXT_REF.write_text(json.dumps(ext_raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Wrote pack_sources.json and external_card_reference.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
