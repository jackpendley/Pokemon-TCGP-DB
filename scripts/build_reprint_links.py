#!/usr/bin/env python3
"""
Builds data/reference/reprint_links.json — the canonical map linking A4b "Deluxe Pack:
ex" reprints to their original-set printing.

WHY: A4b is largely a reprint set — a base-rarity A4b card is the SAME card as its first
(original) printing in A1–A4, and the app credits ownership across both dex slots. The EV
pipeline counts each (set, number) printing independently, so without this map a card you
own (stored at its A4b coord) makes its original-set slot read "unowned" and inflates that
pack's EV. build_pack_ev.py consumes this map to credit ownership across linked coords.

Matching rule ("same base printing only", per project decision):
    For each A4b record whose rarity is a BASE rarity (not in RARE_PLUS_RARITIES), find the
    A1–A4 record(s) with the same normalized name AND the same rarity. Full-art / secret /
    crown printings (rare-plus) on either side are NOT linked — they stay independent.
      - exactly one original          -> link, confidence "unique"
      - two or more originals          -> link to the DEBUT printing (earliest set, then
                                          lowest number), confidence "debut" (alternatives
                                          recorded for transparency)
      - no same-rarity original        -> skip (A4b-exclusive card; not a reprint)
    A curated override (reprint_links_overrides.json) pins specific pairs and wins over the
    heuristic (confidence "override").

Output envelope: {"_meta": {...}, "links": [{a4b, original, name, rarity, confidence, ...}]}

Usage:
    python3 scripts/build_reprint_links.py            # write reprint_links.json
    python3 scripts/build_reprint_links.py --dry-run  # print stats only, no write
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (norm_card_name, normalize_rarity, RARE_PLUS_RARITIES,
                            ROOT, REFERENCE_DIR, CARD_REF_JSON,
                            REPRINT_LINKS_JSON as OUTPUT_JSON,
                            A4B_SET_CODE, A4B_ORIGINAL_SETS)

OVERRIDES_JSON = REFERENCE_DIR / "reprint_links_overrides.json"

REPRINT_SET = A4B_SET_CODE                 # the Deluxe Pack: ex reprint set (upper-cased)
ORIGINAL_SETS = list(A4B_ORIGINAL_SETS)    # in debut order (earliest first)
_ORIG_ORDER = {s: i for i, s in enumerate(ORIGINAL_SETS)}


def _coord(rec) -> tuple[str, int]:
    return (str(rec["set_code"]), int(rec["card_number"]))


def _load_overrides() -> dict[tuple[str, int], dict]:
    """Return {(A4B, num): {original:(set,num), name}} from the curated file (upper-keyed)."""
    out: dict[tuple[str, int], dict] = {}
    if not OVERRIDES_JSON.exists():
        return out
    data = json.loads(OVERRIDES_JSON.read_text(encoding="utf-8"))
    for link in data.get("links", []):
        a4b_sc, a4b_cn = link["a4b"]
        og_sc, og_cn = link["original"]
        out[(a4b_sc.upper(), int(a4b_cn))] = {
            "original": (og_sc, int(og_cn)),
            "name": link.get("name", ""),
        }
    return out


def build_links():
    ref = json.loads(CARD_REF_JSON.read_text(encoding="utf-8"))["records"]
    by_coord = {(str(r.get("set_code", "")).upper(), r.get("card_number")): r for r in ref}

    # Index original-set base printings by (norm name, rarity).
    orig_by_nr: dict[tuple[str, str | None], list[dict]] = {}
    for r in ref:
        if str(r.get("set_code", "")).upper() in _ORIG_ORDER:
            key = (norm_card_name(r.get("name", "")), normalize_rarity(r.get("rarity")))
            orig_by_nr.setdefault(key, []).append(r)

    overrides = _load_overrides()
    a4b_recs = [r for r in ref if str(r.get("set_code", "")).upper() == REPRINT_SET]

    links: list[dict] = []
    counts = {"override": 0, "unique": 0, "debut": 0, "skip_no_original": 0, "skip_rare_plus": 0}

    for r in sorted(a4b_recs, key=lambda x: x.get("card_number", 0)):
        rar = normalize_rarity(r.get("rarity"))
        a4b_coord = (REPRINT_SET, r.get("card_number"))

        ovr = overrides.get(a4b_coord)
        if ovr:
            og = by_coord.get((ovr["original"][0].upper(), ovr["original"][1]))
            if og is None:
                print(f"  WARN: override original {ovr['original']} for A4b/{r['card_number']} "
                      f"not in card_reference — skipping", file=sys.stderr)
            else:
                links.append(_mk(r, og, "override"))
                counts["override"] += 1
                continue

        if rar in RARE_PLUS_RARITIES:
            counts["skip_rare_plus"] += 1
            continue

        cands = orig_by_nr.get((norm_card_name(r.get("name", "")), rar), [])
        if not cands:
            counts["skip_no_original"] += 1
            continue
        if len(cands) == 1:
            links.append(_mk(r, cands[0], "unique"))
            counts["unique"] += 1
        else:
            # Debut printing: earliest original set, then lowest card_number.
            debut = min(cands, key=lambda c: (_ORIG_ORDER[str(c["set_code"]).upper()],
                                              c["card_number"]))
            alts = [list(_coord(c)) for c in cands if c is not debut]
            links.append(_mk(r, debut, "debut", alternatives=alts))
            counts["debut"] += 1

    return links, counts


def _mk(a4b_rec, orig_rec, confidence, alternatives=None) -> dict:
    link = {
        "a4b": list(_coord(a4b_rec)),
        "original": list(_coord(orig_rec)),
        "name": a4b_rec.get("name", ""),
        "rarity": normalize_rarity(a4b_rec.get("rarity")),
        "confidence": confidence,
    }
    if alternatives:
        link["alternatives"] = alternatives
    return link


def main():
    ap = argparse.ArgumentParser(description="Build the A4b reprint-link reference.")
    ap.add_argument("--dry-run", action="store_true", help="print stats only, no file write")
    args = ap.parse_args()

    links, counts = build_links()

    print(f"Reprint links: {len(links)}")
    for k in ("override", "unique", "debut"):
        print(f"  {k}: {counts[k]}")
    print(f"  skipped (no same-rarity original): {counts['skip_no_original']}")
    print(f"  skipped (rare-plus, independent):  {counts['skip_rare_plus']}")

    if args.dry_run:
        print("DRY RUN — no file written.")
        return 0

    envelope = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "1.0",
            "description": "A4b Deluxe Pack: ex reprint -> original printing links "
                           "(same base rarity). Consumed by build_pack_ev.py for "
                           "reprint-aware ownership crediting.",
            "counts": counts,
            "total_links": len(links),
        },
        "links": links,
    }
    OUTPUT_JSON.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"\nWritten → {OUTPUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
