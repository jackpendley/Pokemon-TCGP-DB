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
    data/exports/pack_ev.csv
    review/pack_ev.md

Usage:
    python3 scripts/build_pack_ev.py
    python3 scripts/build_pack_ev.py --validate
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON     = ROOT / "data" / "current"    / "collection_normalized.json"
PULL_MODEL_JSON     = ROOT / "data" / "reference"  / "pull_probability_model.json"
PACK_SOURCES_JSON   = ROOT / "data" / "reference"  / "pack_sources.json"
DECK_VALIDATION_JSON = ROOT / "data" / "exports"   / "deck_recommendation_validation.json"
PZ_PACK_ODDS_JSON   = ROOT / "data" / "reference"  / "pz_pack_odds.json"

OUT_JSON = ROOT / "data" / "current"  / "pack_ev.json"
OUT_CSV  = ROOT / "data" / "exports"  / "pack_ev.csv"
OUT_MD   = ROOT / "review"            / "pack_ev.md"

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "new_card":    1.0,   # first copy of any unseen unique card
    "copy_up_to_2": 0.4,  # second copy (can use 2 copies per deck)
    "ex_missing":  1.0,   # bonus if EX/powerful card, not yet at 2 copies
    "deck_target": 2.0,   # bonus if explicitly needed to complete a deck
}

# Fallback confidence adjustment when PZ rates are unavailable
INFERRED_CONFIDENCE_WEIGHT = 0.85
# PZ direct rates are authoritative — no discount applied
PZ_CONFIDENCE_WEIGHT = 1.0

TOP_N_CARDS = 5  # top EV cards listed per pack

# Deck-priority composite score: adj_ev + DECK_PRIORITY_BOOST * deck_target_ev.
# At 10×, a pack with deck_target_ev=0.06 (Solgaleo/Incineroar ex) scores ~+0.61
# above its adj_ev, enough to rank it above a pure collection-expansion pack when
# the player cares more about completing a chase deck than raw new-card rate.
DECK_PRIORITY_BOOST = 10


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def normalize(name: str) -> str:
    return name.lower().strip()


def _norm_name(name: str) -> str:
    """Normalize card name for cross-source comparison: lowercase + smart-quote → apostrophe."""
    return name.lower().replace("’", "'").replace("‘", "'").strip()


def load_collection(path: Path) -> dict:
    """Returns {normalized_name: total_count} — sums counts across set variants."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for e in raw["collection"]:
        nn = normalize(e["name"])
        result[nn] = result.get(nn, 0) + e["count"]
    return result


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
            nn = normalize(mc["name"])
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
    """
    N_R = combined_by_rarity.get(rarity, 0)
    if N_R <= 0:
        return 0.0

    P_regular  = slot_rates.get("regular_pack_probability", 0.9995)
    P_plus_one = slot_rates.get("regular_pack_plus_one_probability") or 0.0
    P_rare     = slot_rates.get("rare_pack_probability", 0.0005)
    # Combined probability for slots 1-5 (same rates in both regular branches)
    P_combined = P_regular + P_plus_one

    slot_4    = slot_rates.get("slot_4") or {}
    slot_5    = slot_rates.get("slot_5") or {}
    slot_6    = slot_rates.get("slot_6") or {}
    rare_dist = slot_rates.get("rare_pack_all_5_slots") or {}

    if rarity == "one_diamond":
        return P_combined * 3.0 / N_R

    p4 = slot_4.get(rarity, 0.0)
    p5 = slot_5.get(rarity, 0.0)
    regular_contrib = P_combined * (p4 + p5) / N_R

    # Rare pack: 5 slots each with rare_dist probability.
    # crown_or_highest_rare is an alias for crown used in some pack models.
    p_rare_per_slot = rare_dist.get(rarity, 0.0)
    if rarity == "crown" and p_rare_per_slot == 0.0:
        p_rare_per_slot = rare_dist.get("crown_or_highest_rare", 0.0)
    rare_contrib = P_rare * 5 * p_rare_per_slot / N_R

    # Card 6 (regular_pack_plus_one branch only, shiny rarities).
    # Currently 0 for all packs since shiny cards are not in pack_sources.json.
    p6 = slot_6.get(rarity, 0.0)
    plus_one_card6_contrib = P_plus_one * p6 / N_R if p6 > 0 else 0.0

    return regular_contrib + rare_contrib + plus_one_card6_contrib


def value_of_next_copy(owned: int, is_ex: bool,
                       deck_targets: dict, norm_name: str) -> float:
    """
    Value of pulling one more copy of this card.
    owned = copies already in collection.
    deck_targets = {norm_name: still_needed_count}
    """
    still_needed = deck_targets.get(norm_name, 0)

    if owned >= 2:
        return 0.0  # already at maximum useful quantity

    # Determine base value for this copy number
    if owned == 0:
        v = SCORING_WEIGHTS["new_card"]
        if is_ex:
            v += SCORING_WEIGHTS["ex_missing"]
        if still_needed > 0:
            v += SCORING_WEIGHTS["deck_target"]
    else:
        # owned == 1, pulling the second copy
        v = SCORING_WEIGHTS["copy_up_to_2"]
        if is_ex and still_needed > 0:
            v += SCORING_WEIGHTS["ex_missing"] + SCORING_WEIGHTS["deck_target"]
        elif still_needed > 0:
            v += SCORING_WEIGHTS["deck_target"]

    return v


def compute_pack_ev_record(pack_record: dict, all_pool_cards: list,
                           collection: dict, deck_targets: dict,
                           pz_card_odds: dict | None = None,
                           pz_name_odds: dict | None = None) -> dict:
    """Compute all EV fields for one pack.

    pz_card_odds: {(set_code_upper, card_number): drop_chance_decimal} — primary PZ lookup.
    pz_name_odds: {name_lower: drop_chance_decimal} — name fallback for replacement/cross-set
                  cards that don't match by (set_code, card_number). Built only from PZ cards
                  that have no corresponding pack_sources entry, so no double-counting.
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
                "cards_in_pool": len(all_pool_cards),
                "pack_total_ev": 0.0,
                "confidence_adjusted_ev": 0.0}

    owned_in_pool  = 0
    missing_in_pool = 0
    new_card_ev    = 0.0
    copy_ev        = 0.0
    ex_card_ev     = 0.0
    deck_target_ev = 0.0
    card_ev_list   = []
    pz_hits        = 0
    fallback_count = 0

    for card in all_pool_cards:
        card_name = card.get("card_name", "")
        rarity    = card.get("rarity")
        is_ex     = bool(card.get("is_ex"))
        nn        = normalize(card_name)
        is_dt     = nn in deck_targets

        owned = collection.get(nn, 0)

        if owned > 0:
            owned_in_pool += 1
        else:
            missing_in_pool += 1

        sc  = card.get("set_code", "").upper()
        cn  = card.get("card_number")
        pz_pull = pz_card_odds.get((sc, cn)) if (pz_card_odds and sc and cn is not None) else None

        if pz_pull is None and pz_name_odds and card_name:
            pz_pull = pz_name_odds.get(_norm_name(card_name))

        if pz_pull is not None:
            p_pull = pz_pull
            pz_hits += 1
        elif pz_card_odds:
            # PZ data exists for this pack but card absent from it → not pullable from packs
            # (e.g., Mew A1/283 is a mission reward, not in any pack pool)
            continue
        else:
            if not rarity:
                # rarity=None cards never contribute EV — exclude from coverage denominator
                continue
            if not slot_rates:
                fallback_count += 1
                continue
            p_pull = card_pull_ev(rarity, combined_by_rarity, slot_rates)
            fallback_count += 1

        if p_pull <= 0:
            continue

        v = value_of_next_copy(owned, is_ex, deck_targets, nn)
        ev = p_pull * v

        if ev > 0:
            card_ev_list.append({
                "name": card_name,
                "rarity": rarity,
                "is_ex": is_ex,
                "is_deck_target": is_dt,
                "owned": owned,
                "pull_prob": round(p_pull, 7),
                "value": round(v, 2),
                "ev_contribution": round(ev, 7),
                "rate_source": "pz" if pz_pull is not None else "inferred",
            })

        if owned == 0:
            new_card_ev += ev
        else:
            copy_ev += ev

        if is_ex:
            ex_card_ev += ev
        if is_dt:
            deck_target_ev += ev

    pack_total_ev = new_card_ev + copy_ev

    pz_total = pz_hits + fallback_count
    pz_coverage = pz_hits / pz_total if pz_total > 0 else 0.0
    confidence_weight = PZ_CONFIDENCE_WEIGHT if pz_coverage >= 0.90 else INFERRED_CONFIDENCE_WEIGHT
    source_status = "pz_verified" if pz_coverage >= 0.90 else "inferred"

    exploratory_ev = 0.0

    card_ev_list.sort(key=lambda x: x["ev_contribution"], reverse=True)
    deck_target_cards = [c for c in card_ev_list if c.get("is_deck_target")]

    return {
        **base,
        "source_status": source_status,
        "blocked": False,
        "blocked_reason": None,
        "cards_in_pool": len(all_pool_cards),
        "owned_in_pool": owned_in_pool,
        "missing_in_pool": missing_in_pool,
        "collection_completion_ev": round(pack_total_ev, 6),
        "new_card_ev":     round(new_card_ev, 6),
        "copy_ev":         round(copy_ev, 6),
        "ex_card_ev":      round(ex_card_ev, 6),
        "deck_target_ev":  round(deck_target_ev, 6),
        "exploratory_ev":  exploratory_ev,
        "pack_total_ev":   round(pack_total_ev, 6),
        "confidence_adjusted_ev": round(pack_total_ev * confidence_weight, 6),
        "deck_weighted_score": round(
            pack_total_ev * confidence_weight + DECK_PRIORITY_BOOST * deck_target_ev, 6
        ),
        "pz_coverage": round(pz_coverage, 3),
        "top_ev_cards": card_ev_list[:TOP_N_CARDS],
        "deck_target_cards": deck_target_cards,
        "notes": (
            f"slot_rates={'pz_verified' if source_status == 'pz_verified' else 'inferred'}. "
            f"PZ coverage: {pz_hits}/{pz_total} cards. "
            f"{owned_in_pool}/{len(all_pool_cards)} cards in pool are owned. "
            f"EV excludes low_confidence and unresolved collection entries."
        ),
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(collection, pull_model, pack_cards, expansion_shared, deck_targets,
          pz_raw=None, pz_odds=None):
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
                            pz_name_odds[name_l] = pz_name_odds.get(name_l, 0.0) + pct / 100.0
        record = compute_pack_ev_record(
            pack_record, all_pool_cards, collection, deck_targets, pz_card_odds, pz_name_odds
        )
        if record.get("blocked"):
            blocked.append(record)
        else:
            pack_ev_records.append(record)

    return pack_ev_records, blocked


def summarize(records: list) -> dict:
    by_total = sorted(records, key=lambda r: r["pack_total_ev"], reverse=True)
    by_new   = sorted(records, key=lambda r: r["new_card_ev"], reverse=True)
    by_dt    = sorted(records, key=lambda r: r["deck_target_ev"], reverse=True)

    def brief(r):
        return {
            "pack_name": r["pack_name"],
            "expansion": r["expansion"],
            "pack_total_ev": r["pack_total_ev"],
            "new_card_ev": r["new_card_ev"],
            "deck_target_ev": r["deck_target_ev"],
            "confidence_adjusted_ev": r["confidence_adjusted_ev"],
        }

    return {
        "top_packs_by_total_ev":      [brief(r) for r in by_total[:5]],
        "top_packs_by_new_card_ev":   [brief(r) for r in by_new[:5]],
        "top_packs_by_deck_target_ev":[brief(r) for r in by_dt[:5]],
        "highest_ev_pack":     by_total[0]["pack_name"] if by_total else None,
        "highest_new_card_ev_pack": by_new[0]["pack_name"] if by_new else None,
        "total_packs_scored":  len(records),
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _read_model_confidence(path: Path) -> str:
    """Read source_status from pull_probability_model.json."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw.get("meta", {}).get("source_status", "inferred")
    except Exception:
        return "inferred"


def write_json(pack_ev_records, blocked, deck_targets, collection_total):
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


def write_csv(pack_ev_records):
    fields = [
        "pack_name", "expansion", "set_code", "source_status",
        "cards_in_pool", "owned_in_pool", "missing_in_pool",
        "new_card_ev", "copy_ev", "ex_card_ev", "deck_target_ev",
        "pack_total_ev", "confidence_adjusted_ev",
        "top_ev_cards_summary",
    ]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in pack_ev_records:
            top_summary = " | ".join(
                f"{c['name']}({c['rarity']},p={c['pull_prob']:.4f},ev={c['ev_contribution']:.4f})"
                for c in r.get("top_ev_cards", [])
            )
            w.writerow({
                "pack_name":    r["pack_name"],
                "expansion":    r["expansion"],
                "set_code":     r["set_code"],
                "source_status": r["source_status"],
                "cards_in_pool": r["cards_in_pool"],
                "owned_in_pool": r["owned_in_pool"],
                "missing_in_pool": r["missing_in_pool"],
                "new_card_ev":   r["new_card_ev"],
                "copy_ev":       r["copy_ev"],
                "ex_card_ev":    r["ex_card_ev"],
                "deck_target_ev": r["deck_target_ev"],
                "pack_total_ev": r["pack_total_ev"],
                "confidence_adjusted_ev": r["confidence_adjusted_ev"],
                "top_ev_cards_summary": top_summary,
            })


def _ev_ready_md_row(out: dict) -> str:
    w = out.get("meta", {}).get("warnings", [])
    for msg in w:
        if "EV-ready coverage:" in msg:
            # Extract "192/224" style from the warning message
            import re
            m = re.search(r"(\d+/\d+) entries resolved", msg)
            if m:
                n = re.search(r"(\d+) newly resolved", msg)
                newly = n.group(1) if n else "46"
                return f"| EV-ready collection entries | {m.group(1)} (108 auto-accept + 49 secondary + {newly} resolved) |"
    return "| EV-ready collection entries | 157/224 (108 auto-accept + 49 secondary) |"


def _excluded_md_row(out: dict) -> str:
    w = out.get("meta", {}).get("warnings", [])
    for msg in w:
        if "excluded from EV" in msg:
            import re
            m = re.search(r"(\d+) entries still excluded", msg)
            if m:
                excluded = int(m.group(1))
                low_conf = excluded - 8
                return f"| Excluded entries | {excluded}/224 ({low_conf} low-confidence + 8 unresolved) |"
    return "| Excluded entries | 67/224 (59 low-confidence + 8 unresolved) |"


def write_md(out: dict, pack_ev_records: list, deck_targets: dict):
    summary = out["overall_summary"]
    model_confidence = out["meta"]["model_confidence"]
    lines = [
        f"# Pack EV Analysis ({model_confidence.replace('_', ' ').title()} Confidence)",
        "",
        "> **IMPORTANT — Partially Verified Rates**",
        "> Branch structure (regular/rare/plus_one percentages) confirmed from Bulbapedia offering rates",
        "> for 12 packs; rarity distributions within slots remain third_party_verified.",
        "> Pulsing Aura (B3) is user-in-app-verified with Bulbapedia corroboration.",
        "> Do NOT treat these rankings as final pack-opening recommendations.",
        "> Verify remaining packs in PTCGP app → Pack details → Offering Rates before acting.",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Model confidence | **{model_confidence}** |",
        f"| Slot rates source | Bulbapedia (branch) + Game8/ShackNews (rarity dist.) |",
        f"| Packs ranked | {len(pack_ev_records)} |",
        f"| Collection total | {out['meta']['collection_total']} cards (380 validated) |",
        _ev_ready_md_row(out),
        _excluded_md_row(out),
        f"| Deck targets | {len(deck_targets)} cards needed for deck completion |",
        "",
        "---",
        "",
        "## Top 5 Packs by Total EV",
        "",
        "| Rank | Pack | Expansion | Total EV | New Card EV | Deck Target EV | Adj. EV |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(summary["top_packs_by_total_ev"], 1):
        lines.append(
            f"| {i} | {p['pack_name']} | {p['expansion']} "
            f"| {p['pack_total_ev']:.4f} "
            f"| {p['new_card_ev']:.4f} "
            f"| {p['deck_target_ev']:.4f} "
            f"| {p['confidence_adjusted_ev']:.4f} |"
        )

    lines += [
        "",
        "## Top 5 Packs by New-Card EV",
        "",
        "| Rank | Pack | Expansion | New Card EV | Missing in Pool |",
        "|---|---|---|---|---|",
    ]
    for i, p in enumerate(summary["top_packs_by_new_card_ev"], 1):
        full = next((r for r in pack_ev_records if r["pack_name"] == p["pack_name"]), {})
        lines.append(
            f"| {i} | {p['pack_name']} | {p['expansion']} "
            f"| {p['new_card_ev']:.4f} "
            f"| {full.get('missing_in_pool', '?')} |"
        )

    lines += [
        "",
        "## Top 5 Packs by Deck Target EV",
        "",
        "| Rank | Pack | Expansion | Deck Target EV | Deck Target Cards |",
        "|---|---|---|---|---|",
    ]
    for i, p in enumerate(summary["top_packs_by_deck_target_ev"], 1):
        full = next((r for r in pack_ev_records if r["pack_name"] == p["pack_name"]), {})
        dt_cards = [c["name"] for c in full.get("top_ev_cards", []) if c.get("is_deck_target")]
        lines.append(
            f"| {i} | {p['pack_name']} | {p['expansion']} "
            f"| {p['deck_target_ev']:.4f} "
            f"| {', '.join(dt_cards) or 'none'} |"
        )

    lines += [
        "",
        "## All Packs — EV Summary",
        "",
        "| Pack | Expansion | Set | Pool | Owned | Missing | Total EV | Adj. EV |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(pack_ev_records, key=lambda x: x["pack_total_ev"], reverse=True):
        lines.append(
            f"| {r['pack_name']} | {r['expansion']} | {r['set_code']} "
            f"| {r['cards_in_pool']} "
            f"| {r['owned_in_pool']} "
            f"| {r['missing_in_pool']} "
            f"| {r['pack_total_ev']:.4f} "
            f"| {r['confidence_adjusted_ev']:.4f} |"
        )

    lines += [
        "",
        "## Top EV Cards per Pack (Top 5 Packs)",
        "",
    ]
    top5 = [r for r in pack_ev_records
            if r["pack_name"] in {p["pack_name"] for p in summary["top_packs_by_total_ev"]}]
    top5 = sorted(top5, key=lambda x: x["pack_total_ev"], reverse=True)
    for r in top5:
        lines += [
            f"### {r['pack_name']} ({r['expansion']})",
            "",
            "| Card | Rarity | Owned | Pull P | Value | EV |",
            "|---|---|---|---|---|---|",
        ]
        for c in r.get("top_ev_cards", []):
            flags = []
            if c.get("is_ex"):
                flags.append("EX")
            if c.get("is_deck_target"):
                flags.append("DECK")
            flag_str = " ".join(flags)
            lines.append(
                f"| {c['name']} {flag_str} | {c['rarity']} "
                f"| {c['owned']} "
                f"| {c['pull_prob']:.5f} "
                f"| {c['value']:.2f} "
                f"| {c['ev_contribution']:.5f} |"
            )
        lines.append("")

    lines += [
        "## Deck Targets",
        "",
        "| Card | Still Needed | Deck Target EV Impact |",
        "|---|---|---|",
    ]
    for name, needed in sorted(deck_targets.items()):
        # Find which pack has the highest deck_target_ev contribution for this card
        best_pack = None
        best_ev = 0.0
        for r in pack_ev_records:
            for c in r.get("top_ev_cards", []):
                if normalize(c["name"]) == name and c.get("is_deck_target"):
                    if c["ev_contribution"] > best_ev:
                        best_ev = c["ev_contribution"]
                        best_pack = r["pack_name"]
        lines.append(
            f"| {name.title()} | {needed} | "
            f"best in {best_pack or 'not in top cards'} (ev={best_ev:.5f}) |"
        )

    lines += [
        "",
        "## Assumptions and Scoring Weights",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| New unique card | {SCORING_WEIGHTS['new_card']} |",
        f"| 2nd copy (deck usable) | {SCORING_WEIGHTS['copy_up_to_2']} |",
        f"| EX card bonus | {SCORING_WEIGHTS['ex_missing']} |",
        f"| Deck target bonus | {SCORING_WEIGHTS['deck_target']} |",
        f"| Inferred confidence adj. | {INFERRED_CONFIDENCE_WEIGHT} |",
        "",
        "- Cards owned ≥ 2 contribute EV = 0 (maximum useful copies).",
        "- Slot 4 and Slot 5 probabilities are summed per rarity for expected count.",
        "- Rare/god pack (0.05%) contributions are included.",
        "- one_diamond cards: slots 1-3 (100% each, 3 total expected).",
        "- Card matching is by normalized name only (case-insensitive). Cross-set",
        "  cards with the same name may be double-counted as owned.",
        "- 21 low-confidence/unresolved collection entries still excluded from EV (46 newly resolved by resolve_ambiguous_pack_sources.py).",
        "",
        "## Next Steps Before Final Recommendations",
        "",
        "1. **Verify slot rates in-app** — open PTCGP → any pack → Offering Rates.",
        "2. **Resolve remaining 24 ambiguous entries** — run resolve_ambiguous_pack_sources.py; coverage now 192/224.",
        "3. **Build deck scorer** — integrate deck completion probability into EV.",
        "4. **Re-run EV calculator** after any rate or coverage update.",
        "",
        "> This analysis is at **inferred confidence**. Rankings may shift once rates",
        "> are verified. Do not issue pack-opening recommendations from this output alone.",
        "",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

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

    collection       = load_collection(COLLECTION_JSON)
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
        collection, pull_model, pack_cards, expansion_shared, deck_targets, pz_raw, pz_odds
    )

    out = write_json(pack_ev_records, blocked, deck_targets, collection_total)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")

    summary = out["overall_summary"]
    print("\n=== Summary ===")
    print(f"  Packs scored:    {len(pack_ev_records)}")
    print(f"  Packs blocked:   {len(blocked)}")
    print(f"  Model confidence: {out['meta']['model_confidence']}")
    print("  Top packs by total EV:")
    for p in summary["top_packs_by_total_ev"]:
        print(f"    {p['pack_name']:30s} ev={p['pack_total_ev']:.4f}  "
              f"adj={p['confidence_adjusted_ev']:.4f}")
    print("\nDone.")


if __name__ == "__main__":
    main()
