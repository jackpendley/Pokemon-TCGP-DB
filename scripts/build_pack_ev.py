#!/usr/bin/env python3
"""
Compute inferred pack expected value (EV) for all 24 PTCGP packs.

EV is based on:
  - pack_sources.json            — authoritative card pool per pack
  - collection_normalized.json   — owned cards and counts
  - pull_probability_model.json  — inferred per-slot pull probabilities
  - deck_recommendation_validation.json — target cards for deck completion

IMPORTANT: Slot rates are INFERRED from external sources, not verified in-app.
This output is analysis at inferred confidence — NOT a final recommendation.
Verify slot rates in the PTCGP app before acting on these rankings.

Inputs:
    data/current/collection_normalized.json
    data/current/pack_source_confidence_scores.json
    data/current/resolved_pack_sources.json           (optional — from resolve_ambiguous_pack_sources.py)
    data/reference/pull_probability_model.json
    data/reference/pack_sources.json
    data/exports/deck_recommendation_validation.json  (optional)

Outputs:
    data/current/pack_ev.json

Usage:
    python3 scripts/build_pack_ev.py
    python3 scripts/build_pack_ev.py --validate
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import RARE_PLUS_RARITIES, HOURGLASS_PER_PACK, norm_card_name as _norm_name, normalize_rarity

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON     = ROOT / "data" / "current"    / "collection_normalized.json"
PULL_MODEL_JSON     = ROOT / "data" / "reference"  / "pull_probability_model.json"
PACK_SOURCES_JSON   = ROOT / "data" / "reference"  / "pack_sources.json"
REPRINT_LINKS_JSON  = ROOT / "data" / "reference"  / "reprint_links.json"
# TODO(deck-ev): deck_recommendation_validation.json is read here but never written by any
# pipeline script — deck_target_ev is always 0 at runtime. When deck logic lands, wire up a
# producer for this file and switch the owned-count basis to name-level (decks mix sets).
DECK_VALIDATION_JSON = ROOT / "data" / "exports"   / "deck_recommendation_validation.json"
PZ_PACK_ODDS_JSON   = ROOT / "data" / "reference"  / "pz_pack_odds.json"

OUT_JSON = ROOT / "data" / "current"  / "pack_ev.json"

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "new_card":    1.0,   # first copy of any unseen unique card
    "copy_up_to_2": 0.4,  # second copy (can use 2 copies per deck)
    "deck_target": 2.0,   # max bonus for a deck-target card (scaled by copies still needed)
}

# Rarity bonus applied to owned==0 pulls (first copy).
# Values derived from pool-level slot probability averaged across packs:
#   bonus(r) = ln(p_uncommon / p_r), normalized so ultra_rare (crown) = 10.0.
# Pool probabilities (slot4+slot5+rare_pack, avg across packs) — unchanged from the
# symbol-tier model, only renamed:
#   uncommon=1.499/pack, rare=0.256, double_rare=0.083,
#   illustration_rare=0.130, super_rare=0.026, immersive=0.011, ultra_rare=0.002
# special_illustration_rare shares the ★★ tier with super_rare (same pull rate).
# shiny_rare / shiny_super_rare are premium pulls; bonuses interpolate by rarity rank
# between immersive (7.5) and ultra_rare (10.0).
RARITY_BONUS: dict[str, float] = {
    "ultra_rare":                10.0,   # 1-in-472 packs (crown)
    "shiny_super_rare":          9.2,    # ✷✷ — premium shiny ex
    "shiny_rare":                8.3,    # ✷
    "immersive":                 7.5,    # 1-in-89 (★★★)
    "special_illustration_rare": 6.2,    # ★★ rainbow — same tier as super_rare
    "super_rare":                6.2,    # 1-in-38 (★★)
    "double_rare":               4.4,    # 1-in-12
    "illustration_rare":         3.7,    # 1-in-8 (★)
    "rare":                      2.7,    # 1-in-4
    "uncommon":                  0.0,
    "common":                    0.0,
}

# Super Rare and Special Illustration Rare are the same ★★ pull-rate tier (only the art
# differs). For pull-probability math they share the super_rare slot rate and a combined
# pool count; this maps a card's rarity to its probability tier.
PROB_TIER: dict[str, str] = {"special_illustration_rare": "super_rare"}

# Unified score weights — single composite signal used for all recommendations.
UNIFIED_WEIGHTS = {
    "new_card_10x": 1.0,   # primary: unique new cards in a 10-pack batch (diminishing returns)
    "copy":         0.2,   # secondary: duplicate copies for deck building
    "deck_target":  1.5,   # scaled deck completion contribution
}

# Rarities considered "rare+" for breakdown metrics in rankings — imported from
# _collection_io as the single source (shared with assign/sync alt-art logic).
# HOURGLASS_PER_PACK also imported from _collection_io.

# Fallback confidence adjustment when PZ rates are unavailable
INFERRED_CONFIDENCE_WEIGHT = 0.85
# PZ direct rates are authoritative — no discount applied
PZ_CONFIDENCE_WEIGHT = 1.0

TOP_N_CARDS = 5  # top EV cards listed per pack


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_collection(path: Path) -> tuple[dict, dict]:
    """
    Returns (by_name, by_card):
      by_name: {normalized_name: total_count}  — name-based fallback for all entries
      by_card: {(set_code_upper, card_number): count}  — set-specific for entries that
               carry set_code (added by sync for new cards from B3A onwards)
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_name: dict[str, int] = {}
    by_card: dict[tuple[str, int], int] = {}
    for e in raw.get("collection", []):
        nn = _norm_name(e["name"])
        by_name[nn] = by_name.get(nn, 0) + e["count"]
        sc = str(e.get("set_code") or "").upper().strip()
        cn_raw = e.get("card_number")
        if sc and cn_raw is not None:
            try:
                cn = int(cn_raw)
                by_card[(sc, cn)] = by_card.get((sc, cn), 0) + e["count"]
            except (TypeError, ValueError):
                pass
    return by_name, by_card


def apply_reprint_links(by_card: dict, path: Path) -> dict:
    """Credit ownership across A4b 'Deluxe Pack: ex' reprint <-> original links.

    A base-rarity A4b card is the SAME card as its original-set printing (the app fills both
    dex slots when you own one). Owning either coord must therefore credit the other, or the
    unowned slot inflates its pack's EV. One-hop, mirrored crediting (max, never sum — it's
    one physical card). No-op if the link file is absent. Built by build_reprint_links.py.
    """
    if not path.exists():
        return by_card
    # Decide credits from a SNAPSHOT of original ownership so crediting stays one-hop: two
    # A4b printings that share one original (e.g. Greninja A4b/114 and /115 → A1/89) must not
    # credit each other through it. Owning an original still credits all its reprints.
    base = dict(by_card)
    for link in json.loads(path.read_text(encoding="utf-8")).get("links", []):
        a = (str(link["a4b"][0]).upper(), link["a4b"][1])
        o = (str(link["original"][0]).upper(), link["original"][1])
        owned = max(base.get(a, 0), base.get(o, 0))
        if owned:
            by_card[a] = max(by_card.get(a, 0), owned)
            by_card[o] = max(by_card.get(o, 0), owned)
    return by_card


def load_pull_model(path: Path) -> dict:
    """Returns {pack_name: pack_record}."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {p["pack_name"]: p for p in raw["packs"]}


def load_pack_sources(path: Path):
    """Returns (pack_cards, expansion_shared).
    pack_cards:       {pack_name: [records]}
    expansion_shared: {expansion: [records]}  (pack_name=None → shared pool)
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw["records"] if isinstance(raw, dict) else raw
    pack_cards = defaultdict(list)
    expansion_shared = defaultdict(list)
    for r in records:
        pn = r.get("pack_name")
        exp = r.get("expansion", "")
        if pn is None:
            expansion_shared[exp].append(r)
        else:
            pack_cards[pn].append(r)
    return dict(pack_cards), dict(expansion_shared)


def load_deck_targets(path: Path) -> dict:
    """Returns {normalized_card_name: needed_count} for cards missing from decks."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    targets = {}
    for deck in raw.get("decks", []):
        for mc in deck.get("missing_cards", []):
            nn = _norm_name(mc["name"])
            # If a card appears in multiple decks, take the max needed
            needed = mc.get("short_by", 1)
            targets[nn] = max(targets.get(nn, 0), needed)
    return targets



def load_pz_pack_odds(path: Path) -> tuple[dict, dict]:
    """
    Returns (pz_raw, pz_odds_by_slug) where:
    - pz_raw: {pack_slug: pack_data} from pz_pack_odds.json
    - pz_odds_by_slug: {pack_slug: {(set_code_upper, card_number): drop_chance_decimal}}
    """
    if not path.exists():
        return {}, {}
    pz_raw = json.loads(path.read_text(encoding="utf-8"))
    pz_odds: dict[str, dict] = {}
    for slug, pdata in pz_raw.items():
        card_lookup: dict[tuple, float] = {}
        for card in pdata.get("cards", []):
            sc  = card.get("set_code", "").upper()
            num = card.get("card_number")
            pct = card.get("drop_chance_pct")
            if sc and num is not None and pct is not None:
                card_lookup[(sc, num)] = pct / 100.0
        pz_odds[slug] = card_lookup
    return pz_raw, pz_odds


def resolve_pz_slug(pack_name: str, set_code: str, pz_raw: dict) -> str | None:
    """Return the PZ pack slug for a pull_model pack (matched by expansion_id + name)."""
    sc_up = set_code.upper()
    candidates = [
        (pdata.get("pack_name", ""), slug)
        for slug, pdata in pz_raw.items()
        if pdata.get("expansion_id", "").upper() == sc_up
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][1]
    pl = pack_name.lower()
    for pz_name, slug in candidates:
        suffix = pz_name.split(": ", 1)[-1].lower()
        if suffix == pl or pz_name.lower() == pl:
            return slug
    for pz_name, slug in candidates:
        suffix = pz_name.split(": ", 1)[-1].lower()
        if pl in suffix:
            return slug
    return None


# ---------------------------------------------------------------------------
# EV computation
# ---------------------------------------------------------------------------

def card_pull_ev(rarity: str, combined_by_rarity: dict, slot_rates: dict) -> float:
    """
    E[copies of a specific card of this rarity per pack opening].

    Supports two-branch model (regular + rare) and three-branch model
    (regular + rare + regular_pack_plus_one). In the three-branch model,
    slots 1-5 are identical across regular and plus_one branches, so
    combined probability = P_regular + P_plus_one is used for those slots.
    Card 6 (shiny only) is omitted unless shiny cards appear in combined_by_rarity.

    Super Rare and Special Illustration Rare share the ★★ "Two Star" slot rate and
    pull-rate tier, so SIR cards use the super_rare slot probability and the COMBINED
    ★★ pool count (otherwise the shared slot rate would be over-allocated).
    """
    prob_rarity = PROB_TIER.get(rarity, rarity)
    # Pool size for this probability tier — all rarities that map to the same ★★ slot.
    N_R = sum(n for r, n in combined_by_rarity.items() if PROB_TIER.get(r, r) == prob_rarity)
    if N_R <= 0:
        return 0.0

    P_regular  = slot_rates.get("regular_pack_probability", 0.9995)
    P_plus_one = slot_rates.get("regular_pack_plus_one_probability") or 0.0
    P_rare     = slot_rates.get("rare_pack_probability", 0.0005)
    if slot_rates.get("branch_model") == "three_branch" and P_plus_one == 0.0:
        print(
            f"  WARNING: three_branch pack has plus_one_probability=null — "
            f"treating as two_branch. Add regular_pack_plus_one_probability to pull_probability_model.json.",
            file=sys.stderr,
        )
    # Combined probability for slots 1-5 (same rates in both regular branches)
    P_combined = P_regular + P_plus_one

    slot_4    = slot_rates.get("slot_4") or {}
    slot_5    = slot_rates.get("slot_5") or {}
    slot_6    = slot_rates.get("slot_6") or {}
    rare_dist = slot_rates.get("rare_pack_all_5_slots") or {}

    if prob_rarity == "common":
        return P_combined * 3.0 / N_R

    p4 = slot_4.get(prob_rarity, 0.0)
    p5 = slot_5.get(prob_rarity, 0.0)
    regular_contrib = P_combined * (p4 + p5) / N_R

    # Rare pack: 5 slots each with rare_dist probability.
    # crown_or_highest_rare is an alias for ultra_rare used in some pack models.
    p_rare_per_slot = rare_dist.get(prob_rarity, 0.0)
    if prob_rarity == "ultra_rare" and p_rare_per_slot == 0.0:
        p_rare_per_slot = rare_dist.get("crown_or_highest_rare", 0.0)
    rare_contrib = P_rare * 5 * p_rare_per_slot / N_R

    # Card 6 (regular_pack_plus_one branch only, shiny rarities).
    p6 = slot_6.get(prob_rarity, 0.0)
    plus_one_card6_contrib = P_plus_one * p6 / N_R if p6 > 0 else 0.0

    return regular_contrib + rare_contrib + plus_one_card6_contrib


def value_of_next_copy(owned: int, rarity: str | None,
                       deck_targets: dict, norm_name: str) -> float:
    """
    Value of pulling one more copy of this card.

    owned        = copies already in collection.
    rarity       = card rarity string (e.g. "one_star", "crown") — used for rarity bonus on
                   first copy. None is treated as no bonus.
    deck_targets = {norm_name: still_needed_count} where still_needed is how many copies
                   the player is short across all target decks.
    """
    still_needed = deck_targets.get(norm_name, 0)

    if owned >= 2:
        return 0.0  # already at maximum useful quantity

    if owned == 0:
        v = SCORING_WEIGHTS["new_card"]
        v += RARITY_BONUS.get(rarity or "", 0.0)
        if still_needed > 0:
            v += SCORING_WEIGHTS["deck_target"] / max(still_needed, 1)
    else:
        # owned == 1, pulling the second copy
        v = SCORING_WEIGHTS["copy_up_to_2"]
        if still_needed > 0:
            v += SCORING_WEIGHTS["deck_target"] / max(still_needed, 1)

    return v


def compute_pack_ev_record(pack_record: dict, all_pool_cards: list,
                           collection: dict, deck_targets: dict,
                           pz_card_odds: dict | None = None,
                           pz_name_odds: dict | None = None,
                           collection_by_card: dict | None = None) -> dict:
    """Compute all EV fields for one pack.

    pz_card_odds: {(set_code_upper, card_number): drop_chance_decimal} — primary PZ lookup.
    pz_name_odds: {name_lower: drop_chance_decimal} — name fallback for replacement/cross-set
                  cards that don't match by (set_code, card_number). Built only from PZ cards
                  that have no corresponding pack_sources entry, so no double-counting.
                  When a name appeared with conflicting rates, the lower rate is stored.
    """
    pack_name = pack_record["pack_name"]
    slot_rates = pack_record.get("slot_rates")
    combined_by_rarity = pack_record.get("card_pool", {}).get("combined_by_rarity", {})

    base = {
        "pack_name": pack_name,
        "expansion": pack_record["expansion"],
        "set_code": pack_record["set_code"],
        "source_status": "inferred",
        "slot_rates_confidence": (slot_rates or {}).get("confidence", "unknown"),
    }

    if not slot_rates and not pz_card_odds:
        return {**base, "blocked": True,
                "blocked_reason": "no_slot_rates",
                "purchasable": pack_record.get("hourglass_purchasable", True),
                "cards_in_pool": len(all_pool_cards),
                "pack_total_ev": 0.0,
                "confidence_adjusted_ev": 0.0}

    owned_in_pool    = 0
    missing_in_pool  = 0
    new_card_ev      = 0.0
    new_card_ev_10x  = 0.0   # E[rarity-weighted new cards in 10 consecutive openings]
    copy_ev          = 0.0
    deck_target_ev   = 0.0
    missing_rare_plus = 0    # count of missing one_star+ cards
    rare_plus_ev_10x  = 0.0  # P(≥1 in 10 packs), count-based, for rare+ cards only
    card_ev_list     = []
    pz_hits          = 0
    fallback_count   = 0
    pz_excluded_count = 0

    for card in all_pool_cards:
        card_name = card.get("card_name", "")
        # normalize_rarity is the safety net: a stray legacy/un-migrated rarity is read as
        # its new-vocabulary name so RARITY_BONUS / card_pull_ev / RARE_PLUS lookups match.
        rarity    = normalize_rarity(card.get("rarity"))
        nn        = _norm_name(card_name)
        is_dt     = nn in deck_targets

        sc  = card.get("set_code", "").upper()
        cn  = card.get("card_number")

        # Each printing is counted independently: only credits ownership if this exact
        # (set_code, card_number) is in the collection. A4b reprints and their originals are
        # cross-credited beforehand via apply_reprint_links (owning one fills both dex slots,
        # as the app does). Falls back to name-only for genuinely coord-less legacy entries
        # (in practice 0 since all entries carry coords).
        # TODO(deck-ev): when deck logic lands, switch to name-count here (decks mix sets).
        if collection_by_card and sc and cn is not None:
            owned = collection_by_card.get((sc, cn), 0)
        else:
            owned = collection.get(nn, 0)

        if owned > 0:
            owned_in_pool += 1
        else:
            missing_in_pool += 1
        pz_pull = pz_card_odds.get((sc, cn)) if (pz_card_odds and sc and cn is not None) else None

        if pz_pull is None and pz_name_odds and card_name:
            pz_pull = pz_name_odds.get(nn)

        if pz_pull is not None:
            p_pull = pz_pull
            pz_hits += 1  # count all PZ cards in coverage denominator, including zero-rate
        elif pz_card_odds:
            # PZ data exists for this pack but card absent from it → not pullable from packs.
            pz_excluded_count += 1
            continue
        else:
            if not rarity:
                continue
            if not slot_rates:
                continue
            p_pull = card_pull_ev(rarity, combined_by_rarity, slot_rates)

        if p_pull <= 0:
            continue

        if pz_pull is None:
            fallback_count += 1

        v = value_of_next_copy(owned, rarity, deck_targets, nn)
        ev = p_pull * v

        if ev > 0:
            card_ev_list.append({
                "name": card_name,
                "rarity": rarity,
                "is_deck_target": is_dt,
                "owned": owned,
                "pull_prob": round(p_pull, 7),
                "value": round(v, 2),
                "ev_contribution": round(ev, 7),
                "rate_source": "pz" if pz_pull is not None else "inferred",
            })

        if owned == 0:
            new_card_ev += ev
            # 10x model: P(get at least 1 in 10 packs) — accounts for within-batch duplicates.
            # PZ rates are proper per-pack probabilities; use directly.
            # Inferred rates return E[copies per pack] for multi-slot rarities (one/two/three_diamond
            # each fill 3 regular slots), which can exceed 1.0 when the pool has < 3 cards of
            # that rarity. Back-calculate P(≥1 in 1 pack) = 1-(1-p_per_slot)^3 in that case.
            if pz_pull is None and p_pull > 1.0:
                p_per_slot = p_pull / 3.0  # 3 regular slots for common rarities
                p_at_least_one = 1.0 - (1.0 - min(p_per_slot, 1.0)) ** 3
            else:
                p_at_least_one = min(p_pull, 1.0)
            p_10x = 1.0 - (1.0 - p_at_least_one) ** 10
            v_rarity = 1.0 + RARITY_BONUS.get(rarity or "", 0.0)
            new_card_ev_10x += p_10x * v_rarity
            if rarity in RARE_PLUS_RARITIES:
                missing_rare_plus += 1
                rare_plus_ev_10x += p_10x  # count-based for display
        else:
            copy_ev += ev

        if is_dt:
            deck_target_ev += ev

    pack_total_ev = new_card_ev + copy_ev

    pz_total = pz_hits + fallback_count
    pz_coverage = pz_hits / pz_total if pz_total > 0 else 0.0
    confidence_weight = PZ_CONFIDENCE_WEIGHT if pz_coverage >= 0.90 else INFERRED_CONFIDENCE_WEIGHT
    source_status = "pz_verified" if pz_coverage >= 0.90 else "inferred"

    # Diminishing returns ratio: how much 10x batch EV differs from 10 × 1x EV.
    # A ratio < 0.85 means significant within-batch duplicates (pack is near-complete).
    ev_10x_uncapped = new_card_ev * 10
    dr_ratio = new_card_ev_10x / ev_10x_uncapped if ev_10x_uncapped > 0 else 1.0

    # Unified score: single composite signal used for all downstream recommendations.
    # TODO(deck-ev): deck_target_ev is currently ALWAYS 0 — its source file
    # (deck_recommendation_validation.json) has no producer in the pipeline (see load at
    # DECK_VALIDATION_JSON). So the deck_target term is inert today; do not read the ×1.5
    # weight as a live signal until a deck producer is wired up.
    unified_score = (
        new_card_ev_10x * UNIFIED_WEIGHTS["new_card_10x"]
        + copy_ev        * UNIFIED_WEIGHTS["copy"]
        + deck_target_ev * UNIFIED_WEIGHTS["deck_target"]
    ) * confidence_weight

    # Cost efficiency: hourglasses per expected unique new card
    cost_per_unique_1x  = HOURGLASS_PER_PACK / max(new_card_ev, 0.001)
    cost_per_unique_10x = (HOURGLASS_PER_PACK * 10) / max(new_card_ev_10x, 0.001)

    card_ev_list.sort(key=lambda x: x["ev_contribution"], reverse=True)
    deck_target_cards = [c for c in card_ev_list if c.get("is_deck_target")]

    return {
        **base,
        "source_status": source_status,
        "confidence_weight": confidence_weight,
        "blocked": False,
        "blocked_reason": None,
        "purchasable": pack_record.get("hourglass_purchasable", True),
        "cards_in_pool": len(all_pool_cards),
        "owned_in_pool": owned_in_pool,
        "missing_in_pool": missing_in_pool,
        "new_card_ev":     round(new_card_ev, 6),
        "new_card_ev_10x": round(new_card_ev_10x, 6),
        "copy_ev":         round(copy_ev, 6),
        "deck_target_ev":  round(deck_target_ev, 6),
        "missing_rare_plus": missing_rare_plus,
        "rare_plus_ev_10x":  round(rare_plus_ev_10x, 6),
        "pack_total_ev":   round(pack_total_ev, 6),
        "confidence_adjusted_ev": round(pack_total_ev * confidence_weight, 6),
        "unified_score":   round(unified_score, 6),
        "ev_diminishing_returns_ratio": round(dr_ratio, 4),
        "cost_per_unique_card_1x":  round(cost_per_unique_1x, 2),
        "cost_per_unique_card_10x": round(cost_per_unique_10x, 2),
        "pz_coverage": round(pz_coverage, 3),
        "top_ev_cards": card_ev_list[:TOP_N_CARDS],
        "deck_target_cards": deck_target_cards,
        "notes": (
            f"slot_rates={'pz_verified' if source_status == 'pz_verified' else 'inferred'}. "
            f"PZ coverage: {pz_hits}/{pz_total} cards"
            + (f" ({pz_excluded_count} excluded as non-pullable)." if pz_excluded_count else ".")
            + f" {owned_in_pool}/{len(all_pool_cards)} cards in pool are owned. "
            f"EV excludes low_confidence and unresolved collection entries."
        ),
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(collection, pull_model, pack_cards, expansion_shared, deck_targets,
          pz_raw=None, pz_odds=None, collection_by_card=None):
    pack_ev_records = []
    blocked = []

    for pack_name, pack_record in sorted(pull_model.items()):
        expansion = pack_record["expansion"]
        set_code  = pack_record.get("set_code", "")
        all_pool_cards = (
            list(pack_cards.get(pack_name, []))
            + list(expansion_shared.get(expansion, []))
        )
        pz_card_odds = None
        pz_name_odds = None
        if pz_raw and pz_odds:
            slug = resolve_pz_slug(pack_name, set_code, pz_raw)
            if slug:
                pz_card_odds = pz_odds.get(slug, {})
                # Name fallback: PZ cards whose (set_code, card_number) has no matching
                # pack_sources entry — catches A4b replacements and cross-set cards.
                # When the same name appears with conflicting rates, the lower rate wins.
                pool_keys = {
                    (r.get("set_code", "").upper(), r.get("card_number"))
                    for r in all_pool_cards
                }
                pz_name_odds = {}
                for pz_card in pz_raw[slug].get("cards", []):
                    sc_cn = (pz_card["set_code"].upper(), pz_card["card_number"])
                    if sc_cn not in pool_keys:
                        name_l = _norm_name(pz_card.get("name", ""))
                        pct = pz_card.get("drop_chance_pct")
                        if name_l and pct is not None:
                            rate = pct / 100.0
                            if name_l in pz_name_odds and pz_name_odds[name_l] != rate:
                                pz_name_odds[name_l] = min(pz_name_odds[name_l], rate)
                            else:
                                pz_name_odds[name_l] = rate
        record = compute_pack_ev_record(
            pack_record, all_pool_cards, collection, deck_targets,
            pz_card_odds, pz_name_odds, collection_by_card,
        )
        if record.get("blocked"):
            blocked.append(record)
        else:
            pack_ev_records.append(record)

    return pack_ev_records, blocked


def summarize(records: list) -> dict:
    by_unified = sorted(records, key=lambda r: r.get("unified_score", 0.0), reverse=True)
    by_new     = sorted(records, key=lambda r: r["new_card_ev"], reverse=True)
    by_dt      = sorted(records, key=lambda r: r["deck_target_ev"], reverse=True)

    def brief(r):
        return {
            "pack_name": r["pack_name"],
            "expansion": r["expansion"],
            "unified_score": r.get("unified_score", 0.0),
            "new_card_ev": r["new_card_ev"],
            "new_card_ev_10x": r.get("new_card_ev_10x", 0.0),
            "deck_target_ev": r["deck_target_ev"],
            "confidence_adjusted_ev": r["confidence_adjusted_ev"],
        }

    return {
        "top_packs_by_unified_score":  [brief(r) for r in by_unified[:5]],
        "top_packs_by_new_card_ev":    [brief(r) for r in by_new[:5]],
        "top_packs_by_deck_target_ev": [brief(r) for r in by_dt[:5]],
        "highest_unified_pack":        by_unified[0]["pack_name"] if by_unified else None,
        "highest_new_card_ev_pack":    by_new[0]["pack_name"] if by_new else None,
        "total_packs_scored":          len(records),
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _read_model_confidence(path: Path) -> str:
    """Read source_status from pull_probability_model.json.

    Fails loudly if the model is missing or malformed — a corrupt model file
    must not silently degrade all EV to the 'inferred' path.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("meta", {}).get("source_status", "inferred")


def write_json(pack_ev_records, blocked, deck_targets, collection_total, inputs_hash=None):
    model_confidence = _read_model_confidence(PULL_MODEL_JSON)
    summary = summarize(pack_ev_records)

    if model_confidence == "pz_verified":
        pz_verified_count = sum(1 for r in pack_ev_records if r.get("source_status") == "pz_verified")
        warning = (
            f"Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone "
            f"for all {pz_verified_count} packs. EV rankings reflect actual pull probabilities. "
            f"No inferred confidence adjustment applied."
        )
    elif model_confidence == "third_party_verified_with_in_app_anchor":
        warning = (
            "Slot rates are THIRD_PARTY_VERIFIED_WITH_IN_APP_ANCHOR — 12 packs bulbapedia_branch_verified "
            "(branch percentages confirmed from Bulbapedia offering rates), 1 pack user_in_app_verified_plus_bulbapedia "
            "(Pulsing Aura B3: in-app verified + Bulbapedia corroborated), 8 packs third_party_verified "
            "(pattern-consistent two-branch), 3 packs pending_verification (A4/A4b). "
            "Rarity distributions within slots remain third_party_verified. "
            "EV rankings are suitable for planning but not final recommendations."
        )
    elif model_confidence == "in_app_verified_partial":
        warning = (
            "Slot rates are IN_APP_VERIFIED_PARTIAL — Pulsing Aura (B3) user-in-app-verified "
            "(three-branch model, corrected rare pack rates). All other packs retain prior "
            "third_party_verified two-branch model (may be missing regular_pack_plus_one branch). "
            "EV rankings are suitable for planning but not fully verified."
        )
    elif model_confidence == "third_party_verified":
        warning = (
            "Slot rates are THIRD_PARTY_VERIFIED — confirmed across 4 independent sources "
            "(Game8, ONE Esports, CGMagazine, ShackNews). NOT official in-app verified. "
            "EV rankings are suitable for planning but not final recommendations."
        )
    else:
        warning = (
            "Slot rates are INFERRED from external sources. "
            "Not verified from in-app Offering Rates. "
            "EV rankings are for informational/planning purposes only."
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_pack_ev.py",
        "meta": {
            "model_confidence": model_confidence,
            "collection_total": collection_total,
            "collection_mutated": False,
            "inputs_hash": inputs_hash,
            "warnings": [warning],
        },
        "scoring_weights": SCORING_WEIGHTS,
        "confidence_weights": {
            "slot_rates": f"{model_confidence}",
            "pz_verified_adjustment": PZ_CONFIDENCE_WEIGHT,
            "inferred_adjustment": INFERRED_CONFIDENCE_WEIGHT,
            "auto_accept": 1.0,
            "secondary_evidence": 0.85,
            "low_confidence": "excluded_from_ev",
            "unresolved": "excluded_from_ev",
        },
        "deck_targets": {
            "count": len(deck_targets),
            "targets": {k: v for k, v in deck_targets.items()},
        },
        "overall_summary": summary,
        "packs": pack_ev_records,
        "blocked_packs": blocked,
        "next_steps": [
            "Review top-EV packs as planning input — see review/inferred_pack_recommendations.md.",
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def run_validate() -> bool:
    print("\n=== build_pack_ev.py [VALIDATE] ===")
    errors = 0

    if not OUT_JSON.exists():
        print("  ERROR: pack_ev.json not found — run without --validate first")
        return False

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    packs = out.get("packs", [])

    if not packs:
        print("  ERROR: packs array is empty")
        return False
    print(f"  PASS  {len(packs)} pack EV records present")

    # model_confidence must be a valid confidence level
    mc = out.get("meta", {}).get("model_confidence")
    valid_mc = (
        "inferred", "third_party_verified", "verified",
        "user_in_app_verified", "in_app_verified_partial",
        "third_party_verified_with_in_app_anchor", "pending_verification",
        "bulbapedia_branch_verified", "bulbapedia_verified",
        "user_in_app_verified_plus_bulbapedia", "pz_verified",
    )
    if mc not in valid_mc:
        print(f"  ERROR: model_confidence='{mc}' not in {valid_mc}")
        errors += 1
    else:
        print(f"  PASS  model_confidence={mc}")

    # every pack has pack_name and source_status
    bad = [p for p in packs if not p.get("pack_name") or not p.get("source_status")]
    if bad:
        print(f"  ERROR: {len(bad)} packs missing pack_name or source_status")
        errors += 1
    else:
        print("  PASS  all packs have pack_name and source_status")

    # no negative EV values (except if blocked)
    neg = [p for p in packs
           if not p.get("blocked") and p.get("pack_total_ev", 0) < 0]
    if neg:
        print(f"  ERROR: {len(neg)} packs have negative pack_total_ev")
        errors += 1
    else:
        print("  PASS  no negative EV values")

    # collection total unchanged
    col_total = out.get("meta", {}).get("collection_total")
    if not col_total or col_total < 1:
        print(f"  ERROR: collection_total={col_total} — invalid")
        errors += 1
    else:
        print(f"  PASS  collection_total={col_total}")

    col_mutated = out.get("meta", {}).get("collection_mutated")
    if col_mutated:
        print("  ERROR: collection_mutated=True — collection.json must not be modified")
        errors += 1
    else:
        print("  PASS  collection_mutated=False")

    # verify current collection.json still matches
    if COLLECTION_JSON.exists():
        col = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
        actual_total = sum(e["count"] for e in col.get("collection", []))
        if actual_total != col_total:
            print(f"  ERROR: collection.json total={actual_total} differs from pack_ev.json total={col_total}")
            errors += 1
        else:
            print(f"  PASS  collection.json total={actual_total} matches pack_ev.json")

    # every pack must exist in pull_probability_model
    if PULL_MODEL_JSON.exists():
        model = json.loads(PULL_MODEL_JSON.read_text(encoding="utf-8"))
        model_packs = {p["pack_name"] for p in model["packs"]}
        missing_model = [p["pack_name"] for p in packs
                         if p["pack_name"] not in model_packs]
        if missing_model:
            print(f"  ERROR: {len(missing_model)} pack(s) not in pull_probability_model: "
                  f"{missing_model}")
            errors += 1
        else:
            print("  PASS  all packs exist in pull_probability_model.json")

    # top_ev_cards structure
    bad_cards = []
    for p in packs:
        for c in p.get("top_ev_cards", []):
            if not c.get("name") or not c.get("rarity") or c.get("pull_prob") is None:
                bad_cards.append(f"{p['pack_name']}:{c.get('name','?')}")
    if bad_cards:
        print(f"  ERROR: {len(bad_cards)} top_ev_cards missing required fields")
        errors += 1
    else:
        print("  PASS  top_ev_cards structure valid")

    # output file exists
    if OUT_JSON.exists():
        print(f"  PASS  {OUT_JSON.relative_to(ROOT)} exists")
    else:
        print(f"  ERROR: {OUT_JSON.relative_to(ROOT)} missing")
        errors += 1

    if errors == 0:
        print(f"\nVALIDATION PASSED  ({len(packs)} packs, model_confidence={mc})")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build or validate the pack EV model")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        sys.exit(0 if run_validate() else 1)

    print("\n=== build_pack_ev.py ===")

    for p in (COLLECTION_JSON, PULL_MODEL_JSON, PACK_SOURCES_JSON):
        if not p.exists():
            print(f"ERROR: required input not found: {p}", file=sys.stderr)
            sys.exit(1)

    # Inputs hash skip: if no input file has changed since last run, reuse prior results.
    # Covers collection AND all reference inputs so pull-model or deck-target edits invalidate cache.
    _h = hashlib.sha256()
    for _p in (COLLECTION_JSON, PULL_MODEL_JSON, PACK_SOURCES_JSON, REPRINT_LINKS_JSON,
               DECK_VALIDATION_JSON, PZ_PACK_ODDS_JSON):
        if _p.exists():
            _h.update(_p.read_bytes())
    inputs_hash = _h.hexdigest()
    if OUT_JSON.exists():
        try:
            prev_meta = json.loads(OUT_JSON.read_text(encoding="utf-8")).get("meta", {})
            if prev_meta.get("inputs_hash") == inputs_hash:
                print(f"  Inputs unchanged (hash={inputs_hash[:12]}…) — skipping EV recompute.")
                sys.exit(0)
        except Exception:
            pass  # corrupted prior output — recompute

    collection, collection_by_card = load_collection(COLLECTION_JSON)
    collection_by_card = apply_reprint_links(collection_by_card, REPRINT_LINKS_JSON)
    pull_model       = load_pull_model(PULL_MODEL_JSON)
    pack_cards, expansion_shared = load_pack_sources(PACK_SOURCES_JSON)
    deck_targets     = load_deck_targets(DECK_VALIDATION_JSON)
    pz_raw, pz_odds  = load_pz_pack_odds(PZ_PACK_ODDS_JSON)

    collection_total = sum(collection.values())
    print(f"  Collection entries: {len(collection)} unique, total={collection_total}")
    print(f"  Pull model packs:   {len(pull_model)}")
    print(f"  Deck targets:       {len(deck_targets)} → {list(deck_targets)}")
    if pz_raw:
        print(f"  PZ pack odds:       {len(pz_raw)} packs — using direct PZ drop chances")
    else:
        print(f"  PZ pack odds:       not found — falling back to inferred slot rates")

    pack_ev_records, blocked = build(
        collection, pull_model, pack_cards, expansion_shared, deck_targets,
        pz_raw, pz_odds, collection_by_card,
    )

    out = write_json(pack_ev_records, blocked, deck_targets, collection_total, inputs_hash)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")

    summary = out["overall_summary"]
    print("\n=== Summary ===")
    print(f"  Packs scored:    {len(pack_ev_records)}")
    print(f"  Packs blocked:   {len(blocked)}")
    print(f"  Model confidence: {out['meta']['model_confidence']}")
    print("  Top packs by unified score:")
    for p in summary["top_packs_by_unified_score"]:
        print(f"    {p['pack_name']:30s} unified={p['unified_score']:.4f}  "
              f"adj={p['confidence_adjusted_ev']:.4f}")
    print("\nDone.")


if __name__ == "__main__":
    main()
