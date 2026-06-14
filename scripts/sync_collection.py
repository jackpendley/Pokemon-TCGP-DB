#!/usr/bin/env python3
"""
Sync collection.json from Pokemon Zone (pokemon-zone.com).

The user must have linked their Nintendo Account to Pokemon Zone first.

EASIEST — Browser bookmarklet (always works, no auth to manage):
    1. Add the bookmarklet from CLAUDE.md section 4 to your bookmarks bar.
    2. Open pokemon-zone.com/collection-tracker/ (must be logged in).
    3. Click the bookmarklet → pz_collection.json downloads automatically.
    4. Run:  python3 scripts/sync_collection.py --json-import pz_collection.json

FIRST-TIME SETUP (Cloudflare-safe, enables headless syncs):
    python3 scripts/sync_collection.py --curl-import
    # Opens instructions; paste a cURL from browser DevTools once.
    # Auth is stored in data/sync/.auth.json (gitignored).

SUBSEQUENT SYNCS (headless, no browser):
    python3 scripts/sync_collection.py            # uses stored auth
    python3 scripts/sync_collection.py --dry-run  # show diff, no writes

WHEN AUTH EXPIRES (re-run curl import):
    python3 scripts/sync_collection.py --curl-import

ONE-SHOT HAR IMPORT (no persistent auth):
    python3 scripts/sync_collection.py --har-import www.pokemon-zone.com.har

OTHER:
    python3 scripts/sync_collection.py --discover # inspect API responses (Playwright)
    python3 scripts/sync_collection.py --login    # headed Playwright login (may hit Cloudflare)

Exit codes:
    0  Success — collection.json updated and validated
    1  Fatal error (auth missing/expired, API failure, validation failure)
    2  Partial — review queue has items (new/ambiguous cards); matched cards updated
    3  Blocked — unresolved review queue; run --force or resolve queue first
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (strip_comments, TRAINER_SUBTYPE_MAP, RARE_PLUS_RARITIES,
                            is_ex_from_name, pack_sources_by_coord as _ps_by_coord,
                            field_slug as _normalize, RARITY_RANK, normalize_rarity,
                            load_collection_json, ROOT, COLLECTION_JSON,
                            REPRINT_LINKS_JSON,
                            PACK_SOURCES_JSON as PACK_SOURCES,
                            EXT_REF_JSON as EXT_REF)


SYNC_DIR        = ROOT / "data" / "sync"
REVIEW_QUEUE    = SYNC_DIR / "sync_review_queue.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PZCard:
    set_code:    str | None
    card_number: int | None
    raw_name:    str
    count:       int


@dataclass
class MatchResult:
    status:        str   # MATCHED | NEW_CARD | AMBIGUOUS
    pz_card:       PZCard
    entry:         dict | None = None          # the collection.json entry (MATCHED only)
    entry_index:   int | None = None
    canonical_name: str | None = None


@dataclass
class CountChange:
    entry:       dict
    entry_index: int
    old_count:   int
    new_count:   int


# ---------------------------------------------------------------------------
# JSON / reference loaders
# ---------------------------------------------------------------------------

def load_collection() -> tuple[str, dict]:
    """Return (raw_text, parsed_dict) for collection.json."""
    return load_collection_json()


def load_pack_sources() -> dict[tuple[str, int], dict]:
    """Return {(set_code, card_number) → record}."""
    return _ps_by_coord(PACK_SOURCES)


def load_ext_ref() -> dict[str, list[dict]]:
    """Return {normalized_name → [records with hp/set_code/number]}."""
    records = json.loads(EXT_REF.read_text(encoding="utf-8"))
    result: dict[str, list[dict]] = {}
    for r in records:
        nn = _normalize(r.get("normalized_name") or r.get("name", ""))
        result.setdefault(nn, []).append(r)
    return result


def build_card_meta(
    ext_ref: dict[str, list[dict]],
    collection_entries: list[dict],
) -> dict[str, dict]:
    """Build {normalized_name → card_type_metadata} as fallback for auto-add.

    Used when ext_ref has no exact (set_code, card_number) match.  Populated
    from B-set ext_ref records (which have complete card_category coverage) plus
    every entry in collection.json (known-good schema values).
    Collection entries take priority so owned-card data is always authoritative.
    """
    meta: dict[str, dict] = {}

    for nn, records in ext_ref.items():
        for r in records:
            if r.get("card_category") and nn not in meta:
                cat = r.get("card_category", "")
                card_type = "Pokemon" if cat == "Pokemon" else "Trainer"
                meta[nn] = {
                    "card_type": card_type,
                    "trainer_subtype": TRAINER_SUBTYPE_MAP.get(cat) if card_type == "Trainer" else None,
                    "type": r.get("pokemon_type"),
                }
                break

    for entry in collection_entries:
        nn = _normalize(entry.get("name", ""))
        if entry.get("card_type"):
            meta[nn] = {
                "card_type": entry["card_type"],
                "trainer_subtype": entry.get("trainer_subtype"),
                "type": entry.get("type"),
            }

    return meta


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pokemon Zone record → PZCard
# ---------------------------------------------------------------------------

def _guess_field(record: dict, *candidates: str):
    """Return first value found among candidate field names (case-insensitive)."""
    lower = {k.lower(): v for k, v in record.items()}
    for c in candidates:
        v = lower.get(c.lower())
        if v is not None:
            return v
    return None


def normalize_pz_record(raw: dict) -> PZCard | None:
    """Convert a raw Pokemon Zone API record to a PZCard."""
    # Card name
    name = _guess_field(raw, "cardName", "name", "card_name", "pokemonName", "title")
    if not name:
        return None
    name = str(name).strip()
    if not name:
        return None

    # Count / quantity owned
    count_raw = _guess_field(raw, "ownedCount", "count", "quantity", "owned",
                              "amount", "copies", "cardCount")
    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        if count_raw is not None:
            print(f"WARNING: dropped PZ card '{name}' — count parse failed: {count_raw!r}", file=sys.stderr)
        count = 0
    if count <= 0:
        return None

    # Set code
    sc_raw = _guess_field(raw, "setCode", "set_code", "expansionCode", "set",
                           "expansion", "series")
    set_code = str(sc_raw).upper().strip() if sc_raw else None

    # Card number
    cn_raw = _guess_field(raw, "cardNumber", "card_number", "number", "cardId",
                           "collectorNumber")
    # Pokemon Zone may encode as "A1-004" or just 4 or "4"
    card_number: int | None = None
    if cn_raw is not None:
        # Try stripping set prefix if present (e.g. "A1-004" → 4)
        cn_str = str(cn_raw).strip()
        m = re.search(r"(\d+)$", cn_str.split("-")[-1])
        if m:
            try:
                card_number = int(m.group(1))
            except ValueError:
                card_number = None

    return PZCard(
        set_code=set_code,
        card_number=card_number,
        raw_name=name,
        count=count,
    )


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

# Rarity ordering for alt-art disambiguation — shared canonical rank
# (_collection_io.RARITY_RANK). normalize_rarity() is applied at the lookup site so
# both new-vocabulary and any legacy symbol-tier values resolve correctly.
_RARITY_RANK = RARITY_RANK

# Known PROMO-B card-number → canonical collection.json name overrides.
# PZ's catalog returns "Zygarde" for these slots; the correct names use form suffixes.
# #53 and #56 need overrides because pack_sources has no PROMO-B entries and the
# fuzzy matcher picks wrong cards at ≥85% ("Mega Ampharos ex", "Heracross").
_PROMO_B_OVERRIDES: dict[int, str] = {
    51: "Zygarde 10% Forme",
    52: "Zygarde 50% Forme",
    53: "Zygarde ex",
    56: "Mega Heracross ex",
}

# PROMO-A cards are not in pack_sources; fuzzy matcher picks wrong names ("Mega Charizard X ex",
# "Red") at ≥85%. Override directly to the correct collection.json names.
_PROMO_A_OVERRIDES: dict[int, str] = {
    1: "Potion",
    2: "X Speed",
    3: "Hand Scope",
    4: "Pokédex",
    6: "Red Card",
}

# Entries consecutively absent from PZ for this many syncs are considered stale and removed.
# The check fires when stored consecutive_missing == threshold-1 (i.e., this is the Nth miss).
_STALE_THRESHOLD = 3


def _build_name_index(collection: list[dict]) -> dict[str, list[int]]:
    """Return {normalized_name → [entry_indices]}."""
    idx: dict[str, list[int]] = {}
    for i, entry in enumerate(collection):
        nn = _normalize(entry.get("name", ""))
        idx.setdefault(nn, []).append(i)
    return idx


def match_pz_cards(
    pz_cards: list[PZCard],
    collection: list[dict],
    pack_sources: dict[tuple[str, int], dict],
    ext_ref: dict[str, list[dict]],
) -> list[MatchResult]:
    name_index = _build_name_index(collection)
    results: list[MatchResult] = []
    mismatches: list = []

    for pz in pz_cards:
        result = _match_one(pz, collection, name_index, pack_sources, ext_ref, mismatches)
        results.append(result)

    # Collapse the expected A4b-reprint hybrid mismatches into one summary line; surface any
    # mismatch outside the A1–A4 mislabel sets individually (those are genuinely unexpected).
    expected = [m for m in mismatches if m[4]]
    unexpected = [m for m in mismatches if not m[4]]
    if expected:
        print(f"  INFO: {len(expected)} A4b-reprint hybrid coords re-resolved by name match "
              f"(PZ stamps the original set code + A4b number; all matched).", file=sys.stderr)
    for sc, cn, raw, ps_name, _ in unexpected:
        print(f"  WARN: set-numbering mismatch {sc}#{cn} ({raw!r} vs pack_sources {ps_name!r}) "
              f"— using direct name match.", file=sys.stderr)

    # Pass 2: retry AMBIGUOUS results — exclude already-matched entry indices.
    # Handles cases where a sibling PZ record matched by HP first, leaving only one
    # candidate for the remaining ambiguous record (e.g. Mienfoo A1 after B1A matched).
    matched_indices: set[int] = {r.entry_index for r in results if r.status == "MATCHED"}
    changed = True
    while changed:
        changed = False
        for i, r in enumerate(results):
            if r.status != "AMBIGUOUS" or not r.canonical_name:
                continue
            nn = _normalize(r.canonical_name)
            remaining = [idx for idx in name_index.get(nn, []) if idx not in matched_indices]
            if len(remaining) == 1:
                idx = remaining[0]
                results[i] = MatchResult(
                    status="MATCHED",
                    pz_card=r.pz_card,
                    entry=collection[idx],
                    entry_index=idx,
                    canonical_name=r.canonical_name,
                )
                matched_indices.add(idx)
                changed = True

    # Pass 3: group-level rank assignment for remaining AMBIGUOUS groups.
    # When N PZ records and N unmatched collection entries share the same name,
    # assign by rarity rank then set_code order so lower-rarity PZ records map
    # to lower collection.json index entries (e.g. Riolu one_diamond → Fighting Fast).
    ambiguous_groups: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(results):
        if r.status == "AMBIGUOUS" and r.canonical_name:
            ambiguous_groups[r.canonical_name].append(i)

    for canon_name, res_idxs in ambiguous_groups.items():
        nn = _normalize(canon_name)
        remaining = [idx for idx in name_index.get(nn, []) if idx not in matched_indices]
        if len(res_idxs) != len(remaining) or len(res_idxs) < 2:
            continue

        def _pz_sort_key(ri: int) -> tuple:
            pz = results[ri].pz_card
            rank = 99
            if pz.set_code and pz.card_number is not None:
                ref = pack_sources.get((pz.set_code, pz.card_number))
                if ref:
                    rank = _RARITY_RANK.get(normalize_rarity(ref.get("rarity")) or "", 99)
            return (rank, pz.set_code or "", pz.card_number or 0)

        def _coll_sort_key(ci: int) -> tuple:
            """Sort collection entries rarity-ascending to mirror _pz_sort_key ordering."""
            entry = collection[ci]
            variant = (entry.get("variant") or "").lower()
            # Alt-art variants are higher rarity — sort them after base variants.
            is_alt = "alt" in variant.split()
            return (1 if is_alt else 0, ci)

        for ri, ci in zip(sorted(res_idxs, key=_pz_sort_key), sorted(remaining, key=_coll_sort_key)):
            results[ri] = MatchResult(
                status="MATCHED",
                pz_card=results[ri].pz_card,
                entry=collection[ci],
                entry_index=ci,
                canonical_name=canon_name,
            )
        matched_indices.update(remaining)

    # Force-resolve any remaining AMBIGUOUS by picking the first unmatched candidate.
    # Emits a WARN so the user can add disambiguation data to fix the root cause,
    # but never hard-crashes — every PZ card is always ingested.
    for i, r in enumerate(results):
        if r.status != "AMBIGUOUS" or not r.canonical_name:
            continue
        nn = _normalize(r.canonical_name)
        remaining = [idx for idx in name_index.get(nn, []) if idx not in matched_indices]
        if remaining:
            idx = remaining[0]
            print(
                f"  WARN: disambiguation failed for '{r.canonical_name}' "
                f"(set={r.pz_card.set_code}, num={r.pz_card.card_number}) "
                f"— force-matched to collection entry #{idx}. "
                f"Add HP/rarity to ext_ref or pack_sources to resolve properly.",
                file=sys.stderr,
            )
            results[i] = MatchResult(
                status="MATCHED",
                pz_card=r.pz_card,
                entry=collection[idx],
                entry_index=idx,
                canonical_name=r.canonical_name,
            )
            matched_indices.add(idx)
        else:
            # All variants already claimed — merge overflow count into first matched variant.
            # Creating a NEW_CARD here would duplicate an existing entry in collection.json;
            # instead, re-point to an already-matched index so Phase 5 aggregates the count.
            nn_idxs = [idx for idx in name_index.get(nn, []) if idx in matched_indices]
            target_idx = nn_idxs[0] if nn_idxs else None
            print(
                f"  WARN: overflow copies of '{r.canonical_name}' "
                f"(set={r.pz_card.set_code}, num={r.pz_card.card_number}) "
                f"— all {len(name_index.get(nn, []))} collection variant(s) already matched; "
                f"merging {r.pz_card.count} count into existing variant.",
                file=sys.stderr,
            )
            if target_idx is not None:
                results[i] = MatchResult(
                    status="MATCHED",
                    pz_card=r.pz_card,
                    entry=collection[target_idx],
                    entry_index=target_idx,
                    canonical_name=r.canonical_name,
                )
            else:
                results[i] = MatchResult(
                    status="NEW_CARD",
                    pz_card=r.pz_card,
                    canonical_name=r.canonical_name,
                )

    return results


# PZ stamps A4b "Deluxe Pack: ex" reprints with the original set code (A1–A4) + the A4b
# number, so their (set, number) names a different card in pack_sources. This is expected and
# resolved by the direct-name match below; only mismatches OUTSIDE these sets are surprising.
_A4B_HYBRID_TARGET_SETS = frozenset({"A1", "A2", "A3", "A4"})


def _match_one(
    pz: PZCard,
    collection: list[dict],
    name_index: dict[str, list[int]],
    pack_sources: dict,
    ext_ref: dict[str, list[dict]],
    mismatches: list | None = None,
) -> MatchResult:
    # Pre-step: PROMO overrides (PZ catalog returns wrong/missing names for these slots)
    canonical_name: str | None = None
    if pz.set_code == "PROMO-A" and pz.card_number in _PROMO_A_OVERRIDES:
        canonical_name = _PROMO_A_OVERRIDES[pz.card_number]
    elif pz.set_code == "PROMO-B" and pz.card_number in _PROMO_B_OVERRIDES:
        canonical_name = _PROMO_B_OVERRIDES[pz.card_number]

    # Step 1: exact (set_code, card_number) → pack_sources canonical name.
    # Sanity-check: if the raw_name is directly recognized in the collection AND
    # it disagrees with the pack_sources name, the set has a card-numbering mismatch
    # (e.g. PZ A1 uses different indices than our pack_sources). In that case skip
    # Step 1 and let Step 2's direct-name match resolve it correctly.
    if canonical_name is None and pz.set_code and pz.card_number is not None:
        ref = pack_sources.get((pz.set_code, pz.card_number))
        if ref:
            ps_name = ref["card_name"]
            nn_raw = _normalize(pz.raw_name)
            nn_ps  = _normalize(ps_name)
            if nn_raw == nn_ps:
                canonical_name = ps_name
            else:
                # Names disagree after normalization → set-numbering mismatch.
                # Fall through to Step 2's direct-name match using the PZ raw_name,
                # which is always safer than blindly trusting a mismatched pack_sources entry.
                # This handles both: card is already owned (raw_name in name_index) AND
                # card is not yet owned (raw_name not in name_index → NEW_CARD via fallback).
                expected = str(pz.set_code).upper() in _A4B_HYBRID_TARGET_SETS
                if mismatches is not None:
                    mismatches.append((pz.set_code, pz.card_number, pz.raw_name, ps_name, expected))
                elif not expected:
                    print(
                        f"  WARN: set-numbering mismatch {pz.set_code}#{pz.card_number} "
                        f"({pz.raw_name!r} vs pack_sources {ps_name!r}) "
                        f"— using direct name match.",
                        file=sys.stderr,
                    )

    # Step 2: direct normalized-name match against collection.json.
    # Catches Trainers and cards from sets not yet in pack_sources.
    if canonical_name is None:
        nn_direct = _normalize(pz.raw_name)
        if nn_direct in name_index:
            canonical_name = pz.raw_name

    # No match via any deterministic path — auto-add using the PZ name.
    # This ensures no card is ever silently dropped.
    if canonical_name is None:
        canonical_name = pz.raw_name

    nn = _normalize(canonical_name)
    indices = name_index.get(nn, [])

    if not indices:
        return MatchResult(status="NEW_CARD", pz_card=pz, canonical_name=canonical_name)

    if len(indices) == 1:
        single_entry = collection[indices[0]]
        # Rarity cross-check: if pack_sources says alt-art but the only collection
        # entry is base (or vice versa), this is a NEW variant not yet owned.
        if pz.set_code and pz.card_number is not None:
            ps_ref = pack_sources.get((pz.set_code, pz.card_number))
            # Only apply rarity cross-check when pack_sources confirms the card
            # identity — a set-numbering mismatch would give us a different card's
            # rarity (e.g. triple_star for "Charizard ex" at the Farfetch'd slot).
            if ps_ref and _normalize(ps_ref["card_name"]) == _normalize(canonical_name):
                rarity = normalize_rarity(ps_ref.get("rarity")) or ""
                is_pz_alt = rarity in RARE_PLUS_RARITIES
                entry_is_alt = "alt" in str(single_entry.get("variant", "")).lower().split()
                if is_pz_alt != entry_is_alt:
                    return MatchResult(status="NEW_CARD", pz_card=pz, canonical_name=canonical_name)
        return MatchResult(
            status="MATCHED",
            pz_card=pz,
            entry=single_entry,
            entry_index=indices[0],
            canonical_name=canonical_name,
        )

    # Exact-name shortcut: canonical_name may contain characters that normalize
    # identically to a sibling (e.g. Nidoran♀ and Nidoran♂ both → "nidoran").
    # If exactly one collection entry matches the canonical name verbatim, use it
    # directly rather than falling into the HP/rarity disambiguation path.
    if canonical_name:
        exact = [i for i in indices if collection[i].get("name") == canonical_name]
        if len(exact) == 1:
            return MatchResult(
                status="MATCHED",
                pz_card=pz,
                entry=collection[exact[0]],
                entry_index=exact[0],
                canonical_name=canonical_name,
            )

    # Step 0 (preferred): coord-exact match. Collection entries now carry
    # set_code/card_number, so when the PZ card's exact coord is present among the
    # same-name entries, match it directly. This is more reliable than the HP/rarity
    # heuristics below (legacy fallbacks for entries without coords) and correctly
    # pairs base vs alt-art prints when PZ returns BOTH (e.g. Glimmora B3A/45 base +
    # B3A/78 alt) — the base entry may lack an hp field, which would otherwise let
    # the alt entry wrongly absorb both PZ records.
    if pz.set_code and pz.card_number is not None:
        coord_idx = [i for i in indices
                     if str(collection[i].get("set_code") or "").upper() == pz.set_code
                     and collection[i].get("card_number") == pz.card_number]
        if len(coord_idx) == 1:
            return MatchResult(
                status="MATCHED",
                pz_card=pz,
                entry=collection[coord_idx[0]],
                entry_index=coord_idx[0],
                canonical_name=canonical_name,
            )

    # Multiple variants — try HP then rarity to disambiguate
    if pz.set_code and pz.card_number is not None:
        # Step A: HP from external_card_reference
        ext_records = ext_ref.get(nn, [])
        target_hp: int | None = None
        for er in ext_records:
            if (str(er.get("set_code", "")).upper() == pz.set_code
                    and er.get("number") == pz.card_number):
                target_hp = er.get("hp")
                break

        if target_hp is not None:
            hp_matches = [i for i in indices if collection[i].get("hp") == target_hp]
            if len(hp_matches) == 1:
                return MatchResult(
                    status="MATCHED",
                    pz_card=pz,
                    entry=collection[hp_matches[0]],
                    entry_index=hp_matches[0],
                    canonical_name=canonical_name,
                )
            if hp_matches:
                indices = hp_matches  # narrow to same-HP bucket before rarity step

        # Step B: rarity-based alt-art disambiguation
        ps_ref = pack_sources.get((pz.set_code, pz.card_number))
        if ps_ref and _normalize(ps_ref["card_name"]) == _normalize(canonical_name):
            rarity = normalize_rarity(ps_ref.get("rarity")) or ""
            is_alt = rarity in RARE_PLUS_RARITIES
            alt_idx = [i for i in indices
                       if "alt" in str(collection[i].get("variant", "")).lower().split()]
            reg_idx = [i for i in indices
                       if "alt" not in str(collection[i].get("variant", "")).lower().split()]
            if is_alt and len(alt_idx) == 1:
                return MatchResult(
                    status="MATCHED",
                    pz_card=pz,
                    entry=collection[alt_idx[0]],
                    entry_index=alt_idx[0],
                    canonical_name=canonical_name,
                )
            if not is_alt and len(reg_idx) == 1:
                return MatchResult(
                    status="MATCHED",
                    pz_card=pz,
                    entry=collection[reg_idx[0]],
                    entry_index=reg_idx[0],
                    canonical_name=canonical_name,
                )

    # Disambiguation failed
    return MatchResult(
        status="AMBIGUOUS",
        pz_card=pz,
        canonical_name=canonical_name,
    )


# ---------------------------------------------------------------------------
# Collection.json in-place editor
# ---------------------------------------------------------------------------

def _find_count_lines(raw: str, collection: list[dict]) -> dict[int, int]:
    """
    Return {entry_index → line_number_of_count_field} (0-based line numbers).

    Walks the raw JSONC text, tracking object boundaries and matching each
    "name" field to the corresponding collection entry to locate its "count" line.
    """
    lines = raw.split("\n")
    # Build a lookup: normalized_name + hp (to distinguish variants) → entry_index
    # Use a list because we match in order of appearance in the file
    entry_signatures: list[tuple[str, int | None, int]] = []
    for i, e in enumerate(collection):
        nn = _normalize(e.get("name", ""))
        hp = e.get("hp")
        entry_signatures.append((nn, hp, i))

    count_line: dict[int, int] = {}  # entry_index → line number

    depth = 0
    current_name: str | None = None
    current_hp: int | None = None
    # Track which signatures have been matched (in order) to handle duplicates
    matched_set: set[int] = set()

    for lineno, line in enumerate(lines):
        stripped = re.sub(r"//[^\n]*", "", line)  # strip inline comment
        depth += stripped.count("{") - stripped.count("}")

        # Detect "name": "..." on this line
        m_name = re.search(r'"name"\s*:\s*"([^"]+)"', stripped)
        if m_name:
            current_name = m_name.group(1).strip()
            current_hp = None  # reset so previous card's HP can't bleed into this entry

        m_hp = re.search(r'"hp"\s*:\s*(\d+)', stripped)
        if m_hp:
            current_hp = int(m_hp.group(1))

        # Detect "count": N on this line
        m_count = re.search(r'"count"\s*:\s*(\d+)', stripped)
        if m_count and current_name is not None:
            nn = _normalize(current_name)
            # Find the matching signature (in-order, first unmatched)
            for sig_nn, sig_hp, sig_idx in entry_signatures:
                if sig_idx in matched_set:
                    continue
                if sig_nn != nn:
                    continue
                # If both have HP, require match; otherwise accept
                if sig_hp is not None and current_hp is not None and sig_hp != current_hp:
                    continue
                count_line[sig_idx] = lineno
                matched_set.add(sig_idx)
                break
            # Reset HP after binding to avoid bleeding into next object
            if depth == 1:
                current_name = None
                current_hp = None

    return count_line


def apply_count_changes(
    raw: str, changes: list[CountChange], collection: list[dict]
) -> tuple[str, list[CountChange]]:
    """
    Apply count changes to the raw JSONC text in-place.
    Replacements are made from bottom to top so line numbers stay valid.

    Returns (edited_text, skipped) where skipped is any changes that could not
    be located in the file. Callers must treat a non-empty skipped list as an error.
    """
    count_lines = _find_count_lines(raw, collection)
    lines = raw.split("\n")

    indexed_changes = []
    skipped: list[CountChange] = []
    for ch in changes:
        lineno = count_lines.get(ch.entry_index)
        if lineno is None:
            skipped.append(ch)
            continue
        indexed_changes.append((lineno, ch))

    # Sort bottom-to-top so earlier line numbers stay valid during replacement
    indexed_changes.sort(key=lambda x: x[0], reverse=True)

    for lineno, ch in indexed_changes:
        line = lines[lineno]
        new_line = re.sub(
            r'("count"\s*:\s*)(\d+)',
            lambda m: f"{m.group(1)}{ch.new_count}",
            line,
            count=1,
        )
        lines[lineno] = new_line

    return "\n".join(lines), skipped


def update_meta(raw: str, new_total: int) -> str:
    """Update meta.total_cards and meta.last_updated in the raw text."""
    today = date.today().isoformat()
    # Update total_cards (in meta block — first occurrence)
    raw = re.sub(
        r'("total_cards"\s*:\s*)(\d+)',
        lambda m: f"{m.group(1)}{new_total}",
        raw,
        count=1,
    )
    # Update last_updated
    raw = re.sub(
        r'("last_updated"\s*:\s*)"[^"]+"',
        lambda m: f'{m.group(1)}"{today}"',
        raw,
        count=1,
    )
    return raw


# ---------------------------------------------------------------------------
# Auto-add new cards from ext_ref
# ---------------------------------------------------------------------------

_STAGE_MAP: dict[str, tuple[int, str]] = {
    "Basic":   (0, "Basic"),
    "Stage 1": (1, "Stage 1"),
    "Stage 2": (2, "Stage 2"),
}


def build_auto_entry(
    mr: "MatchResult",
    ext_ref: dict,
    card_meta: dict | None = None,
    resolver=None,
) -> dict:
    """Build a collection entry for a NEW_CARD match.

    Lookup priority:
    1. ext_ref exact match on (set_code, card_number) — best metadata.
    2. ext_ref records[0] — same card name, different set; hp/stage may differ.
    3. card_meta lookup — card_type/subtype from B-set ext_ref or owned collection.
    4. " ex" suffix heuristic — always a Pokemon EX card in TCGP.
    5. Assume Pokemon — all remaining cards; warn so ext_ref can be populated.

    Never returns None: one of the five paths always produces a valid entry.
    Callers should check that canonical_name is non-empty before calling.

    If `resolver` (a coord_resolver.CoordResolver) is given, the coord is
    cross-validated (PZ # → pack_sources → TCGdex/Limitless) so a new card's
    set_code is corrected at add time — PZ mislabels the A4b "Deluxe Pack: ex"
    set as A1/A2/A3/A4 while keeping the right number. Falls back to the raw PZ
    coord when no resolver is supplied or the coord can't be confirmed.
    """
    nn = _normalize(mr.canonical_name)
    pz = mr.pz_card
    records = ext_ref.get(nn, [])

    def _with_coords(e: dict) -> dict | None:
        """Inject the (cross-validated, if a resolver is given) coord from PZ.

        Returns None when the resolver finds a genuine conflict (two independent
        sources disagree on what card lives at this coord) — the caller must route
        the card to the review queue rather than auto-adding with a wrong coord.
        """
        sc_code, cn = pz.set_code, pz.card_number
        if resolver is not None and pz.card_number is not None:
            rc = resolver.resolve(mr.canonical_name, pz.set_code, pz.card_number)
            if rc.confidence == "conflict":
                print(f"  CONFLICT: {mr.canonical_name} {pz.set_code}/{pz.card_number} "
                      f"— independent sources disagree; routed to review queue",
                      file=sys.stderr)
                return None  # caller routes to still_new
            if rc.confidence in ("confirmed", "single-source") and rc.set_code:
                if (rc.set_code, rc.card_number) != (pz.set_code, pz.card_number):
                    print(f"  COORD: {mr.canonical_name} {pz.set_code}/{pz.card_number} "
                          f"→ {rc.set_code}/{rc.card_number} (cross-validated, {rc.confidence})",
                          file=sys.stderr)
                sc_code, cn = rc.set_code, rc.card_number
                if rc.rarity and not e.get("rarity"):
                    e["rarity"] = rc.rarity
            else:
                print(f"  WARN: coord for {mr.canonical_name} {pz.set_code}/{pz.card_number} "
                      f"unconfirmed ({rc.confidence}) — using raw PZ coord", file=sys.stderr)
        if sc_code:
            e["set_code"] = sc_code
        if cn is not None:
            e["card_number"] = cn
        # Backfill Pokémon type from card_reference (TCGdex-backed authority) when ext_ref
        # left it null — A-series ext_ref has no types, so a freshly-synced A-series card
        # would otherwise be type-less until the pipeline's assign step runs.
        if (e.get("card_type") == "Pokemon" and not e.get("type")
                and resolver is not None and sc_code and cn is not None):
            ref_rec = resolver.ref_by_coord.get((str(sc_code).upper(), cn))
            ref_type = ref_rec.get("pokemon_type") if ref_rec else None
            if ref_type:
                e["type"] = ref_type
        return e

    if records:
        best = next(
            (r for r in records
             if r.get("set_code", "").upper() == (pz.set_code or "").upper()
             and r.get("number") == pz.card_number),
            None,
        )
        if best is None:
            best = records[0]
            if best.get("set_code", "").upper() != (pz.set_code or "").upper():
                print(
                    f"  INFO: using {best.get('set_code')} metadata for {mr.canonical_name!r} "
                    f"(PZ {pz.set_code} not in ext_ref — hp/stage sourced from different set)",
                    file=sys.stderr,
                )

        entry: dict = {"name": mr.canonical_name, "count": pz.count}
        cat = best.get("card_category", "")
        if cat == "Pokemon":
            entry["card_type"] = "Pokemon"
            ptype = best.get("pokemon_type")
            if ptype and ptype != "None":
                entry["type"] = ptype
            stage_str = best.get("stage", "")
            if stage_str in _STAGE_MAP:
                s, sl = _STAGE_MAP[stage_str]
                entry["stage"] = s
                entry["stage_label"] = sl
            hp = best.get("hp")
            if hp is not None:
                entry["hp"] = hp
        elif not cat:
            # Blank ext_ref category — warn and default to Pokemon (safer than Trainer;
            # run scripts/fetch_ext_ref.py to populate the missing card_category).
            print(
                f"  WARN: blank card_category in ext_ref for {mr.canonical_name!r} "
                f"— defaulting to Pokemon. Run fetch_ext_ref.py to fix.",
                file=sys.stderr,
            )
            entry["card_type"] = "Pokemon"
            ptype = best.get("pokemon_type")
            if ptype and ptype != "None":
                entry["type"] = ptype
            stage_str = best.get("stage", "")
            if stage_str in _STAGE_MAP:
                s, sl = _STAGE_MAP[stage_str]
                entry["stage"] = s
                entry["stage_label"] = sl
            hp = best.get("hp")
            if hp is not None:
                entry["hp"] = hp
        else:
            entry["card_type"] = "Trainer"
            subtype = TRAINER_SUBTYPE_MAP.get(cat)
            if subtype:
                entry["trainer_subtype"] = subtype
            else:
                print(
                    f"  WARN: unknown trainer category {cat!r} for {mr.canonical_name!r} "
                    f"— add to TRAINER_SUBTYPE_MAP",
                    file=sys.stderr,
                )
        # is_ex is intentionally not written: it's no longer a tracked collection
        # field (EX status derives from the " ex" name suffix via is_ex_from_name,
        # and assign_collection_coords strips any stray is_ex).
        return _with_coords(entry)

    # No ext_ref record — fall back to name-based inference.

    # Heuristic 1: " ex" suffix is unambiguous in TCGP.
    if is_ex_from_name(mr.canonical_name):
        return _with_coords({
            "name": mr.canonical_name,
            "count": pz.count,
            "card_type": "Pokemon",
        })

    # Heuristic 2: card_meta lookup (B-set ext_ref + owned collection entries).
    if card_meta and nn in card_meta:
        known = card_meta[nn]
        entry = {
            "name": mr.canonical_name,
            "count": pz.count,
            "card_type": known["card_type"],
        }
        if known["card_type"] == "Pokemon":
            if known.get("type"):
                entry["type"] = known["type"]
        else:
            if known.get("trainer_subtype"):
                entry["trainer_subtype"] = known["trainer_subtype"]
        return _with_coords(entry)

    # Heuristic 3: assume Pokemon. In TCGP, all known Trainer names are covered by
    # card_meta (from B-set ext_ref + collection.json). Anything not found there is
    # overwhelmingly a Pokemon species. The caller is responsible for logging a
    # summary; per-card logging at this site would be too noisy for bulk syncs.
    return _with_coords({
        "name": mr.canonical_name,
        "count": pz.count,
        "card_type": "Pokemon",
    })


def append_entries_to_collection(raw: str, entries: list[dict]) -> str:
    """Append new card entries to the collection array in raw JSONC text."""
    blocks = []
    for e in entries:
        lines = json.dumps(e, indent=2).splitlines()
        blocks.append("\n".join("    " + line for line in lines))
    insertion = ",\n".join(blocks)
    pattern = r'(?<=\})\n(\s*\])\n(\})\s*$'
    if not re.search(pattern, raw):
        raise RuntimeError(
            "collection.json append point not found — "
            r"expected closing structure: }\n]\n}. "
            "Check for trailing whitespace or extra blank lines at end of file."
        )
    return re.sub(
        pattern,
        lambda m: f",\n{insertion}\n{m.group(1)}\n{m.group(2)}",
        raw,
    )


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def write_review_queue(
    new_cards: list[MatchResult],
    missing_from_pz: list[dict],
) -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    # Build a lookup of previous consecutive_missing counts so we can increment them.
    prev_consecutive: dict[str, int] = {}
    if REVIEW_QUEUE.exists():
        try:
            prev_q = json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
            for entry in prev_q.get("missing_from_pz", []):
                name = entry.get("name")
                if name:
                    prev_consecutive[name] = entry.get("consecutive_missing", 0)
        except Exception:
            print(
                "  WARN: could not read previous sync_review_queue.json — "
                "consecutive_missing counts reset to 1.",
                file=sys.stderr,
            )
    queue = {
        "generated_at": date.today().isoformat(),
        "resolved": not bool(new_cards),
        "new_cards": [
            {
                "set_code": r.pz_card.set_code,
                "card_number": r.pz_card.card_number,
                "raw_name": r.pz_card.raw_name,
                "canonical_name": r.canonical_name,
                "count": r.pz_card.count,
                "action_needed": "Add this card to collection.json manually",
            }
            for r in new_cards
        ],
        "ambiguous_matches": [],
        "missing_from_pz": [
            {
                "name": e.get("name"),
                "current_count": e.get("count"),
                "consecutive_missing": prev_consecutive.get(e.get("name", ""), 0) + 1,
                "note": "Not found in Pokemon Zone response — count NOT zeroed",
            }
            for e in missing_from_pz
        ],
    }
    REVIEW_QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def load_review_queue() -> dict:
    if not REVIEW_QUEUE.exists():
        return {"resolved": True}
    try:
        return json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
    except Exception:
        return {"resolved": True}


def review_queue_is_unresolved(q: dict) -> bool:
    return not q.get("resolved", True)


# ---------------------------------------------------------------------------
# Validation subprocess
# ---------------------------------------------------------------------------

def pair_dual_location_entries(
    collection_entries: list[dict],
    entry_pz_total: dict[int, int],
    entry_pz_coords: dict[int, set],
    matched_indices: set[int],
    link_orig: dict[tuple, tuple],
) -> set[int]:
    """Pair dual-location split entries so neither side is reset or flagged stale.

    A dual-location card (A4b "Deluxe Pack: ex" reprint) is ONE PZ record but TWO
    collection entries after reconcile splits it: the original-set slot (1st copy)
    and the A4b slot (2nd+ copies). The 1:1 matcher lands the record on one entry,
    which would reset it to the full PZ count and flag the sibling as missing
    (eventually stale-removing it). When the pair's combined count already equals
    the PZ count, both entries are correct: leave counts alone, don't flag the
    sibling. When they don't sum (a genuinely new copy), the normal count update +
    reconcile re-split applies.

    Mutates entry_pz_total in place; returns the set of paired sibling indices.
    """
    paired_siblings: set[int] = set()
    if not link_orig:
        return paired_siblings

    a4b_by_orig: dict[tuple, list] = {}
    for a, o in link_orig.items():
        a4b_by_orig.setdefault(o, []).append(a)

    def _coord(e: dict) -> tuple:
        return (str(e.get("set_code") or "").upper(), e.get("card_number"))

    for idx in list(entry_pz_total):
        e = collection_entries[idx]
        c = _coord(e)
        partners = a4b_by_orig.get(c) or ([link_orig[c]] if c in link_orig else [])
        if not partners:
            continue
        # Only pair when every PZ coord aggregated onto this entry belongs to THIS
        # dual-location pair — a copy from any other set is a real extra copy the
        # reset below would silently discard. The valid coords are the pair's own
        # two (original + A4b) PLUS the hybrid stamp Pokémon Zone actually emits:
        # the original set code with the A4b card number (e.g. Cubone A1/194 for
        # original A1/151 + A4b/194). Omitting the hybrid skips pairing on every
        # real PZ sync and double-counts the A4b half.
        # (See test_sync.py::test_pairing_fires_on_pz_hybrid_stamp.)
        allowed = {c} | set(partners)
        if c in a4b_by_orig:                      # entry is the original slot
            allowed |= {(c[0], p[1]) for p in partners}
        else:                                     # entry is the A4b slot
            allowed |= {(p[0], c[1]) for p in partners}
        if not entry_pz_coords.get(idx, set()) <= allowed:
            continue
        for j, s in enumerate(collection_entries):
            if j in matched_indices or j in paired_siblings:
                continue
            if _normalize(s.get("name", "")) != _normalize(e.get("name", "")):
                continue
            if _coord(s) in partners and \
                    e.get("count", 0) + s.get("count", 0) == entry_pz_total[idx]:
                entry_pz_total[idx] = e.get("count", 0)
                paired_siblings.add(j)
                break
    return paired_siblings


def run_validation(expected_total: int | None = None) -> bool:
    cmd = [sys.executable, "scripts/validate_current_collection.py"]
    if expected_total is not None:
        cmd += ["--expected-total", str(expected_total)]
    r1 = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r1.returncode != 0:
        print("  VALIDATION FAILED:", file=sys.stderr)
        print(r1.stdout, file=sys.stderr)
        print(r1.stderr, file=sys.stderr)
        return False

    r2 = subprocess.run(
        [sys.executable, "scripts/normalize_current_collection.py"],
        capture_output=True, text=True, cwd=ROOT
    )
    if r2.returncode != 0:
        print("  NORMALIZE FAILED:", file=sys.stderr)
        print(r2.stdout, file=sys.stderr)
        print(r2.stderr, file=sys.stderr)
        return False

    return True


# ---------------------------------------------------------------------------
# Diff printer
# ---------------------------------------------------------------------------

def print_diff(
    changes: list[CountChange],
    new_cards: list[MatchResult],
    missing: list[dict],
) -> None:
    today = date.today().isoformat()
    print(f"\nSYNC DIFF — {today}")
    print("-" * 50)

    if changes:
        print(f"  Count updates ({len(changes)}):")
        for ch in changes:
            name = ch.entry.get("name", "?")
            variant = ch.entry.get("variant", "")
            tag = f" [{variant}]" if variant else ""
            print(f"    {name}{tag}: {ch.old_count} → {ch.new_count}")
    else:
        print("  Count updates: none")

    if new_cards:
        print(f"\n  New cards — not in collection.json ({len(new_cards)}) [review required]:")
        for r in new_cards:
            sc = r.pz_card.set_code or "?"
            cn = r.pz_card.card_number or "?"
            print(f"    [{sc}/{cn}] {r.canonical_name or r.pz_card.raw_name}  ×{r.pz_card.count}")

    if missing:
        print(f"\n  Missing from Pokemon Zone ({len(missing)}) [counts NOT changed]:")
        for e in missing:
            print(f"    {e.get('name')}  (current count: {e.get('count')})")

    print("-" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_pz_client():
    """Load pokemon_zone_client as a sibling module (avoids package import issues)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pokemon_zone_client",
        Path(__file__).parent / "pokemon_zone_client.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_curl_from_clipboard() -> str:
    """Return clipboard contents if they look like a cURL command, else ''."""
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            text = result.stdout.strip()
            if text.startswith("curl ") or text.startswith("curl'"):
                return text
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            if text.startswith("curl ") or text.startswith("curl'"):
                return text
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _read_curl_from_stdin() -> str:
    """Print instructions and read a multi-line cURL paste from stdin."""
    print()
    print("=" * 65)
    print("  CURL IMPORT — paste your cURL command, then press Ctrl+D")
    print("=" * 65)
    print()
    print("Steps:")
    print("  1. Open  https://www.pokemon-zone.com/collection-tracker/")
    print("     in your browser (must be logged in)")
    print("  2. Open DevTools: F12  or  Cmd+Option+I")
    print("  3. Click the 'Network' tab, then 'Fetch/XHR'")
    print("  4. Reload the page (Cmd+R or F5)")
    print("  5. Wait for your cards to appear")
    print("  6. In the Network tab, look for a large request")
    print("     (50 KB+, URL contains 'card', 'collection', or 'inventory')")
    print("  7. Right-click that request → 'Copy' → 'Copy as cURL'")
    print("  8. Paste below, then press Ctrl+D (Mac/Linux) or Ctrl+Z+Enter (Windows):")
    print()
    try:
        curl_str = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return ""
    return curl_str.strip()


def _get_curl() -> str:
    """Try clipboard first; if no cURL found there, fall back to stdin prompt."""
    clipboard = _read_curl_from_clipboard()
    if clipboard:
        print()
        print("=" * 65)
        print("  CURL IMPORT — reading cURL from clipboard")
        print("=" * 65)
        # Show just the URL so user can confirm it's the right request
        url_match = re.search(r"curl\s+['\"]?(https?://[^\s'\"]+)", clipboard)
        if url_match:
            print(f"  URL: {url_match.group(1)}")
        print()
        return clipboard
    return _read_curl_from_stdin()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync collection.json from Pokemon Zone.")
    parser.add_argument("--har-import",  metavar="FILE",
                        help="Import collection from a browser HAR file (no auth stored; run --curl-import afterwards for ongoing syncs)")
    parser.add_argument("--json-import", metavar="FILE",
                        help="Import pre-normalized JSON from the browser bookmarklet (fastest; no auth stored)")
    parser.add_argument("--curl-import", action="store_true",
                        help="Paste a browser DevTools cURL to set up / refresh auth (Cloudflare-safe)")
    parser.add_argument("--curl-file",   metavar="FILE",
                        help="Read cURL from a file instead of stdin (alternative to --curl-import)")
    parser.add_argument("--login",       action="store_true",
                        help="Headed Playwright browser login (fallback; may hit Cloudflare)")
    parser.add_argument("--discover",    action="store_true",
                        help="Print all Playwright-intercepted network responses and exit")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Show diff only, no writes")
    parser.add_argument("--force",       action="store_true",
                        help="Apply updates even if review queue has items")
    parser.add_argument("--no-fetch",    action="store_true",
                        help="Skip live coord cross-validation for new cards (use caches only)")
    args = parser.parse_args()

    # ── Load sibling client module ────────────────────────────────────────
    pz = _load_pz_client()
    AUTH_CACHE          = pz.AUTH_CACHE
    browser_session     = ROOT / ".browser_session"

    # ── Phase 0: Pre-flight ───────────────────────────────────────────────

    # --json-import: read pre-normalized JSON from the browser bookmarklet
    if args.json_import:
        json_path = Path(args.json_import)
        if not json_path.exists():
            print(f"ERROR: file not found: {json_path}", file=sys.stderr)
            return 1
        print(f"Importing collection from bookmarklet JSON: {json_path.name}")
        try:
            raw_cards = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: could not read {json_path}: {e}", file=sys.stderr)
            return 1
        if not isinstance(raw_cards, list) or not raw_cards:
            print("ERROR: JSON file must contain a non-empty array of card objects.", file=sys.stderr)
            return 1
        print(f"  Loaded {len(raw_cards)} card records.")

    # --har-import: parse a HAR file directly (one-shot; no auth stored)
    elif args.har_import:
        print(f"Importing collection from HAR file: {args.har_import}")
        try:
            raw_cards, _cache = pz.import_har(args.har_import)
        except (ValueError, FileNotFoundError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1
        print()
        print("NOTE: HAR import does not save auth credentials (browser cookies are")
        print("      not included in HAR exports). For automatic future syncs, run:")
        print("       python3 scripts/sync_collection.py --curl-import")
        print("      Go to pokemon-zone.com/collection-tracker/ → DevTools → Network →")
        print("      right-click the /api/players/mine/ request → Copy as cURL.")
        print()

    # --curl-file: read cURL from a file (alternative to --curl-import + paste)
    elif args.curl_file:
        curl_path = Path(args.curl_file)
        if not curl_path.exists():
            print(f"ERROR: file not found: {curl_path}", file=sys.stderr)
            return 1
        curl_str = curl_path.read_text(encoding="utf-8").strip()
        if not curl_str:
            print("ERROR: curl file is empty.", file=sys.stderr)
            return 1
        print(f"Reading cURL from {curl_path} ...")
        print("Parsing cURL and fetching collection...")
        try:
            raw_cards, _cache = pz.import_curl_auth(curl_str)
        except (ValueError, pz.APIDiscoveryFailedError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1

    # --curl-import: read cURL (clipboard first, then stdin), save auth, sync
    elif args.curl_import:
        curl_str = _get_curl()
        if not curl_str:
            return 1
        print("\nParsing cURL and fetching collection...")
        try:
            raw_cards, _cache = pz.import_curl_auth(curl_str)
        except (ValueError, pz.APIDiscoveryFailedError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1

    # Normal headless sync using stored auth or Playwright session
    else:
        # Check auth availability before doing anything else
        has_stored_auth  = AUTH_CACHE.exists()
        has_browser_sess = browser_session.exists()

        if not has_stored_auth and not has_browser_sess and not args.login and not args.discover:
            print("ERROR: No stored auth and no browser session found.", file=sys.stderr)
            print()
            print("First-time setup (recommended — avoids Cloudflare):")
            print("  python3 scripts/sync_collection.py --curl-import")
            print()
            print("Alternative (may hit Cloudflare CAPTCHA loop):")
            print("  python3 scripts/sync_collection.py --login")
            return 1

        # ── Phase 1: Fetch from Pokemon Zone ─────────────────────────────
        print("Fetching collection from Pokemon Zone...")
        try:
            raw_cards, _cache = pz.fetch_collection(login=args.login, discover=args.discover)
        except (pz.AuthNotFoundError, pz.SessionNotFoundError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        except pz.AuthExpiredError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        except (pz.SessionExpiredError, pz.APIDiscoveryFailedError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

        if args.discover:
            return 0  # already printed by fetch_collection

    if not raw_cards:
        print("ERROR: No card records returned from Pokemon Zone.", file=sys.stderr)
        return 1

    # ── Review queue gate (all modes except discover/dry-run/force) ───────
    if not args.force and not args.discover and not args.dry_run:
        q = load_review_queue()
        if review_queue_is_unresolved(q):
            n_new = len(q.get("new_cards", []))
            print(f"BLOCKED: Review queue has {n_new} unresolved new card(s).")
            print(f"  File: {REVIEW_QUEUE}")
            print("  Resolve the items or run with --force to skip this check.")
            return 3

    print(f"  Fetched {len(raw_cards)} card records from Pokemon Zone.")

    # ── Load collection.json and reference data ───────────────────────────
    raw_text, collection_data = load_collection()
    collection_entries: list[dict] = collection_data.get("collection", [])
    print("Loading reference data...")
    pack_sources = load_pack_sources()
    ext_ref      = load_ext_ref()

    # ── Phase 2: Normalize PZ records ────────────────────────────────────
    pz_cards: list[PZCard] = []
    skipped = 0
    for rec in raw_cards:
        pzc = normalize_pz_record(rec)
        if pzc is None:
            skipped += 1
            continue
        pz_cards.append(pzc)

    if skipped:
        print(f"  Skipped {skipped} records with count=0 or missing name.")

    # ── Phase 3: Match ────────────────────────────────────────────────────
    print(f"  Matching {len(pz_cards)} PZ cards to {len(collection_entries)} collection entries...")
    try:
        results = match_pz_cards(pz_cards, collection_entries, pack_sources, ext_ref)
    except RuntimeError as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        print("Sync cannot proceed. Add disambiguation data to reference files and retry.", file=sys.stderr)
        return 1

    matched   = [r for r in results if r.status == "MATCHED"]
    new_cards = [r for r in results if r.status == "NEW_CARD"]

    matched_indices = {r.entry_index for r in matched if r.entry_index is not None}

    # ── Phase 4: Compute diff ─────────────────────────────────────────────
    # Aggregate counts: the same card may appear in multiple sets in PZ
    # (e.g. Shroomish in B2 + B3); sum all copies into one collection entry.
    entry_pz_total: dict[int, int] = {}
    entry_pz_coords: dict[int, set] = {}
    for r in matched:
        idx = r.entry_index
        entry_pz_total[idx] = entry_pz_total.get(idx, 0) + r.pz_card.count
        entry_pz_coords.setdefault(idx, set()).add(
            (str(r.pz_card.set_code or "").upper(), r.pz_card.card_number))

    # ── Dual-location pairing (see pair_dual_location_entries) ───────────
    link_orig: dict[tuple, tuple] = {}
    if REPRINT_LINKS_JSON.exists():
        for l in json.loads(REPRINT_LINKS_JSON.read_text(encoding="utf-8")).get("links", []):
            link_orig[(str(l["a4b"][0]).upper(), int(l["a4b"][1]))] = (
                str(l["original"][0]).upper(), int(l["original"][1]))
    paired_siblings = pair_dual_location_entries(
        collection_entries, entry_pz_total, entry_pz_coords, matched_indices, link_orig)

    missing_from_pz = [
        e for i, e in enumerate(collection_entries)
        if i not in matched_indices and i not in paired_siblings
    ]

    if missing_from_pz:
        print(
            f"  WARNING: {len(missing_from_pz)} collection entries not returned by PZ "
            f"— counts unchanged (check sync_review_queue.json)",
            file=sys.stderr,
        )

    # Split-gap detection: when PZ maps copies from >1 DISTINCT coord onto a single
    # entry, those copies are different printings that the per-coord model wants as
    # separate entries — but in-place count editing can only aggregate them here.
    # Surface it so the user runs the per-coord reconcile (which splits + cross-validates).
    multi_coord = {i: cs for i, cs in entry_pz_coords.items() if len(cs) > 1}
    if multi_coord:
        names = sorted({collection_entries[i].get("name", "?") for i in multi_coord})
        shown = ", ".join(names[:5]) + ("…" if len(names) > 5 else "")
        print(f"  NOTE: {len(multi_coord)} entry(ies) received copies from multiple coords "
              f"({shown}) — counts aggregated onto one entry. Run "
              f"`python3 scripts/reconcile_coords_from_pz.py --apply` to split per printing.",
              file=sys.stderr)

    changes: list[CountChange] = []
    for idx, new_count in entry_pz_total.items():
        entry = collection_entries[idx]
        old_count = entry.get("count", 0)
        if old_count != new_count:
            changes.append(CountChange(
                entry=entry,
                entry_index=idx,
                old_count=old_count,
                new_count=new_count,
            ))

    print_diff(changes, new_cards, missing_from_pz)

    if args.dry_run:
        print("DRY RUN — no changes written.")
        return 0

    # ── Phase 4b: Auto-add new cards ─────────────────────────────────────
    card_meta = build_card_meta(ext_ref, collection_entries)
    auto_added: list[dict] = []
    still_new: list[MatchResult] = []
    n_assumed = 0

    # Cross-validate new-card coords (corrects PZ A4b set-mislabels at add time).
    # Best-effort: if the resolver can't load, fall back to raw PZ coords.
    resolver = None
    if new_cards:
        try:
            from coord_resolver import CoordResolver
            resolver = CoordResolver(fetch=not args.no_fetch)
        except Exception as e:
            print(f"  WARN: coord cross-validation unavailable ({e}); using raw PZ coords",
                  file=sys.stderr)

    _ALT_RARITIES = RARE_PLUS_RARITIES

    def _mr_is_alt(mr: MatchResult) -> bool:
        """Return True if this NEW_CARD maps to an alt-rarity slot in pack_sources."""
        pz_c = mr.pz_card
        if not (pz_c.set_code and pz_c.card_number is not None):
            return False
        ps_r = pack_sources.get((pz_c.set_code, pz_c.card_number))
        return bool(
            ps_r
            and _normalize(ps_r["card_name"]) == _normalize(mr.canonical_name or "")
            and normalize_rarity(ps_r.get("rarity")) in _ALT_RARITIES
        )

    # Merge duplicate NEW_CARD results for the same canonical name AND rarity tier.
    # Can occur when PZ returns the same new card from multiple set records
    # (e.g. cross-set parallels); sum counts so only one entry is appended.
    # Key includes "|alt" vs "|base" so a base Bulbasaur and an alt-art Bulbasaur
    # get separate entries — they require separate collection rows.
    merged_new: dict[str, MatchResult] = {}
    for mr in new_cards:
        if not mr.canonical_name:
            # Blank PZ name: try to recover from card_reference using coord.
            # Reuse resolver.ref_by_coord — already loaded from the same file.
            pz_c = mr.pz_card
            recovered = None
            if resolver is not None and pz_c.set_code and pz_c.card_number is not None:
                ref_rec = resolver.ref_by_coord.get(
                    (str(pz_c.set_code).upper(), pz_c.card_number)
                )
                if ref_rec and ref_rec.get("confidence") in ("confirmed", "single"):
                    recovered = ref_rec.get("name") or None
            if recovered:
                print(f"  RECOVER: blank PZ name at {pz_c.set_code}/{pz_c.card_number} "
                      f"→ {recovered!r} (card_reference)", file=sys.stderr)
                mr = MatchResult(
                    status=mr.status, pz_card=mr.pz_card, canonical_name=recovered
                )
            else:
                still_new.append(mr)
                continue
        key = mr.canonical_name.lower() + ("|alt" if _mr_is_alt(mr) else "|base")
        if key in merged_new:
            prev = merged_new[key]
            merged_new[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(
                    set_code=prev.pz_card.set_code,
                    card_number=prev.pz_card.card_number,
                    raw_name=prev.pz_card.raw_name,
                    count=prev.pz_card.count + mr.pz_card.count,
                ),
                canonical_name=prev.canonical_name,
            )
        else:
            merged_new[key] = mr

    for mr in merged_new.values():
        nn = _normalize(mr.canonical_name)
        entry = build_auto_entry(mr, ext_ref, card_meta, resolver=resolver)
        if entry is None:
            # Genuine conflict: independent sources disagree on this coord.
            # Route to still_new so it surfaces in the review queue — do NOT auto-add.
            still_new.append(mr)
            continue
        # Tag alt-art entries so they're distinguishable from base copies.
        # Uses the same name-guard as the rarity cross-check to avoid mismatch slots.
        # IMPORTANT: look up the entry's RESOLVED coord (build_auto_entry may have
        # corrected a PZ set-mislabel, e.g. A4b-as-A1) — using the raw PZ coord here
        # would miss the alt-art rarity for exactly the mislabeled-set case.
        ec = entry.get("set_code")
        en = entry.get("card_number")
        if ec and en is not None:
            ps_r = pack_sources.get((str(ec).upper(), en))
            if (ps_r
                    and _normalize(ps_r["card_name"]) == _normalize(mr.canonical_name)
                    and normalize_rarity(ps_r.get("rarity")) in _ALT_RARITIES):
                entry["variant"] = "alt art"
        auto_added.append(entry)
        print(f"  Auto-adding: {mr.canonical_name} ×{mr.pz_card.count}")
        if (not ext_ref.get(nn)
                and not is_ex_from_name(mr.canonical_name)
                and not (card_meta and nn in card_meta)):
            n_assumed += 1

    if n_assumed:
        print(
            f"  WARN: {n_assumed} card(s) assumed card_type=Pokemon "
            f"(no ext_ref metadata — run scripts/fetch_ext_ref.py to add)",
            file=sys.stderr,
        )
    if resolver is not None:
        resolver.save()
    new_cards = still_new

    # ── Phase 4c: Mark stale entries for removal ─────────────────────────────
    # Two cases trigger removal:
    #   A) PZ returned an alt-art for the card but not the base copy → stale base
    #   B) Entry has been consecutively absent from PZ for >= threshold syncs
    #      (implies the card is no longer owned and PZ has stopped tracking it)
    # Read previous consecutive_missing counts from the existing review queue.
    prev_consecutive: dict[str, int] = {}
    if REVIEW_QUEUE.exists():
        try:
            prev_q = json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
            for entry in prev_q.get("missing_from_pz", []):
                name = entry.get("name")
                if name:
                    prev_consecutive[name] = entry.get("consecutive_missing", 0)
        except Exception:
            pass

    stale_base_indices: set[int] = set()
    alt_art_nns: set[str] = set()
    if auto_added:
        # Use .lower() (not _normalize) so Nidoran♀ and Nidoran♂ stay distinct.
        # Case A only fires when a NEW alt-art was auto-added this sync — a strong PZ-level
        # signal that the base is superseded. Extending to pre-existing matched alt-art would
        # fire Case A on any transient PZ failure, deleting a base with no threshold protection.
        alt_art_nns = {e["name"].lower() for e in auto_added if e.get("variant") == "alt art"}
    missing_nns = {_normalize(e.get("name", "")) for e in missing_from_pz}

    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue  # matched this run — keep
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue  # not missing from PZ this run
        name = e.get("name", "")
        has_variant = bool(e.get("variant"))
        # Case A: alt-art just added — only mark BASE entries stale (not alt-art variants).
        # Match by name.lower() (not _normalize) to keep Nidoran♀/♂ distinct.
        if not has_variant and name.lower() in alt_art_nns:
            stale_base_indices.add(i)
        # Case B: consecutively missing past threshold — applies to base entries and alt-art
        # variants only. Named-art entries (e.g. 'Tackle art', 'Flame Tail art') are never
        # returned by PZ as standalone records, so they would always hit this threshold and
        # be incorrectly deleted. Only remove them if they genuinely had no variant (base
        # cards) or were an "alt art" variant (which PZ does return).
        # prev_consecutive holds the count from the LAST run. This is the current Nth miss,
        # so stored == threshold-1 means this run is the Nth (threshold-th) consecutive miss.
        elif (e.get("variant") in (None, "alt art")
              and prev_consecutive.get(name, 0) >= _STALE_THRESHOLD - 1):
            stale_base_indices.add(i)

    if stale_base_indices:
        names = ", ".join(
            collection_entries[i].get("name", "?") for i in sorted(stale_base_indices)
        )
        print(f"  Removing {len(stale_base_indices)} stale entry(ies): {names}")
        # print_diff (above) reported missing_from_pz before stale filtering — clarify the delta.
        # Use exact name matching (same as stale_names below) to avoid _normalize() collapsing
        # distinct names like Nidoran♀ and Nidoran♂ into the same string.
        missing_raw_names = {e.get("name", "") for e in missing_from_pz if e.get("name")}
        n_stale_missing = sum(
            1 for i in stale_base_indices
            if collection_entries[i].get("name", "") in missing_raw_names
        )
        if n_stale_missing:
            print(f"  (Note: {n_stale_missing} of the 'missing' entries above are stale and will be removed)")

    # ── Phase 4e: Write review queue ─────────────────────────────────────
    # Exclude stale entries from the queue — they're about to be removed, so
    # reporting them as "missing" would be misleading and inflate consecutive counts.
    # Guard: only include non-empty names so "" never accidentally matches unnamed entries.
    stale_names = {
        collection_entries[i]["name"]
        for i in stale_base_indices
        if collection_entries[i].get("name")
    }
    queue_missing = [e for e in missing_from_pz if e.get("name") not in stale_names]
    # write_review_queue is deferred to after Phase 5 so that if stale removal aborts,
    # the stale entry's consecutive_missing count is NOT reset (the old queue survives intact).
    # Exception: the no-changes early-exit below calls it immediately since there's nothing to abort.

    # ── Phase 5: Apply in-place edits ────────────────────────────────────
    if not changes and not auto_added and not stale_base_indices:
        write_review_queue(new_cards, queue_missing)
        if new_cards and not args.force:
            print(f"\nReview queue written: {REVIEW_QUEUE}")
            print(f"  {len(new_cards)} new card(s) could not be auto-added — add to collection.json manually")
        if queue_missing:
            print(f"  INFO: {len(queue_missing)} entry/entries missing from PZ response (informational)")
        print("No count changes to apply.")
        # Return 2 only for genuinely NEW cards that need review, not for cards
        # that are merely absent from the PZ response (queue_missing — common for
        # promos/named-art cards that PZ perpetually omits on clean syncs).
        return 2 if new_cards else 0

    edited = raw_text

    if changes:
        print(f"Applying {len(changes)} count update(s) to collection.json...")
        counts = [e.get("count", 0) for e in collection_entries]
        for ch in changes:
            counts[ch.entry_index] = ch.new_count
        new_total = sum(counts)

        edited, skipped = apply_count_changes(raw_text, changes, collection_entries)
        if skipped:
            names = ", ".join(f"'{ch.entry.get('name')}'" for ch in skipped)
            print(f"  ERROR: could not locate count line(s) for: {names}", file=sys.stderr)
            print("  Aborting — collection.json not modified.", file=sys.stderr)
            return 1
    else:
        new_total = sum(e.get("count", 0) for e in collection_entries)

    if auto_added:
        print(f"Auto-adding {len(auto_added)} new card(s) to collection.json...")
        try:
            edited = append_entries_to_collection(edited, auto_added)
        except RuntimeError as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            print("  Aborting — collection.json not modified.", file=sys.stderr)
            return 1
        new_total += sum(e.get("count", 0) for e in auto_added)

    if stale_base_indices:
        # Remove stale base entries (indices into the original collection_entries list).
        # count changes and appended entries don't shift earlier positions, so indices
        # remain valid against the fully-edited parsed collection.
        # Try direct JSON parse first: safe when 'edited' is json.dumps output (no comments).
        # Fall back to strip_comments only if that fails (original JSONC with // comment lines).
        try:
            staged = json.loads(edited)
        except json.JSONDecodeError:
            try:
                staged = json.loads(strip_comments(edited))
            except json.JSONDecodeError as exc:
                print(f"  ERROR: could not parse collection for stale removal: {exc}", file=sys.stderr)
                print("  Aborting — collection.json not modified.", file=sys.stderr)
                return 1
        staged_coll = staged.get("collection", [])
        final_coll = [e for i, e in enumerate(staged_coll) if i not in stale_base_indices]
        new_total = sum(e.get("count", 0) for e in final_coll)
        staged["collection"] = final_coll
        edited = json.dumps(staged, indent=2, ensure_ascii=False)

    edited = update_meta(edited, new_total)

    COLLECTION_JSON.write_text(edited, encoding="utf-8")
    print(f"  collection.json updated. New total: {new_total}")

    # Write the review queue only AFTER collection.json is successfully written.
    # This ensures that if any Phase 5 step aborted (JSON parse failure, append error, etc.),
    # the old queue survives intact — stale entries retain their consecutive_missing counts
    # and removal is retried on the next sync rather than silently resetting the threshold.
    write_review_queue(new_cards, queue_missing)
    if new_cards and not args.force:
        print(f"\nReview queue written: {REVIEW_QUEUE}")
        print(f"  {len(new_cards)} new card(s) could not be auto-added — add to collection.json manually")
        print("Continuing to apply count updates for matched cards...")

    # ── Phase 6: Validate ─────────────────────────────────────────────────
    print("Validating...")
    if not run_validation(expected_total=new_total):
        print("ROLLBACK: restoring original collection.json", file=sys.stderr)
        COLLECTION_JSON.write_text(raw_text, encoding="utf-8")
        return 1

    print("  PASS — collection.json valid and normalized.")

    if new_cards or queue_missing:
        queue_data = json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
        n_new = len(queue_data.get("new_cards", []))
        n_mis = len(queue_data.get("missing_from_pz", []))
        print("\nReview queue summary:")
        if n_new:
            print(f"  {n_new} new card(s) needing manual addition:")
            for item in queue_data.get("new_cards", [])[:3]:
                sc = item.get("set_code", "?")
                cn = item.get("card_number", "?")
                name_display = item.get("canonical_name") or item.get("raw_name", "?")
                print(f"    [{sc}/{cn}] {name_display} ×{item.get('count', '?')}")
            if n_new > 3:
                print(f"    ... and {n_new - 3} more")
        if n_mis:
            print(f"  {n_mis} collection entries not found in PZ response")
        print(f"  Full details: {REVIEW_QUEUE}")
        print("\nExit 2: matched card counts updated; review queue requires attention.")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
