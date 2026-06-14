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
from _collection_io import (strip_comments, norm_card_name, ROOT,
                            COLLECTION_JSON, CARD_REF_JSON,
                            REPRINT_LINKS_JSON as REPRINT_LINKS)
from coord_resolver import CoordResolver

LAST_SYNC_RAW   = ROOT / "data" / "sync" / "last_sync_raw.json"

_BASE_RARITIES = {"common", "uncommon", "rare", "double_rare"}

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

    # Dual-location (A4b "Deluxe Pack: ex") handling. PZ exports these as HYBRID coords:
    # the ORIGINAL set code + the A4b number (e.g. Cubone as A1/194). User-verified in-app
    # behavior (2026-06-12): the first owned copy fills the ORIGINAL set's dex slot; further
    # copies fill the A4b slot. So a hybrid record re-coords to the original printing, and
    # splits 1/(n-1) across original/A4b when count >= 2.
    ref_records = json.loads(CARD_REF_JSON.read_text(encoding="utf-8")).get("records", [])
    ref_by_coord = {(str(r["set_code"]).upper(), r["card_number"]): r for r in ref_records}
    link_orig = {}   # (A4B, num) -> (orig_set_upper, orig_num)
    if REPRINT_LINKS.exists():
        for l in json.loads(REPRINT_LINKS.read_text(encoding="utf-8")).get("links", []):
            link_orig[(str(l["a4b"][0]).upper(), l["a4b"][1])] = \
                (str(l["original"][0]).upper(), l["original"][1])

    def find_original(name: str, pz_set: str, a4b_num: int):
        """Original-printing coord for an A4b dual-location card, or None.
        Prefers reprint_links; falls back to the unique base-rarity name match in
        PZ's set (PZ's set code IS the original set)."""
        o = link_orig.get(("A4B", a4b_num))
        if o and o[0] == str(pz_set).upper():
            return o
        cands = sorted({(s, n) for (s, n), r in ref_by_coord.items()
                        if s == str(pz_set).upper() and r.get("rarity") in _BASE_RARITIES
                        and norm_card_name(r.get("name", "")) == norm_card_name(name)})
        return cands[0] if len(cands) == 1 else None

    def ext_hp(name: str, set_code, num) -> int | None:
        """HP of the exact printing per ext_ref (Limitless) — printings of the same
        Pokémon differ in HP across sets, so a split/re-coorded entry must not
        inherit the source entry's HP."""
        for r in ext_ref.get(norm_card_name(name), []):
            if str(r.get("set_code", "")).upper() == str(set_code or "").upper() \
                    and r.get("number") == num:
                return r.get("hp")
        return None

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
    origins = []          # parallel to new_collection: "pz" | "preserved"
    recoord = split = unchanged = preserved = 0
    bad_confidence = []   # (name, set, num, confidence, detail)
    changes = []          # (name, old_coord, new_coords)

    def _key(e: dict) -> tuple:
        return (str(e.get("set_code") or "").upper(), e.get("card_number"),
                norm_card_name(e.get("name", "")))

    for idx, entry in enumerate(collection):
        pzlist = entry_pz.get(idx)
        if not pzlist:
            new_collection.append(entry)
            origins.append("preserved")
            preserved += 1
            continue

        # Resolve + cross-validate each PZ coord, collapse identical authoritative coords.
        by_coord = defaultdict(lambda: [None, 0, None])   # (set,num) -> [rarity, count, confidence]
        for pz_set, pz_num, cnt in pzlist:
            rc = resolver.resolve(entry["name"], pz_set, pz_num)
            if rc.confidence not in _OK_CONFIDENCE:
                bad_confidence.append((entry["name"], rc.set_code, rc.card_number, rc.confidence, rc.detail))
            if rc.confidence == "conflict":
                # Can't auto-resolve: keep the existing collection coord rather than
                # overwriting it with None.  Logged above; --apply will skip this entry.
                key = (str(entry.get("set_code") or "").upper(), entry.get("card_number"))
            else:
                key = (rc.set_code, rc.card_number)

            # Dual-location hybrid: PZ set != A4b but the coord resolved to A4b.
            if (str(key[0] or "").upper() == "A4B"
                    and str(pz_set or "").upper() != "A4B"
                    and rc.confidence in _OK_CONFIDENCE):
                orig = find_original(entry["name"], pz_set, key[1])
                orig_ref = ref_by_coord.get(orig) if orig else None
                if orig_ref is None:
                    bad_confidence.append((entry["name"], key[0], key[1], "conflict",
                                           f"dual-location card: no original found in {pz_set}"))
                else:
                    if cnt >= 2:
                        # 2nd+ copies fill the A4b slot
                        by_coord[key][0] = rc.rarity
                        by_coord[key][1] += cnt - 1
                        by_coord[key][2] = rc.confidence
                        cnt = 1
                    key = (orig_ref["set_code"], orig_ref["card_number"])
                    rc = type(rc)(rc.name, key[0], key[1], orig_ref.get("rarity"),
                                  rc.confidence, rc.sources_agreed,
                                  rc.detail + "; dual-location → original slot")

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
            hp = ext_hp(entry["name"], s, n)
            if hp is not None and entry.get("card_type") == "Pokemon":
                e["hp"] = hp
            new_collection.append(e)
            origins.append("pz")
            if (str(s).upper(), n) != cur or cnt != entry.get("count") \
                    or s != entry.get("set_code") \
                    or (hp is not None and hp != entry.get("hp")):
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
                hp = ext_hp(entry["name"], s, n)
                if hp is not None and entry.get("card_type") == "Pokemon":
                    e["hp"] = hp
                new_collection.append(e)
                origins.append("pz")

    resolver.save()

    # Drop preserved entries shadowed by a PZ-derived entry at the same coord+name.
    # A dual-location split re-derives BOTH coords from the one PZ record each run;
    # the A4b-half entry written by a prior reconcile gets no PZ record of its own and
    # would otherwise survive as a duplicate (and double-count).
    pz_keys = {_key(e) for e, o in zip(new_collection, origins) if o == "pz"}
    deduped = [e for e, o in zip(new_collection, origins)
               if o == "pz" or _key(e) not in pz_keys]
    if len(deduped) != len(new_collection):
        preserved -= len(new_collection) - len(deduped)
        new_collection = deduped

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
    unconfirmed = [b for b in bad_confidence if b[3] == "unconfirmed"]
    if unconfirmed:
        print("\nABORT: unconfirmed coords (new cards not in reference) — not writing.", file=sys.stderr); return 1
    if bad_confidence:
        # Conflicts only: existing coords preserved above; warn but allow --apply.
        print(f"\nWARNING: {len(bad_confidence)} conflict coord(s) above kept at existing value — verify manually.")
    if total != pz_total:
        print(f"\nABORT: total {total} != PZ total {pz_total} — not writing.", file=sys.stderr); return 1
    if new_collection == collection:
        print("\nNo changes — collection.json left untouched.")
        return 0

    full["collection"] = new_collection
    full.setdefault("meta", {})["total_cards"] = total
    COLLECTION_JSON.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote collection.json ({len(new_collection)} entries, total={total}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
