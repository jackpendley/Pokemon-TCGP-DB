#!/usr/bin/env python3
"""
Build data/reference/printing_groups.json — coords that are the SAME physical card.

WHY: the 2026-07-29 game update changed card-dex registration. Obtaining a card
that appears in several booster packs now registers it under *every* one of those
expansions, retroactively — "if you obtain Mewtwo ex from Genetic Apex, it will be
registered in your card dex under both Genetic Apex and Deluxe Pack: ex."

Before that update the dex filled one slot at a time, which the pipeline mirrored by
SPLITTING copies across the two coords (1st copy → original slot, 2nd+ → A4b slot).
That model is now wrong: one copy fills both slots. Rather than duplicating counts in
collection.json (you own three cards, not six), ownership stays stored per-coord
exactly as Pokémon Zone reports it and is *propagated* across a printing group when
read — for dex completion, for the cards browser, and for EV.

SOURCES, both of them Pokémon Zone's own data — nothing is inferred from name
matching across the catalog:

  1. HYBRID COORDS. For a card that occupies a reprint slot, PZ reports the
     *original's* set code carrying the *reprint's* card number — Cubone arrives
     as A1/194, where A1/194 is Wigglytuff and the real printings are A1/151 and
     A4b/194. That coord is direct evidence the card fills the A4b slot, and the
     pipeline already decodes the convention in reconcile_coords_from_pz and
     coord_resolver. This is the bulk of the signal: 24 of the 49 Deluxe Pack: ex
     slots the game credits arrive this way.
  2. `expansionIds`. A player record lists
every expansion the card registers in — the game's own answer to "is this card
included in multiple booster packs", which is precisely the question the dex rule
turns on. It names expansions rather than coords, so the partner coord inside each
expansion is resolved by name + base rarity, and an ambiguous match is skipped
rather than guessed.

Deliberately NOT sourced from reprint_links.json. That map pairs A4b printings to
their originals by a name+rarity heuristic (245 links, 12 of them user-confirmed)
and was built for a different job. Using it to synthesise dex registrations
credited 87 of 353 A4b base slots when the game showed 49 and Pokémon Zone's own
data showed 27 — inference presented as fact, inflating completion by ~3x the
sourced signal. Being behind a stale upstream is recoverable; being confidently
wrong is not.

A group is a set of coords closed under those edges (union-find), with a `debut`
coord — the earliest printing, which is where "first appeared" display rules point.

    python3 scripts/build_printing_groups.py [--dry-run]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _collection_io import (  # noqa: E402
    A4B_SET_CODE,
    CARD_REF_JSON,
    REFERENCE_DIR,
    ROOT,
    norm_card_name,
    normalize_rarity,
)

PRINTING_GROUPS_JSON = REFERENCE_DIR / "printing_groups.json"
LAST_SYNC_RAW = ROOT / "data" / "sync" / "last_sync_raw.json"

# Only base-rarity printings are the "same card" across expansions. Full-art,
# secret and crown printings are independent dex slots on both sides — the same
# rule build_reprint_links.py applies.
BASE_RARITIES = frozenset({"common", "uncommon", "rare", "double_rare"})

# The set PZ reports via hybrid coords. A4b "Deluxe Pack: ex" is the only reprint
# set today; A4B_SET_CODE is the shared constant every other consumer uses.
REPRINT_SET = A4B_SET_CODE

# Debut ordering. Sets released earlier come first; a card's debut is the earliest
# printing in this order, then the lowest card number.
SET_ORDER = [
    "A1", "A1A", "A2", "A2A", "A2B", "A3", "A3A", "A3B",
    "A4", "A4A", "A4B", "B1", "B1A", "B2", "B2A", "B2B",
    "B3", "B3A", "B3B", "B4", "PROMO-A", "PROMO-B",
]
_ORDER = {s: i for i, s in enumerate(SET_ORDER)}


class _Union:
    """Minimal union-find over coord tuples."""

    def __init__(self):
        self.parent: dict = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _coord(set_code, num) -> tuple:
    return (str(set_code).upper(), int(num))


def _debut_key(c: tuple) -> tuple:
    return (_ORDER.get(c[0], len(SET_ORDER)), c[1])


def load_reference() -> list[dict]:
    return json.loads(CARD_REF_JSON.read_text(encoding="utf-8")).get("records", [])


def _load_pz_records() -> list[dict]:
    if not LAST_SYNC_RAW.exists():
        return []
    try:
        raw = json.loads(LAST_SYNC_RAW.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(raw, list):
        return raw
    return next((v for v in raw.values()
                 if isinstance(v, list) and v and isinstance(v[0], dict)), [])


def hybrid_edges(uf: _Union, records: list[dict]) -> tuple[int, int]:
    """Edges from Pokémon Zone's hybrid reprint coords.

    A record whose (set_code, card_number) does not name its own card, but whose
    card_number DOES name it inside the reprint set, is PZ telling us the card
    occupies that reprint slot. Both coords follow: the reprint slot is
    (REPRINT_SET, number) directly, and the original is that name at the same base
    rarity inside the set PZ stamped.

    This is the signal the pipeline used to throw away. reconcile_coords_from_pz
    re-coords these records onto the original printing, so the reprint slot was
    left reading unowned — Deluxe Pack: ex showed 25 of the 49 slots the game
    credits, and every attempt to close that gap by matching names across the
    catalog overshot instead.

    Returns (edges_added, unresolved).
    """
    ref_by_coord = {_coord(r["set_code"], r["card_number"]): r for r in records}
    by_name: dict[tuple, list] = defaultdict(list)
    for r in records:
        rar = normalize_rarity(r.get("rarity"))
        if rar not in BASE_RARITIES:
            continue
        by_name[(str(r["set_code"]).upper(),
                 norm_card_name(r.get("name", "")), rar)].append(
            _coord(r["set_code"], r["card_number"]))

    added = unresolved = 0
    for c in _load_pz_records():
        if not isinstance(c, dict):
            continue
        num = c.get("cardNumber")
        stamped = str(c.get("setCode") or "").upper()
        name = norm_card_name(c.get("cardName", ""))
        if num is None or not stamped or not name:
            continue
        if stamped == REPRINT_SET:
            continue  # already filed under the reprint set; no hybrid to decode

        here = ref_by_coord.get((stamped, num))
        if here and norm_card_name(here.get("name", "")) == name:
            continue  # coord names its own card — not a hybrid

        slot = ref_by_coord.get((REPRINT_SET, num))
        if not slot or norm_card_name(slot.get("name", "")) != name:
            continue  # not a reprint-slot coord either; leave it alone

        rar = normalize_rarity(slot.get("rarity"))
        if rar not in BASE_RARITIES:
            continue
        originals = [x for x in by_name.get((stamped, name, rar), [])
                     if x != (REPRINT_SET, num)]
        if len(originals) == 1:
            uf.union(originals[0], (REPRINT_SET, num))
            added += 1
        else:
            unresolved += 1
    return added, unresolved


def pz_edges(uf: _Union, records: list[dict]) -> tuple[int, int]:
    """Edges from Pokémon Zone's expansionIds.

    PZ names the expansions a card registers in, not the coord inside each, and its
    own coord is a HYBRID for exactly these cards: the *original* set code carrying
    the *reprint's* card number (Cubone arrives as A1/194, whose real printings are
    A1/151 and A4b/194). Trusting setCode would look the coord up as whatever card
    happens to sit at A1/194 — Wigglytuff — and resolve nothing.

    So the number is treated as reliable and the set code is not: the anchor is
    whichever listed expansion actually holds a card of that number with this name.
    Remaining expansions resolve by name + base rarity, and anything ambiguous or
    missing is skipped rather than guessed.

    Returns (edges_added, unresolved).
    """
    cards = _load_pz_records()

    # (set, normalized name, normalized rarity) -> [coords], base rarities only.
    # Full-art and secret printings are independent dex slots on both sides.
    by_name: dict[tuple, list] = defaultdict(list)
    for r in records:
        rar = normalize_rarity(r.get("rarity"))
        if rar not in BASE_RARITIES:
            continue
        key = (str(r["set_code"]).upper(), norm_card_name(r.get("name", "")), rar)
        by_name[key].append(_coord(r["set_code"], r["card_number"]))

    ref_by_coord = {_coord(r["set_code"], r["card_number"]): r for r in records}

    added = unresolved = 0
    for c in cards:
        if not isinstance(c, dict):
            continue
        exps = [str(e).upper() for e in (c.get("expansionIds") or []) if e]
        if len(exps) < 2:
            continue
        num = c.get("cardNumber")
        name = norm_card_name(c.get("cardName", ""))
        if num is None or not name:
            continue

        # Anchor: the listed expansion that genuinely holds this number+name.
        anchor = None
        for exp in exps:
            ref = ref_by_coord.get((exp, num))
            if ref and norm_card_name(ref.get("name", "")) == name:
                anchor = (exp, num)
                break
        if anchor is None:
            unresolved += 1
            continue

        rar = normalize_rarity(ref_by_coord[anchor].get("rarity"))
        if rar not in BASE_RARITIES:
            continue

        for exp in exps:
            if exp == anchor[0]:
                continue
            cands = [x for x in by_name.get((exp, name, rar), []) if x != anchor]
            if len(cands) == 1:
                uf.union(anchor, cands[0])
                added += 1
            else:
                unresolved += 1
    return added, unresolved


def build() -> dict:
    records = load_reference()
    uf = _Union()

    n_hybrid, n_hybrid_unresolved = hybrid_edges(uf, records)
    n_pz, n_unresolved = pz_edges(uf, records)

    clusters: dict = defaultdict(set)
    for coord in list(uf.parent):
        clusters[uf.find(coord)].add(coord)

    ref_by_coord = {_coord(r["set_code"], r["card_number"]): r for r in records}

    groups = []
    for i, coords in enumerate(sorted(clusters.values(), key=lambda s: sorted(s)[0], reverse=False)):
        # Drop coords the reference doesn't know (stale links); a group needs 2+.
        known = sorted((c for c in coords if c in ref_by_coord), key=_debut_key)
        if len(known) < 2:
            continue
        debut = known[0]
        groups.append({
            "id": f"g{i + 1:04d}",
            "name": ref_by_coord[debut].get("name"),
            "debut": list(debut),
            "coords": [list(c) for c in known],
        })

    grouped_coords = sum(len(g["coords"]) for g in groups)
    return {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "1.0",
            "description": (
                "Coords that are the same physical card, per Pokémon Zone's expansionIds. "
                "Since the 2026-07-29 update a card registers in the dex under every "
                "expansion it appears in, so ownership of any coord in a group credits "
                "the whole group. Sourced only — never inferred from name matching."
            ),
            "sources": {
                "pz_hybrid_coord_edges": n_hybrid,
                "pz_hybrid_unresolved": n_hybrid_unresolved,
                "pz_expansion_edges": n_pz,
                "pz_unresolved": n_unresolved,
            },
            "group_count": len(groups),
            "grouped_coord_count": grouped_coords,
        },
        "groups": groups,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report only; do not write")
    args = ap.parse_args()

    data = build()
    m = data["_meta"]
    print(f"  PZ hybrid-coord edges: {m['sources']['pz_hybrid_coord_edges']} "
          f"({m['sources']['pz_hybrid_unresolved']} unresolved)")
    print(f"  PZ expansion edges  : {m['sources']['pz_expansion_edges']} "
          f"({m['sources']['pz_unresolved']} unresolved)")
    print(f"  groups              : {m['group_count']} "
          f"covering {m['grouped_coord_count']} coords")

    if args.dry_run:
        print("\n  (dry run — nothing written)")
        return 0

    PRINTING_GROUPS_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWritten → {PRINTING_GROUPS_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
