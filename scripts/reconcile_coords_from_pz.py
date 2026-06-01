#!/usr/bin/env python3
"""
Reconcile collection.json coords (set_code / card_number) against PZ ownership,
cross-validated by pack_sources × TCGdex × Limitless (via coord_resolver).

Why: assign_collection_coords.py *guessed* coords heuristically and got ~124 wrong for
cards that exist in multiple sets. PZ knows the exact printing owned; its card_number is
reliable but its set_code is sometimes wrong (A4b mislabeled A1/A2). coord_resolver
recovers and cross-validates the true coord.

For each collection entry matched to PZ card(s):
  - 1 authoritative coord  → re-coord the entry (set_code, card_number, rarity, count).
  - N authoritative coords → SPLIT into per-coord entries (a card owned across sets),
                             each inheriting base data with its own count + rarity.
Entries PZ didn't return are preserved unchanged (the missing-from-PZ grace logic owns them).

Aborts the write unless EVERY resolved coord is `confirmed` or `single-source`
(never on `conflict` / `unconfirmed`), no duplicate coords remain, and the total equals
PZ's total.

Usage:
    python3 scripts/reconcile_coords_from_pz.py            # dry-run (report only)
    python3 scripts/reconcile_coords_from_pz.py --apply    # write collection.json
    python3 scripts/reconcile_coords_from_pz.py --no-fetch # use caches only (offline)
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_collection as sc
from _collection_io import strip_comments
from coord_resolver import CoordResolver

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"
LAST_SYNC_RAW   = ROOT / "data" / "sync" / "last_sync_raw.json"

# Pokemon-only fields that don't apply when an entry is a Trainer (kept on splits only
# if already present; not invented).
_OK_CONFIDENCE = {"confirmed", "single-source"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write collection.json (default: dry-run)")
    ap.add_argument("--no-fetch", action="store_true", help="use caches only (no network)")
    args = ap.parse_args()

    full = json.loads(strip_comments(COLLECTION_JSON.read_text(encoding="utf-8")))
    collection = full["collection"]
    pack_sources = sc.load_pack_sources()
    ext_ref = sc.load_ext_ref()
    resolver = CoordResolver(fetch=not args.no_fetch)

    raw = json.loads(LAST_SYNC_RAW.read_text(encoding="utf-8"))
    cards = raw if isinstance(raw, list) else next(
        (v for v in raw.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])
    pz_cards = [p for p in (sc.normalize_pz_record(c) for c in cards) if p]

    results = sc.match_pz_cards(pz_cards, collection, pack_sources, ext_ref)
    entry_pz = defaultdict(list)   # entry_index -> [(pz_set, pz_num, count)]
    for r in results:
        if r.status == "MATCHED" and r.entry_index is not None:
            entry_pz[r.entry_index].append((r.pz_card.set_code, r.pz_card.card_number, r.pz_card.count))

    new_collection = []
    recoord = split = unchanged = preserved = 0
    bad_confidence = []   # (name, set, num, confidence, detail)
    changes = []          # (name, old_coord, new_coords)

    for idx, entry in enumerate(collection):
        pzlist = entry_pz.get(idx)
        if not pzlist:
            new_collection.append(entry)
            preserved += 1
            continue

        # Resolve + cross-validate each PZ coord, collapse identical authoritative coords.
        by_coord = defaultdict(lambda: [None, 0, None])   # (set,num) -> [rarity, count, confidence]
        for pz_set, pz_num, cnt in pzlist:
            rc = resolver.resolve(entry["name"], pz_set, pz_num)
            if rc.confidence not in _OK_CONFIDENCE:
                bad_confidence.append((entry["name"], rc.set_code, rc.card_number, rc.confidence, rc.detail))
            key = (rc.set_code, rc.card_number)
            by_coord[key][0] = rc.rarity
            by_coord[key][1] += cnt
            by_coord[key][2] = rc.confidence

        cur = (str(entry.get("set_code") or "").upper(), entry.get("card_number"))
        if len(by_coord) == 1:
            (s, n), (rar, cnt, _c) = next(iter(by_coord.items()))
            e = dict(entry)
            e["set_code"], e["card_number"], e["count"] = s, n, cnt
            if rar is not None:
                e["rarity"] = rar
            new_collection.append(e)
            if (s, n) != cur or cnt != entry.get("count"):
                recoord += 1
                changes.append((entry["name"], cur, [(s, n)]))
            else:
                unchanged += 1
        else:
            split += 1
            changes.append((entry["name"], cur, sorted(by_coord)))
            for (s, n), (rar, cnt, _c) in sorted(by_coord.items()):
                e = dict(entry)
                e["set_code"], e["card_number"], e["count"] = s, n, cnt
                if rar is not None:
                    e["rarity"] = rar
                new_collection.append(e)

    resolver.save()

    # ── Validate ──
    total = sum(e["count"] for e in new_collection)
    pairs = defaultdict(list)
    for e in new_collection:
        s, n = str(e.get("set_code") or "").upper(), e.get("card_number")
        if s and n is not None:
            pairs[(s, n)].append(e["name"])
    dups = {k: v for k, v in pairs.items() if len(v) > 1}
    pz_total = sum(p.count for p in pz_cards)

    print("=== Reconciliation summary ===")
    print(f"  entries: {len(collection)} → {len(new_collection)}")
    print(f"  re-coorded: {recoord}   split: {split}   unchanged: {unchanged}   preserved (not in PZ): {preserved}")
    print(f"  total count: {total}   (PZ total: {pz_total})")
    print(f"  duplicate coords after: {len(dups)}")
    for k, v in list(dups.items())[:10]:
        print(f"     {k[0]}/{k[1]} ×{len(v)}: {v}")
    print(f"  coords NOT confirmed/single-source: {len(bad_confidence)}")
    for it in bad_confidence[:20]:
        print(f"     {it}")
    print("  sample changes:")
    for nm, old, new in changes[:25]:
        print(f"     {nm}: {old[0]}/{old[1]} → {['%s/%s' % (s, n) for s, n in new]}")

    if not args.apply:
        print("\nDRY RUN — collection.json not modified. Re-run with --apply to write.")
        return 0

    if dups:
        print("\nABORT: duplicate coords present — not writing.", file=sys.stderr); return 1
    if bad_confidence:
        print("\nABORT: unconfirmed/conflict coords — not writing.", file=sys.stderr); return 1
    if total != pz_total:
        print(f"\nABORT: total {total} != PZ total {pz_total} — not writing.", file=sys.stderr); return 1

    full["collection"] = new_collection
    full.setdefault("meta", {})["total_cards"] = total
    COLLECTION_JSON.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote collection.json ({len(new_collection)} entries, total={total}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
