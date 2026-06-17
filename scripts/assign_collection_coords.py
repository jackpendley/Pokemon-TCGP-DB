#!/usr/bin/env python3
"""
Assign set_code, card_number, and rarity to every collection.json entry that
is missing them.  Fully automated — no manual review required.

Disambiguation priority per entry:
  1. Name match     → candidates from pack_sources by card_name
  2. HP filter      → keep candidates whose ext_ref HP matches entry HP
  3. Variant filter → "alt art" → highest card_number per set; else → lowest
  4. Stage/type     → filter by ext_ref stage/pokemon_type vs entry stage/type
  5. Tiebreaker     → pick candidate with earliest alphabetical set_code

Writes:
  data/current/coord_assignments_log.json — all assignments with confidence level

Usage:
    python3 scripts/assign_collection_coords.py          # assign and apply
    python3 scripts/assign_collection_coords.py --dry-run  # show assignments, no write
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (
    ext_ref_by_coord, card_reference_by_coord, load_records, PROMO_SET_CODES,
    TRAINER_SUBTYPE_MAP,
    TRAINER_CATEGORIES, RARE_PLUS_RARITIES, normalize_rarity, norm_card_name,
    load_collection_json, ROOT, COLLECTION_JSON, PACK_SOURCES_JSON,
    EXT_REF_JSON, CARD_REF_JSON, CURRENT_DIR,
)

LOG_JSON         = CURRENT_DIR / "coord_assignments_log.json"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_collection() -> tuple[dict, list]:
    _, data = load_collection_json()
    return data, data["collection"]


def load_pack_sources() -> dict[str, list]:
    """Returns {norm_card_name(card_name): [record, ...]}"""
    records = load_records(PACK_SOURCES_JSON)
    by_name: dict[str, list] = defaultdict(list)
    for r in records:
        name = (r.get("card_name") or "").strip()
        by_name[norm_card_name(name)].append(r)
    return dict(by_name)


# ---------------------------------------------------------------------------
# Disambiguation logic
# ---------------------------------------------------------------------------

# card_reference stage strings ("Basic"/"Stage1"/"Stage2") → collection (int, label) convention.
_CARD_REF_STAGE: dict[str, tuple[int, str]] = {
    "Basic":   (0, "Basic"),
    "Stage1":  (1, "Stage 1"),
    "Stage2":  (2, "Stage 2"),
}


def _stage_match(entry_stage, ext_stage) -> bool:
    """Loose stage comparison: collection uses 0/1/2 integers, ext_ref uses Basic/Stage 1/etc."""
    if entry_stage is None or ext_stage is None:
        return True  # no data to reject on
    stage_map = {0: "basic", 1: "stage 1", 2: "stage 2"}
    entry_label = stage_map.get(entry_stage, str(entry_stage)).lower()
    return entry_label in ext_stage.lower()


def _type_match(entry_type, ext_type) -> bool:
    if not entry_type or not ext_type:
        return True
    return entry_type.lower() == ext_type.lower()


def pick_candidate(entry: dict, candidates: list[dict], ext_ref: dict) -> tuple[dict, str]:
    """
    Choose the best pack_sources candidate for a collection entry.
    Returns (chosen_record, confidence) where confidence is 'high' | 'medium' | 'tiebreak'.
    """
    entry_hp      = entry.get("hp")
    entry_variant = (entry.get("variant") or "").lower()
    entry_stage   = entry.get("stage")
    entry_type    = entry.get("type")
    # "alt art" in variant string → one_star+ card. Named attack arts (e.g. "Flame Tail art")
    # describe the BASE card's artwork, not a full art — treated as base/non-alt.
    is_alt_art    = "alt art" in entry_variant

    # ── Step 2: HP filter ────────────────────────────────────────────────────
    hp_filtered = []
    for c in candidates:
        sc = str(c.get("set_code") or "").upper().strip()
        cn_raw = c.get("card_number")
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            continue
        ref = ext_ref.get((sc, cn))
        ref_hp = ref.get("hp") if ref else None
        if entry_hp is not None and ref_hp is not None:
            if ref_hp == entry_hp:
                hp_filtered.append(c)
        else:
            hp_filtered.append(c)  # no HP data to reject on

    pool = hp_filtered if hp_filtered else candidates
    confidence = "high" if len(pool) == 1 else "medium"

    # ── Step 3: Variant filter ───────────────────────────────────────────────
    # Use rarity tier to separate base art (1-3 diamond) from alt art (one_star+).
    # "alt art" in variant → the card is a one_star+ full-art; prefer those candidates.
    # Named attack arts ("Flame Tail art") and no-variant → prefer diamond-rarity cards.
    if len(pool) > 1:
        # normalize_rarity guards against any legacy/un-migrated rarity in the pool so
        # the RARE_PLUS_RARITIES (new-vocabulary) membership test matches correctly.
        if is_alt_art:
            rare_candidates = [c for c in pool if normalize_rarity(c.get("rarity")) in RARE_PLUS_RARITIES]
        else:
            rare_candidates = [c for c in pool if normalize_rarity(c.get("rarity")) not in RARE_PLUS_RARITIES]

        if rare_candidates:
            pool = rare_candidates

    # ── Step 4: Stage / type filter ─────────────────────────────────────────
    if len(pool) > 1:
        st_filtered = []
        for c in pool:
            sc = str(c.get("set_code") or "").upper().strip()
            cn_raw = c.get("card_number")
            try:
                cn = int(cn_raw)
            except (TypeError, ValueError):
                continue
            ref = ext_ref.get((sc, cn))
            if ref:
                if _stage_match(entry_stage, ref.get("stage")) and \
                   _type_match(entry_type, ref.get("pokemon_type")):
                    st_filtered.append(c)
            else:
                st_filtered.append(c)  # no ext_ref data, keep

        if st_filtered:
            pool = st_filtered

    # ── Step 5: Tiebreaker — earliest set_code alphabetically ───────────────
    if len(pool) > 1:
        confidence = "tiebreak"
        pool = sorted(pool, key=lambda c: (
            str(c.get("set_code") or "").upper(),
            int(c.get("card_number") or 0)
        ))

    return pool[0], confidence


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Assign set coords to collection.json entries.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show assignments without writing collection.json")
    args = parser.parse_args()

    print("Loading data…")
    full_data, entries = load_collection()
    initial_count = sum(e.get("count", 0) for e in entries)
    ps_by_name = load_pack_sources()
    ext_ref    = ext_ref_by_coord(EXT_REF_JSON)
    # card_reference (TCGdex-backed, cross-validated) is the authority for pokemon_type;
    # it has full type coverage where Limitless-derived ext_ref leaves A-series types null.
    card_ref   = card_reference_by_coord(CARD_REF_JSON)

    assignments = []
    skipped = 0
    by_confidence: dict[str, int] = {"high": 0, "medium": 0, "tiebreak": 0}

    for idx, entry in enumerate(entries):
        # Already has coords?
        if entry.get("set_code") and entry.get("card_number") is not None:
            sc = str(entry["set_code"]).upper().strip()
            try:
                cn = int(entry["card_number"])
            except (TypeError, ValueError):
                skipped += 1
                continue
            # Look up rarity from pack_sources if missing or needs normalization
            ps_candidates = ps_by_name.get(norm_card_name(entry.get("name") or ""), [])
            ps_match = next(
                (c for c in ps_candidates
                 if str(c.get("set_code") or "").upper() == sc
                 and int(c.get("card_number") or -1) == cn),
                None
            )
            rarity_from_ps = normalize_rarity(ps_match.get("rarity") if ps_match else None)
            existing_rarity = normalize_rarity(entry.get("rarity"))
            if rarity_from_ps and rarity_from_ps != existing_rarity:
                assignments.append({
                    "index": idx,
                    "name": entry.get("name"),
                    "count": entry.get("count"),
                    "set_code": sc,
                    "card_number": cn,
                    "rarity": rarity_from_ps,
                    "confidence": "existing_coords_rarity_fill",
                })
            skipped += 1
            continue

        # FALLBACK ONLY: this heuristic coord-guesser runs solely for entries that
        # reach here WITHOUT a coord. The sync pipeline (coord_resolver) is the
        # authority and assigns cross-validated coords at add time, so in normal
        # operation no entry should land here. Heuristic guesses (esp. "tiebreak")
        # are NOT cross-validated and are flagged below for review.
        name = (entry.get("name") or "").strip()
        candidates = ps_by_name.get(norm_card_name(name), [])

        if not candidates:
            print(f"  WARNING: no pack_sources match for '{name}' (idx {idx})", file=sys.stderr)
            continue

        if len(candidates) == 1:
            chosen = candidates[0]
            confidence = "high"
        else:
            chosen, confidence = pick_candidate(entry, candidates, ext_ref)
        if confidence == "tiebreak":
            print(f"  WARN: heuristic tiebreak coord for '{name}' → "
                  f"{chosen.get('set_code')}/{chosen.get('card_number')} (NOT cross-validated; "
                  f"a sync would assign the authoritative coord)", file=sys.stderr)

        sc = str(chosen.get("set_code") or "").upper().strip()
        cn_raw = chosen.get("card_number")
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            print(f"  WARNING: invalid card_number for '{name}' in pack_sources", file=sys.stderr)
            continue

        rarity = normalize_rarity(chosen.get("rarity"))

        by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
        assignments.append({
            "index": idx,
            "name": name,
            "count": entry.get("count"),
            "set_code": sc,
            "card_number": cn,
            "rarity": rarity,
            "confidence": confidence,
        })

    print(f"\nAssignments: {len(assignments)} entries to update (skipped {skipped} with existing coords)")
    for conf, n in sorted(by_confidence.items()):
        print(f"  {conf}: {n}")

    # Write log
    LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    LOG_JSON.write_text(json.dumps(assignments, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nLog written → {LOG_JSON.relative_to(ROOT)}")

    if args.dry_run:
        print("\nDRY RUN — collection.json not modified.")
        return 0

    # ── Apply to collection.json ─────────────────────────────────────────────
    for a in assignments:
        entry = entries[a["index"]]
        entry["set_code"]    = a["set_code"]
        entry["card_number"] = a["card_number"]
        entry["rarity"]      = a["rarity"]
        # Also normalize any existing rarity aliases on entries we're NOT re-assigning coords to
        if entry.get("rarity"):
            entry["rarity"] = normalize_rarity(entry["rarity"])

    # ── Whole-collection cleanup (idempotent, safe to run every pipeline pass) ───
    # Build canonical set_code casing lookup from the already-loaded pack_sources
    # records (ps_by_name values) — avoids re-reading the 1.5 MB file.
    ps_sc_canonical: dict[str, str] = {}
    for recs in ps_by_name.values():
        for r in recs:
            sc = r.get("set_code") or ""
            if sc:
                ps_sc_canonical[sc.upper()] = sc

    is_ex_removed = 0
    case_fixed = 0
    rarity_alias_fixed = 0
    type_backfilled = 0
    stage_backfilled = 0
    card_type_flips: list[str] = []
    for entry in entries:
        # 1. Strip is_ex (no longer tracked; rarity encodes this)
        if "is_ex" in entry:
            del entry["is_ex"]
            is_ex_removed += 1
        # 2. Normalize rarity aliases
        if entry.get("rarity"):
            normalized = normalize_rarity(entry["rarity"])
            if normalized != entry["rarity"]:
                entry["rarity"] = normalized
                rarity_alias_fixed += 1
        # 2b. Promo cards carry no rarity symbol — keep the 'promo' sentinel when
        #     unresolved (many owned promos aren't in the sparse pack_sources reference).
        if not entry.get("rarity") and str(entry.get("set_code") or "").upper() in PROMO_SET_CODES:
            entry["rarity"] = "promo"
            rarity_alias_fixed += 1
        # 3. Normalize set_code casing to match pack_sources
        sc = entry.get("set_code") or ""
        if sc and sc.upper() in ps_sc_canonical:
            canon = ps_sc_canonical[sc.upper()]
            if canon != sc:
                entry["set_code"] = canon
                case_fixed += 1

        # 4. Reconcile card_type with ext_ref. Entries created from stale/missing
        #    ext_ref data can carry the wrong card_type; ext_ref (now classified
        #    by authoritative type-line supertype) is the source of truth.
        #    NON-DESTRUCTIVE: we only set card_type/trainer_subtype and backfill
        #    missing fields — never delete existing entry data. A wrong ext_ref
        #    flip is thus recoverable, and category flips are logged for review.
        #    (fetch_ext_ref.py also guards category flips at fetch time.)
        cn = entry.get("card_number")
        ext_rec = None
        if entry.get("set_code") and cn is not None:
            try:
                ext_rec = ext_ref.get((str(entry["set_code"]).upper(), int(cn)))
            except (TypeError, ValueError):
                ext_rec = None
        ext_cat = ext_rec.get("card_category") if ext_rec else None
        if ext_cat == "Pokemon" and entry.get("card_type") != "Pokemon":
            entry["card_type"] = "Pokemon"
            entry.pop("trainer_subtype", None)
            if ext_rec.get("hp") is not None and entry.get("hp") is None:
                entry["hp"] = ext_rec["hp"]
            card_type_flips.append(f"{entry.get('name')} ({entry['set_code']}/{cn}): →Pokemon")
        elif ext_cat in TRAINER_CATEGORIES and entry.get("card_type") != "Trainer":
            entry["card_type"] = "Trainer"
            entry["trainer_subtype"] = TRAINER_SUBTYPE_MAP[ext_cat]
            card_type_flips.append(f"{entry.get('name')} ({entry['set_code']}/{cn}): →Trainer/{ext_cat}")

        # 5. Backfill missing Pokémon type from card_reference (TCGdex-backed authority).
        #    ext_ref leaves A-series pokemon_type null; card_reference has full coverage.
        ref_coord = None
        if cn is not None:
            try:
                ref_coord = (str(entry.get("set_code") or "").upper(), int(cn))
            except (TypeError, ValueError):
                ref_coord = None
        ref_rec = card_ref.get(ref_coord) if ref_coord else None
        if entry.get("card_type") == "Pokemon" and not entry.get("type"):
            ref_type = ref_rec.get("pokemon_type") if ref_rec else None
            if ref_type:
                entry["type"] = ref_type
                type_backfilled += 1

        # 6. Backfill missing Pokémon stage from card_reference (same authority).
        #    A-series ext_ref has no stage, so older entries lack it; card_reference covers it.
        if entry.get("card_type") == "Pokemon" and entry.get("stage") is None and ref_rec:
            stg = _CARD_REF_STAGE.get(ref_rec.get("stage"))
            if stg:
                entry["stage"], entry["stage_label"] = stg
                stage_backfilled += 1

    if is_ex_removed:
        print(f"  Stripped is_ex from {is_ex_removed} entries")
    if case_fixed:
        print(f"  Normalized set_code casing on {case_fixed} entries")
    if rarity_alias_fixed:
        print(f"  Fixed {rarity_alias_fixed} rarity aliases")
    if type_backfilled:
        print(f"  Backfilled Pokémon type on {type_backfilled} entries from card_reference")
    if stage_backfilled:
        print(f"  Backfilled Pokémon stage on {stage_backfilled} entries from card_reference")
    if card_type_flips:
        print(f"  Reconciled card_type on {len(card_type_flips)} entries from ext_ref:")
        for flip in card_type_flips:
            print(f"    {flip}")

    # ── Validate ─────────────────────────────────────────────────────────────
    total_count = sum(e.get("count", 0) for e in entries)
    coord_pairs: list[tuple[str, int]] = []
    missing_coords = 0
    for e in entries:
        sc = str(e.get("set_code") or "").upper().strip()
        cn = e.get("card_number")
        if sc and cn is not None:
            coord_pairs.append((sc, int(cn)))
        else:
            missing_coords += 1

    # Duplicate check
    from collections import Counter
    dup_pairs = {k: v for k, v in Counter(coord_pairs).items() if v > 1}

    print(f"\nValidation:")
    print(f"  Total count: {total_count} (was {initial_count})")
    print(f"  Entries missing coords after assignment: {missing_coords}")
    print(f"  Duplicate (set_code, card_number) pairs: {len(dup_pairs)}")
    if dup_pairs:
        for pair, n in list(dup_pairs.items())[:10]:
            entries_with_dup = [e for e in entries
                                if str(e.get("set_code") or "").upper() == pair[0]
                                and e.get("card_number") == pair[1]]
            names = [e.get("name") for e in entries_with_dup]
            print(f"    {pair[0]}/{pair[1]} appears {n}× → {names}")

    if total_count != initial_count:
        print(f"  ERROR: count changed during script run ({initial_count} → {total_count})", file=sys.stderr)
        return 1

    # ── Write collection.json only if content actually changed ─────────────────
    # Avoids a redundant rewrite (and its mtime churn) on the common no-op run.
    new_text = json.dumps(full_data, indent=2, ensure_ascii=False)
    current_text = COLLECTION_JSON.read_text(encoding="utf-8")
    if new_text == current_text:
        print(f"\nNo changes — collection.json left untouched.")
    else:
        COLLECTION_JSON.write_text(new_text, encoding="utf-8")
        print(f"\nWrote updated collection.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
