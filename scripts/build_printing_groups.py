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

SOURCES, in precedence order:
  1. Pokémon Zone `expansionIds` (authoritative). A player record lists every
     expansion the card registers in. It names expansions, not coords, so the
     partner coord inside each expansion is resolved by name + base rarity.
  2. reprint_links.json (fallback, offline). The curated/heuristic A4b→original
     map, which is what the pipeline used before PZ exposed expansionIds.

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
    CARD_REF_JSON,
    REFERENCE_DIR,
    REPRINT_LINKS_JSON,
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


def reprint_edges(uf: _Union) -> int:
    """Edges from the curated/heuristic A4b → original-printing map."""
    if not REPRINT_LINKS_JSON.exists():
        return 0
    links = json.loads(REPRINT_LINKS_JSON.read_text(encoding="utf-8")).get("links", [])
    for l in links:
        uf.union(_coord(*l["a4b"]), _coord(*l["original"]))
    return len(links)


def pz_edges(uf: _Union, records: list[dict]) -> tuple[int, int]:
    """Edges from Pokémon Zone's expansionIds.

    PZ names the expansions a card registers in but not the coord inside each, so
    the partner is resolved by normalized name + base rarity within that expansion.
    Ambiguous or absent matches are skipped — reprint_links already covers the
    curated cases, and a wrong merge would silently mark an unowned card owned.

    Returns (edges_added, unresolved).
    """
    if not LAST_SYNC_RAW.exists():
        return 0, 0
    try:
        raw = json.loads(LAST_SYNC_RAW.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0, 0
    cards = raw if isinstance(raw, list) else next(
        (v for v in raw.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])

    # (set, normalized name, normalized rarity) -> [coords]
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
        home = _coord(c.get("setCode") or exps[0], c.get("cardNumber") or 0)
        ref = ref_by_coord.get(home)
        if ref is None:
            continue
        rar = normalize_rarity(ref.get("rarity"))
        if rar not in BASE_RARITIES:
            continue
        nn = norm_card_name(ref.get("name", ""))
        for exp in exps:
            if exp == home[0]:
                continue
            cands = by_name.get((exp, nn, rar), [])
            if len(cands) == 1:
                uf.union(home, cands[0])
                added += 1
            else:
                unresolved += 1
    return added, unresolved


def build() -> dict:
    records = load_reference()
    uf = _Union()

    n_links = reprint_edges(uf)
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
                "Coords that are the same physical card. Since the 2026-07-29 update a "
                "card registers in the dex under every expansion it appears in, so "
                "ownership of any coord in a group credits the whole group."
            ),
            "sources": {
                "reprint_links": n_links,
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
    print(f"  reprint_links edges : {m['sources']['reprint_links']}")
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
