#!/usr/bin/env python3
"""
Simulate opening N packs and produce a full PZ-format JSON for --json-import testing.

The output JSON mirrors what the PZ bookmarklet produces: a complete snapshot of all
owned cards with counts, plus the newly pulled cards merged in.  Feed it directly to:
  python3 scripts/sync_collection.py --json-import <output_file>

Usage:
  # Fixed pack, 5 opens, reproducible seed
  python3 scripts/simulate_pack_opens.py --pack triumphant-light --count 5 --seed 42 --output /tmp/sim.json

  # Random pack selection
  python3 scripts/simulate_pack_opens.py --random --seed 42 --count 5 --output /tmp/sim.json
  python3 scripts/simulate_pack_opens.py --random --count 5 --output /tmp/sim.json

  # Preview pulls without writing output
  python3 scripts/simulate_pack_opens.py --pack pulsing-aura --count 5 --dry-run

Stdout: the selected pack slug (useful for the test runner to capture).
Stderr: selection info, pull summary, output path.
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT            = Path(__file__).resolve().parent.parent
PZ_PACK_ODDS    = ROOT / "data" / "reference" / "pz_pack_odds.json"
PACK_SOURCES    = ROOT / "data" / "reference" / "pack_sources.json"
COLLECTION_FILE = ROOT / "collection.json"  # canonical source; strip JSONC comments before parsing


def _normalize(name: str) -> str:
    # Matches _norm_name in build_pack_ev.py: normalize apostrophe variants, keep hyphens
    # and other punctuation so names like Farfetch'd, Ho-Oh, Sirfetch'd compare correctly.
    return name.lower().replace("’", "'").replace("‘", "'").strip()


def _load_collection() -> dict:
    """Load collection.json, stripping JSONC // comments before parsing."""
    raw = COLLECTION_FILE.read_text(encoding="utf-8")
    # Only strip lines whose first non-whitespace chars are '//'; avoids corrupting
    # any string value containing '//' (e.g. a future URL field).
    clean = re.sub(r"(?m)^\s*//[^\n]*\n?", "", raw)
    return json.loads(clean)


def _load_pz_data() -> dict:
    return json.loads(PZ_PACK_ODDS.read_text(encoding="utf-8"))


def select_pack(pack_slug: str | None, seed: int | None, pz_data: dict) -> tuple[str, dict]:
    """Return (slug, pack_info). Random selection excludes promo packs."""
    non_promo_slugs = sorted(
        slug for slug, info in pz_data.items()
        if not info.get("expansion_id", "").upper().startswith("PROMO")
    )
    if pack_slug:
        if pack_slug not in pz_data:
            print(f"ERROR: pack slug '{pack_slug}' not found in pz_pack_odds.json", file=sys.stderr)
            print(f"  Available non-promo slugs: {', '.join(non_promo_slugs)}", file=sys.stderr)
            sys.exit(1)
        return pack_slug, pz_data[pack_slug]
    rng = random.Random(seed)
    slug = rng.choice(non_promo_slugs)
    return slug, pz_data[slug]


def simulate_opens(pack_info: dict, count: int, seed: int | None) -> dict[tuple[str, int], int]:
    """
    Simulate 'count' pack opens using per-card per-slot probabilities from pz_pack_odds.json.
    Returns {(set_code, card_number): total_pull_count}.
    """
    cards = pack_info.get("cards", [])
    if not cards:
        print("ERROR: pack has no cards defined", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    pulled: dict[tuple[str, int], int] = {}

    for _ in range(count):
        for slot in range(1, 6):
            slot_key = str(slot)
            eligible = [
                (c, c["slot_odds_pct"].get(slot_key, 0.0))
                for c in cards
                if c["slot_odds_pct"].get(slot_key, 0.0) > 0
            ]
            if not eligible:
                continue
            population = [c for c, _ in eligible]
            weights    = [w for _, w in eligible]
            chosen = rng.choices(population, weights=weights, k=1)[0]
            key = (chosen["set_code"], chosen["card_number"])
            pulled[key] = pulled.get(key, 0) + 1

    return pulled


def _build_name_to_coord(ps_records: list[dict]) -> dict[str, tuple[str, int]]:
    """Build {normalized_card_name: (set_code, card_number)} from pack_sources records."""
    lookup: dict[str, tuple[str, int]] = {}
    for r in ps_records:
        nn     = _normalize(r.get("card_name", ""))
        sc     = str(r.get("set_code", "")).upper().strip()
        cn_raw = r.get("card_number")
        if not nn or not sc or cn_raw is None:
            continue
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            continue
        if nn not in lookup:
            lookup[nn] = (sc, cn)
    return lookup


def build_pz_snapshot(
    pulled: dict[tuple[str, int], int],
    pack_info: dict,
    collection_data: dict,
    ps_records: list[dict],
) -> list[dict]:
    """
    Build a complete PZ-format snapshot:
    - All currently owned cards from collection_normalized.json (preserves existing counts)
    - Pulled cards merged in: existing cards get incremented; new cards get appended

    Must include ALL owned cards — not just pulled ones — because --json-import treats
    absent entries as "missing from PZ" and will stale them out after a threshold.
    """
    entries = collection_data.get("collection", [])
    name_to_coord = _build_name_to_coord(ps_records)

    # (set_code, card_number) → name for cards in the simulated pack
    pack_card_names: dict[tuple[str, int], str] = {
        (c["set_code"], c["card_number"]): c["name"]
        for c in pack_info.get("cards", [])
    }

    output: list[dict] = []
    covered: set[tuple[str, int]] = set()

    for entry in entries:
        name  = entry.get("name", "")
        count = entry.get("count", 0)
        nn    = _normalize(name)
        coord = name_to_coord.get(nn)

        extra = 0
        if coord and coord in pulled and coord not in covered:
            extra = pulled[coord]
            covered.add(coord)

        rec: dict = {"cardName": name, "ownedCount": count + extra}
        if coord:
            rec["setCode"]     = coord[0]
            rec["cardNumber"]  = coord[1]
        output.append(rec)

    # Append brand-new pulled cards not present in the collection at all
    for coord, pull_count in pulled.items():
        if coord in covered:
            continue
        card_name = pack_card_names.get(coord, f"Unknown-{coord[0]}-{coord[1]}")
        output.append({
            "cardName":   card_name,
            "setCode":    coord[0],
            "cardNumber": coord[1],
            "ownedCount": pull_count,
        })

    return output


def print_pull_summary(
    pulled: dict[tuple[str, int], int],
    pack_info: dict,
    collection_data: dict,
    ps_records: list[dict],
) -> None:
    pack_card_map: dict[tuple[str, int], dict] = {
        (c["set_code"], c["card_number"]): c
        for c in pack_info.get("cards", [])
    }

    coord_rarity: dict[tuple[str, int], str] = {}
    for r in ps_records:
        sc = str(r.get("set_code", "")).upper()
        try:
            cn = int(r.get("card_number", 0))
        except (TypeError, ValueError):
            continue
        coord_rarity[(sc, cn)] = r.get("rarity", "?")

    owned_set = {
        _normalize(e.get("name", ""))
        for e in collection_data.get("collection", [])
    }

    print("\nPull summary:", file=sys.stderr)
    new_count = 0
    for coord, count in sorted(pulled.items(), key=lambda x: -x[1]):
        card = pack_card_map.get(coord, {})
        name    = card.get("name", f"{coord[0]}#{coord[1]}")
        rarity  = coord_rarity.get(coord, "?")
        is_new  = _normalize(name) not in owned_set
        new_tag = " [NEW]" if is_new else ""
        print(f"  {name} x{count}  ({rarity}){new_tag}", file=sys.stderr)
        if is_new:
            new_count += 1
    print(f"\nTotal pulls: {sum(pulled.values())}  |  Unique cards: {len(pulled)}  |  New to collection: {new_count}",
          file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate pack opens and generate a PZ-format JSON for --json-import testing."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack",   help="Pack slug from pz_pack_odds.json")
    group.add_argument("--random", action="store_true", dest="use_random",
                       help="Randomly select a non-promo pack")
    parser.add_argument("--count",   type=int, default=5, help="Number of packs to open (default: 5)")
    parser.add_argument("--seed",    type=int,            help="Random seed for reproducibility")
    parser.add_argument("--output",  "-o",                help="Output JSON file path (required unless --dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Print pull summary without writing output")
    args = parser.parse_args()

    pz_data = _load_pz_data()
    slug, pack_info = select_pack(args.pack, args.seed, pz_data)

    print(f"Selected pack : {pack_info['pack_name']} ({pack_info['expansion_id']}, {pack_info['card_count']} cards)",
          file=sys.stderr)
    print(f"Simulating    : {args.count} pack(s) with seed={args.seed}", file=sys.stderr)

    pulled = simulate_opens(pack_info, args.count, args.seed)

    collection_data = _load_collection()
    ps_data    = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
    ps_records = ps_data.get("records", ps_data) if isinstance(ps_data, dict) else ps_data

    print_pull_summary(pulled, pack_info, collection_data, ps_records)

    # Always emit the slug to stdout for the test runner
    print(slug)

    if args.dry_run:
        print("\nDry run — no output file written.", file=sys.stderr)
        return

    if not args.output:
        print("ERROR: --output PATH required unless --dry-run", file=sys.stderr)
        sys.exit(1)

    records = build_pz_snapshot(pulled, pack_info, collection_data, ps_records)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nOutput: {out_path}  ({len(records)} records)", file=sys.stderr)


if __name__ == "__main__":
    main()
