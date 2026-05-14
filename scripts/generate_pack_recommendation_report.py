#!/usr/bin/env python3
"""
Generate a human-readable inferred-confidence pack recommendation report.

Reads from existing EV outputs — does NOT recompute EV.
Does NOT mutate collection.json or cards.json.

IMPORTANT: All outputs are at INFERRED confidence.
Slot rates are from external sources, not verified in-app.
These are planning inputs, not final recommendations.

Inputs:
    data/current/pack_ev.json
    data/current/pack_ev_readiness.json
    data/current/pack_source_confidence_scores.json
    data/current/collection_normalized.json
    data/exports/deck_recommendation_validation.json

Outputs:
    review/inferred_pack_recommendations.md
    data/current/inferred_pack_recommendations.json
    data/exports/inferred_pack_recommendations.csv

Usage:
    python3 scripts/generate_pack_recommendation_report.py
    python3 scripts/generate_pack_recommendation_report.py --validate
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACK_EV_JSON         = ROOT / "data" / "current"  / "pack_ev.json"
EV_READINESS_JSON    = ROOT / "data" / "current"  / "pack_ev_readiness.json"
CONFIDENCE_JSON      = ROOT / "data" / "current"  / "pack_source_confidence_scores.json"
COLLECTION_JSON      = ROOT / "data" / "current"  / "collection_normalized.json"
DECK_VALIDATION_JSON = ROOT / "data" / "exports"  / "deck_recommendation_validation.json"
COLLECTION_SOURCE    = ROOT / "collection.json"
CARDS_SOURCE         = ROOT / "cards.json"

OUT_MD   = ROOT / "review"         / "inferred_pack_recommendations.md"
OUT_JSON = ROOT / "data" / "current" / "inferred_pack_recommendations.json"
OUT_CSV  = ROOT / "data" / "exports" / "inferred_pack_recommendations.csv"

TOP_N = 5


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_ev(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_deck_validation(path: Path) -> list:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("decks", [])


def load_confidence_meta(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("meta", {})


def load_ev_readiness(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def rank_packs(packs: list, key: str, n: int = TOP_N) -> list:
    return sorted(packs, key=lambda p: p.get(key, 0.0), reverse=True)[:n]


def deck_target_pack_map(packs: list) -> dict:
    """
    Returns {card_name: [(pack_name, ev_contribution, pull_prob, owned)]}.
    Only includes deck-target cards that appear in at least one pack's top_ev_cards.
    """
    out = {}
    for p in packs:
        for c in p.get("top_ev_cards", []):
            if c.get("is_deck_target"):
                name = c["name"]
                if name not in out:
                    out[name] = []
                out[name].append({
                    "pack_name": p["pack_name"],
                    "expansion": p["expansion"],
                    "ev_contribution": c["ev_contribution"],
                    "pull_prob": c["pull_prob"],
                    "owned": c["owned"],
                    "rarity": c["rarity"],
                    "value": c["value"],
                })
    # Sort each card's pack list by ev_contribution descending
    for name in out:
        out[name].sort(key=lambda x: x["ev_contribution"], reverse=True)
    return out


def build_buckets(packs: list, deck_targets: dict, deck_validation: list) -> dict:
    """Build recommendation buckets from EV data."""
    by_adj_ev   = rank_packs(packs, "confidence_adjusted_ev")
    by_total_ev = rank_packs(packs, "pack_total_ev")
    by_new_card = rank_packs(packs, "new_card_ev")
    by_dt       = rank_packs(packs, "deck_target_ev")
    by_ex       = rank_packs(packs, "ex_card_ev")

    # Deprioritize: lowest adjusted EV + low missing count
    by_adj_asc  = sorted(packs, key=lambda p: p["confidence_adjusted_ev"])[:5]

    # Chase deck specifics: which packs contain the missing deck-target cards
    chase_decks = [d for d in deck_validation if not d.get("fully_buildable")]
    best_for_chase = {}
    for deck in chase_decks:
        deck_name = deck["name"]
        for mc in deck.get("missing_cards", []):
            card_name = mc["name"]
            if card_name in deck_targets:
                entries = deck_targets[card_name]
                best_for_chase[deck_name] = {
                    "card_needed": card_name,
                    "short_by": mc["short_by"],
                    "best_pack": entries[0]["pack_name"] if entries else None,
                    "best_ev": entries[0]["ev_contribution"] if entries else 0.0,
                    "best_pull_prob": entries[0]["pull_prob"] if entries else 0.0,
                    "candidates": entries,
                }
            else:
                best_for_chase[deck_name] = {
                    "card_needed": card_name,
                    "short_by": mc["short_by"],
                    "best_pack": None,
                    "best_ev": 0.0,
                    "best_pull_prob": 0.0,
                    "candidates": [],
                    "note": "card not found in pack_sources — pack unknown",
                }

    return {
        "best_overall_adj_ev": by_adj_ev,
        "best_total_ev": by_total_ev,
        "best_new_card_ev": by_new_card,
        "best_deck_target_ev": by_dt,
        "best_ex_ev": by_ex,
        "deprioritize": by_adj_asc,
        "chase_deck_packs": best_for_chase,
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_json(ev_data: dict, buckets: dict, conf_meta: dict, ev_readiness: dict) -> dict:
    packs = ev_data["packs"]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "generate_pack_recommendation_report.py",
        "disclaimer": (
            "INFERRED CONFIDENCE ONLY. Slot rates are from trusted external sources "
            "(Game8, ShackNews, cgmagonline) — NOT verified from the in-app Offering "
            "Rates screen. Rankings are for planning purposes only. Verify in-app before "
            "acting on any recommendation."
        ),
        "model_confidence": ev_data["meta"]["model_confidence"],
        "collection_total": ev_data["meta"]["collection_total"],
        "collection_mutated": False,
        "ev_ready_entries": {
            "total": conf_meta.get("total_entries", 0),
            "auto_accept": conf_meta.get("tier_counts", {}).get("auto_accept", 0),
            "secondary_evidence": conf_meta.get("tier_counts", {}).get("secondary_evidence", 0),
            "low_confidence_excluded": conf_meta.get("tier_counts", {}).get("low_confidence", 0),
            "unresolved_excluded": conf_meta.get("tier_counts", {}).get("unresolved", 0),
        },
        "top_5_by_adjusted_ev": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["best_overall_adj_ev"]
        ],
        "top_5_by_new_card_ev": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["best_new_card_ev"]
        ],
        "top_5_by_deck_target_ev": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["best_deck_target_ev"]
        ],
        "top_5_by_ex_ev": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["best_ex_ev"]
        ],
        "deprioritize_5": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["deprioritize"]
        ],
        "chase_deck_packs": buckets["chase_deck_packs"],
        "planning_scenarios": {
            "conservative": {
                "label": "Wait for in-app verification",
                "description": (
                    "Do not open any packs yet. Verify slot rates in PTCGP app "
                    "(Pack details → Offering Rates). If rates match inferred values, "
                    "upgrade to verified confidence and run the EV calculator again. "
                    "Only then act on rankings."
                ),
            },
            "moderate": {
                "label": "Accept inferred confidence — limited opens",
                "description": (
                    "Accept that inferred rates may be off by a small margin (~15% "
                    "confidence adjustment applied). Open 10 pulls from the top-adjusted-EV "
                    "pack only. Recommended starting pack: Paldean Wonders (adj EV=4.20). "
                    "If a specific deck target is the goal, open Crimson Blaze for Ivysaur "
                    "or Solgaleo for Incineroar ex instead."
                ),
                "suggested_pack": buckets["best_overall_adj_ev"][0]["pack_name"] if buckets["best_overall_adj_ev"] else None,
            },
            "aggressive": {
                "label": "Accept inferred confidence — prioritize top EV packs",
                "description": (
                    "Focus pack openings on the top 2–3 adjusted-EV packs. "
                    "These packs have the most missing cards relative to their pool size. "
                    "High miss rate means high per-pull value at current collection state. "
                    "Rankings will shift as collection grows. Re-run EV calculator after "
                    "every 20+ pulls."
                ),
                "suggested_packs": [p["pack_name"] for p in buckets["best_overall_adj_ev"][:3]],
            },
        },
        "blockers": {
            "inferred_rates": {
                "severity": "HIGH",
                "description": (
                    "Slot rates not verified in-app. All EVs adjusted by 0.85 to reflect "
                    "this uncertainty. Actual EVs may be higher or lower."
                ),
                "fix": "PTCGP app → Pack details → Offering Rates",
            },
            "ambiguous_entries": {
                "severity": "MEDIUM",
                "description": (
                    "59 collection entries are low-confidence (card appears in multiple "
                    "expansions with no confirmed set). These are excluded from EV. "
                    "Resolving them could shift rankings."
                ),
                "fix": "Fill data/exports/current_pack_source_review.csv",
            },
            "zygarde_unknown_pack": {
                "severity": "MEDIUM",
                "description": (
                    "Zygarde ex is not in pack_sources.json — its source pack is unknown. "
                    "Cannot calculate pull probability. One chase deck (Zygarde ex Fighting) "
                    "cannot be targeted by pack selection."
                ),
                "fix": "Identify Zygarde ex set from external reference or in-app",
            },
            "deck_scorer_not_automated": {
                "severity": "LOW",
                "description": (
                    "Deck completion probability is not integrated into EV. "
                    "deck_target_ev only reflects the value of the missing card(s), "
                    "not the full deck completion probability uplift."
                ),
                "fix": "Build automated deck scorer as a future phase",
            },
        },
        "next_actions": [
            "PRIORITY 1: Verify slot rates in-app (PTCGP → any pack → Offering Rates). "
            "If they match, set confidence=verified in pull_probability_model.json.",
            "PRIORITY 2: If accepting inferred confidence, open Paldean Wonders "
            "(best overall adjusted EV) or Crimson Blaze (best for Mega Venusaur ex chase deck).",
            "PRIORITY 3: Resolve 59 ambiguous collection entries "
            "(fill data/exports/current_pack_source_review.csv) to expand EV coverage.",
            "PRIORITY 4: Identify Zygarde ex pack source to enable Zygarde ex Fighting deck targeting.",
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_csv(ev_data: dict, buckets: dict):
    fields = [
        "rank_adj_ev", "pack_name", "expansion", "set_code",
        "confidence_adjusted_ev", "pack_total_ev", "new_card_ev",
        "ex_card_ev", "deck_target_ev",
        "cards_in_pool", "owned_in_pool", "missing_in_pool",
        "is_deck_target_pack", "top_deck_target_card",
        "recommendation_bucket",
    ]
    packs = ev_data["packs"]
    by_adj = sorted(packs, key=lambda p: p["confidence_adjusted_ev"], reverse=True)
    dt_pack_names = {p["pack_name"] for p in buckets["best_deck_target_ev"]}

    # Build a lookup for best deck target card per pack
    dt_card_lookup = {}
    for card_name, entries in buckets.get("chase_deck_packs", {}).items():
        if isinstance(entries, dict) and entries.get("best_pack"):
            pk = entries["best_pack"]
            dt_card_lookup[pk] = entries["card_needed"]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, p in enumerate(by_adj, 1):
            bucket = "top_ev" if i <= 5 else ("deprioritize" if i > len(by_adj) - 5 else "mid")
            if p["pack_name"] in dt_pack_names:
                bucket = "deck_target"
            w.writerow({
                "rank_adj_ev": i,
                "pack_name": p["pack_name"],
                "expansion": p["expansion"],
                "set_code": p["set_code"],
                "confidence_adjusted_ev": p["confidence_adjusted_ev"],
                "pack_total_ev": p["pack_total_ev"],
                "new_card_ev": p["new_card_ev"],
                "ex_card_ev": p["ex_card_ev"],
                "deck_target_ev": p["deck_target_ev"],
                "cards_in_pool": p["cards_in_pool"],
                "owned_in_pool": p["owned_in_pool"],
                "missing_in_pool": p["missing_in_pool"],
                "is_deck_target_pack": "yes" if p["pack_name"] in dt_pack_names else "no",
                "top_deck_target_card": dt_card_lookup.get(p["pack_name"], ""),
                "recommendation_bucket": bucket,
            })


def write_md(out_data: dict, ev_data: dict, buckets: dict, deck_validation: list):
    packs = ev_data["packs"]
    top5 = buckets["best_overall_adj_ev"]

    def pack_detail(p: dict) -> list:
        lines = []
        lines.append(f"**{p['pack_name']}** ({p['expansion']})")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Adjusted EV (×0.85) | **{p['confidence_adjusted_ev']:.4f}** |")
        lines.append(f"| Total EV (raw) | {p['pack_total_ev']:.4f} |")
        lines.append(f"| New-card EV | {p['new_card_ev']:.4f} |")
        lines.append(f"| EX-card EV | {p['ex_card_ev']:.4f} |")
        lines.append(f"| Deck target EV | {p['deck_target_ev']:.4f} |")
        lines.append(f"| Pool size | {p['cards_in_pool']} cards |")
        lines.append(f"| Already owned in pool | {p['owned_in_pool']} |")
        lines.append(f"| Missing from pool | **{p['missing_in_pool']}** |")
        lines.append("")
        top_cards = p.get("top_ev_cards", [])
        if top_cards:
            lines.append("Top EV cards in this pack:")
            lines.append("")
            lines.append("| Card | Rarity | Owned | Pull P | Value | EV |")
            lines.append("|---|---|---|---|---|---|")
            for c in top_cards:
                flags = []
                if c.get("is_ex"):
                    flags.append("EX")
                if c.get("is_deck_target"):
                    flags.append("DECK TARGET")
                flag_str = " · ".join(flags)
                name_str = f"{c['name']}" + (f" _{flag_str}_" if flag_str else "")
                lines.append(
                    f"| {name_str} | {c['rarity']} "
                    f"| {c['owned']} "
                    f"| {c['pull_prob']:.5f} "
                    f"| {c['value']:.2f} "
                    f"| {c['ev_contribution']:.5f} |"
                )
        return lines

    lines = [
        "# Inferred Pack Recommendation Report",
        "",
        "> ## ⚠ INFERRED CONFIDENCE — NOT VERIFIED",
        ">",
        "> Slot rates sourced from Game8 PTCGP guide and corroborating sites.",
        "> These rates have **NOT been verified** against the in-app Offering Rates screen.",
        "> All EV values are adjusted by ×0.85 to reflect this uncertainty.",
        ">",
        "> **Do not treat this as a final pack-opening recommendation.**",
        "> Verify slot rates in the PTCGP app first:",
        "> App → any pack → Pack details → Offering Rates",
        ">",
        "> This report is decision-support for planning purposes only.",
        "",
        "---",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Report generated | {out_data['generated_at']} |",
        f"| Model confidence | **{out_data['model_confidence']}** (not official in-app verified) |",
        f"| Collection total | {out_data['collection_total']} cards (380 validated) |",
        f"| EV-ready entries | 157/224 (108 auto-accept + 49 secondary evidence) |",
        f"| Excluded from EV | 67/224 (59 low-confidence + 8 unresolved) |",
        f"| Packs ranked | {len(packs)} |",
        f"| Packs blocked | {len(ev_data.get('blocked_packs', []))} |",
        "",
        "---",
        "",
        "## Top 5 Packs — All Metrics",
        "",
        "| Rank | Pack | Expansion | Adj. EV | Total EV | New EV | Deck EV | EX EV | Missing |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    all_sorted = sorted(packs, key=lambda p: p["confidence_adjusted_ev"], reverse=True)
    for i, p in enumerate(all_sorted[:TOP_N], 1):
        lines.append(
            f"| {i} | **{p['pack_name']}** | {p['expansion']} "
            f"| {p['confidence_adjusted_ev']:.4f} "
            f"| {p['pack_total_ev']:.4f} "
            f"| {p['new_card_ev']:.4f} "
            f"| {p['deck_target_ev']:.4f} "
            f"| {p['ex_card_ev']:.4f} "
            f"| {p['missing_in_pool']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Recommendation Buckets",
        "",
        "### Best Overall Inferred EV",
        "",
        "These packs have the highest expected number of new unique cards per pull,",
        "adjusted for inferred-rate uncertainty.",
        "",
        "| Rank | Pack | Adj. EV | Why |",
        "|---|---|---|---|",
    ]

    explanations = {
        "Paldean Wonders": "Large pool, very few owned (3/131). Almost every pull is new.",
        "Fantastical Parade": "Largest pool (234 cards), 205 missing. Highest raw volume of new cards.",
        "Mew": "Small dense pool (86 cards), 77 missing — high hit rate per pull.",
        "Extradimensional Crisis": "Medium pool, low ownership (13/103). Consistent new-card rate.",
        "Mega Altaria": "Large pool (139), 119 missing. Strong EX cards present.",
    }
    for i, p in enumerate(buckets["best_overall_adj_ev"], 1):
        why = explanations.get(p["pack_name"], "High new-card EV relative to pool size.")
        lines.append(f"| {i} | {p['pack_name']} | {p['confidence_adjusted_ev']:.4f} | {why} |")

    lines += [
        "",
        "### Best for Collection Completion",
        "",
        "Ranked by new_card_ev — these packs return the most new unique cards per pull.",
        "",
        "| Rank | Pack | New Card EV | Missing in Pool |",
        "|---|---|---|---|",
    ]
    for i, p in enumerate(buckets["best_new_card_ev"], 1):
        lines.append(f"| {i} | {p['pack_name']} | {p['new_card_ev']:.4f} | {p['missing_in_pool']} |")

    lines += [
        "",
        "### Best for Deck Targets",
        "",
        "Ranked by deck_target_ev — these packs contain the highest-value missing deck cards.",
        "Only Ivysaur (two_diamond) is in the top deck-target packs.",
        "Incineroar ex is in Solgaleo. Magnezone ex is in Pulsing Aura.",
        "Zygarde ex has **no known pack** — not in pack_sources.json.",
        "",
        "| Rank | Pack | Deck Target EV | Notes |",
        "|---|---|---|---|",
    ]
    dt_notes = {
        "Crimson Blaze": "Contains Ivysaur (two_diamond) — best for Mega Venusaur ex",
        "Mewtwo": "Contains Ivysaur (two_diamond) — alternative Mega Venusaur ex route",
        "Deluxe Pack: ex": "Contains Ivysaur but low per-card rate (large pool, 379 cards)",
        "Solgaleo": "Contains Incineroar ex (four_diamond) — best for Incineroar ex chase deck",
        "Pulsing Aura": "Contains Magnezone ex — best for Magnezone ex chase deck",
    }
    for i, p in enumerate(buckets["best_deck_target_ev"], 1):
        note = dt_notes.get(p["pack_name"], "")
        lines.append(f"| {i} | {p['pack_name']} | {p['deck_target_ev']:.4f} | {note} |")

    lines += [
        "",
        "### Best for EX / Card Power",
        "",
        "Ranked by ex_card_ev — these packs contain the most missing EX cards.",
        "",
        "| Rank | Pack | EX Card EV |",
        "|---|---|---|",
    ]
    for i, p in enumerate(buckets["best_ex_ev"], 1):
        lines.append(f"| {i} | {p['pack_name']} | {p['ex_card_ev']:.4f} |")

    lines += [
        "",
        "### Packs to Deprioritize",
        "",
        "These packs have the lowest adjusted EV — most cards in the pool are already owned.",
        "",
        "| Rank | Pack | Adj. EV | Owned/Pool | Notes |",
        "|---|---|---|---|---|",
    ]
    deprio_notes = {
        "Crimson Blaze": "High deck-target value offsets low general EV — open only if chasing Ivysaur",
        "Pulsing Aura": "Contains Magnezone ex — open only if chasing that deck",
        "Mewtwo": "Higher EV than Crimson Blaze/Pulsing Aura; only deprioritized vs top packs",
        "Arceus": "Mid-range owned ratio",
    }
    for i, p in enumerate(buckets["deprioritize"], 1):
        owned_str = f"{p['owned_in_pool']}/{p['cards_in_pool']}"
        note = deprio_notes.get(p["pack_name"], "Low new-card return relative to pool")
        lines.append(f"| {i} | {p['pack_name']} | {p['confidence_adjusted_ev']:.4f} | {owned_str} | {note} |")

    lines += [
        "",
        "---",
        "",
        "## Pack Detail — Top 5 by Adjusted EV",
        "",
    ]
    for p in buckets["best_overall_adj_ev"]:
        lines += pack_detail(p)
        lines.append("")
        lines.append("---")
        lines.append("")

    lines += [
        "## Chase Deck Pack Guide",
        "",
        "| Chase Deck | Missing Card | Short By | Best Pack | Pack EV | Pull Prob | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    chase_decks_order = ["Mega Venusaur ex", "Incineroar ex", "Zygarde ex Fighting", "Magnezone ex (Clemont Engine)"]
    for deck_name in chase_decks_order:
        info = buckets["chase_deck_packs"].get(deck_name, {})
        if not info:
            continue
        card = info.get("card_needed", "?")
        short_by = info.get("short_by", 1)
        best_pack = info.get("best_pack") or "**UNKNOWN**"
        best_ev = info.get("best_ev", 0.0)
        best_pp = info.get("best_pull_prob", 0.0)
        note = info.get("note", "")
        if not note and not info.get("best_pack"):
            note = "not in pack_sources"
        pp_str = f"{best_pp:.5f}" if best_pp > 0 else "N/A"
        ev_str = f"{best_ev:.5f}" if best_ev > 0 else "N/A"
        lines.append(
            f"| {deck_name} | {card} | {short_by} | {best_pack} "
            f"| {ev_str} | {pp_str} | {note} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Planning Scenarios",
        "",
        "> These are scenarios for your consideration — not instructions.",
        "> All scenarios assume inferred-confidence slot rates.",
        "",
        "### Scenario A — Conservative: Wait for In-App Verification",
        "",
        "**Action:** No pack opens until slot rates are verified in PTCGP app.",
        "",
        "**How:** Open PTCGP → any pack → Pack details → Offering Rates.",
        "Compare the displayed percentages against `slot_rates` in",
        "`data/reference/pull_probability_model.json`.",
        "",
        "If rates match: set `confidence=verified` in the model, re-run",
        "`python3 scripts/build_pack_ev.py`, then return to this report for final rankings.",
        "",
        "**Tradeoff:** Delays pack decisions but eliminates rate uncertainty.",
        "",
        "### Scenario B — Moderate: Limited Opens at Inferred Confidence",
        "",
        "**Action:** Open up to ~10 pulls from one pack, accepting the ~15% rate uncertainty.",
        "",
        "**Suggested pack:** Paldean Wonders (adj EV=4.20) for general collection growth.",
        "**Alternate:** Crimson Blaze if the Mega Venusaur ex chase deck is the priority.",
        "**Alternate:** Solgaleo if the Incineroar ex chase deck is the priority.",
        "",
        "**Tradeoff:** Some risk of suboptimal pulls if inferred rates are wrong, but EV",
        "rankings are broadly stable — a pack ranked #1 at inferred confidence is very",
        "unlikely to be worst at verified confidence.",
        "",
        "### Scenario C — Aggressive: Maximize EV at Inferred Confidence",
        "",
        "**Action:** Focus all pack opens on the top 2–3 adjusted-EV packs.",
        "",
        "**Suggested priority order:**",
        "1. Paldean Wonders (adj EV=4.20) — most missing cards relative to pool",
        "2. Fantastical Parade (adj EV=3.82) — highest absolute missing count (205)",
        "3. Mew (adj EV=3.78) — small focused pool, very high completion rate",
        "",
        "**Important:** EV rankings change as the collection grows. After every 20+ pulls,",
        "re-run `python3 scripts/build_pack_ev.py` and regenerate this report.",
        "",
        "**Tradeoff:** Optimizes collection growth but ignores deck-target priority.",
        "If completing a specific chase deck matters more, see Scenario B.",
        "",
        "---",
        "",
        "## Complete Pack Ranking",
        "",
        "| Rank | Pack | Expansion | Adj. EV | Total EV | New EV | Missing | Deck EV | EX EV |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(all_sorted, 1):
        lines.append(
            f"| {i} | {p['pack_name']} | {p['expansion']} "
            f"| {p['confidence_adjusted_ev']:.4f} "
            f"| {p['pack_total_ev']:.4f} "
            f"| {p['new_card_ev']:.4f} "
            f"| {p['missing_in_pool']} "
            f"| {p['deck_target_ev']:.4f} "
            f"| {p['ex_card_ev']:.4f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Blockers Before Verified Recommendations",
        "",
        "| Blocker | Severity | Fix |",
        "|---|---|---|",
        "| Slot rates not verified in-app | **HIGH** | PTCGP app → Pack details → Offering Rates |",
        "| 59 ambiguous collection entries excluded from EV | MEDIUM | Fill data/exports/current_pack_source_review.csv |",
        "| Zygarde ex not in pack_sources (unknown pack) | MEDIUM | Identify Zygarde ex set from external reference |",
        "| Deck completion probability not integrated | LOW | Future: build automated deck scorer |",
        "",
        "---",
        "",
        "## Next Actions",
        "",
        "1. **Verify slot rates in-app** (highest impact) — PTCGP → Pack details → Offering Rates.",
        "   Compare to `slot_rates` in `data/reference/pull_probability_model.json`.",
        "   If they match, set `confidence=verified`, re-run `build_pack_ev.py`, re-run this report.",
        "",
        "2. **OR accept inferred confidence** and use Scenario B or C above.",
        "",
        "3. **Resolve ambiguous entries** — fill `data/exports/current_pack_source_review.csv`",
        "   to expand EV-ready coverage from 157 to ~216/224 entries.",
        "",
        "4. **Identify Zygarde ex pack source** — enables Zygarde ex Fighting deck targeting.",
        "",
        "> Rankings are for **informational/planning purposes only** at inferred confidence.",
        "> Verify in-app before treating these as actionable spend decisions.",
        "",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def run_validate() -> bool:
    print("\n=== generate_pack_recommendation_report.py [VALIDATE] ===")
    errors = 0

    # Output files exist
    for fpath, label in [
        (OUT_JSON, "inferred_pack_recommendations.json"),
        (OUT_MD,   "inferred_pack_recommendations.md"),
        (OUT_CSV,  "inferred_pack_recommendations.csv"),
    ]:
        if fpath.exists():
            print(f"  PASS  {label} exists")
        else:
            print(f"  ERROR: {label} missing — run without --validate first")
            errors += 1

    if errors:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
        return False

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    # model_confidence must be a valid confidence level
    mc = out.get("model_confidence")
    valid_mc = (
        "inferred", "third_party_verified", "verified",
        "user_in_app_verified", "in_app_verified_partial",
        "third_party_verified_with_in_app_anchor", "pending_verification",
        "bulbapedia_branch_verified", "bulbapedia_verified",
        "user_in_app_verified_plus_bulbapedia",
    )
    if mc not in valid_mc:
        print(f"  ERROR: model_confidence='{mc}' not in {valid_mc}")
        errors += 1
    else:
        print(f"  PASS  model_confidence={mc}")

    # disclaimer must be present
    disclaimer = out.get("disclaimer", "")
    if "INFERRED" not in disclaimer.upper() and "inferred" not in disclaimer.lower():
        print("  ERROR: disclaimer missing or does not mention inferred confidence")
        errors += 1
    else:
        print("  PASS  disclaimer present")

    # No unqualified claim that rates currently are verified
    md_text = OUT_MD.read_text(encoding="utf-8").lower()
    # Only flag phrases that assert current/past verified state — not instructional future tense
    bad_phrases = [
        "rates have been verified",
        "rates are now verified",
        "slot rates are confirmed",
        "verified slot rates",
    ]
    false_verified = [p for p in bad_phrases if p in md_text]
    if false_verified:
        print(f"  ERROR: markdown contains verified-rate claims: {false_verified}")
        errors += 1
    else:
        print("  PASS  no false verified-rate claims in markdown")

    # top_5_by_adjusted_ev non-empty
    top5 = out.get("top_5_by_adjusted_ev", [])
    if len(top5) < 1:
        print("  ERROR: top_5_by_adjusted_ev is empty")
        errors += 1
    else:
        print(f"  PASS  top_5_by_adjusted_ev has {len(top5)} entries")

    # All referenced packs exist in pack_ev.json
    if PACK_EV_JSON.exists():
        ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
        ev_pack_names = {p["pack_name"] for p in ev.get("packs", [])}
        rec_packs = {p["pack_name"] for p in out.get("top_5_by_adjusted_ev", [])}
        missing_packs = rec_packs - ev_pack_names
        if missing_packs:
            print(f"  ERROR: recommendation references packs not in pack_ev.json: {missing_packs}")
            errors += 1
        else:
            print("  PASS  all recommended packs exist in pack_ev.json")

    # collection.json unchanged — use regex since file has JS-style comments
    if COLLECTION_SOURCE.exists():
        import re as _re
        raw = COLLECTION_SOURCE.read_text(encoding="utf-8")
        m = _re.search(r'"total_cards"\s*:\s*(\d+)', raw)
        total = int(m.group(1)) if m else 0
        if total != 380:
            print(f"  ERROR: collection.json total_cards={total}, expected 380")
            errors += 1
        else:
            print("  PASS  collection.json total_cards=380 (unchanged)")

    # collection_mutated must be False
    if out.get("collection_mutated"):
        print("  ERROR: collection_mutated=True")
        errors += 1
    else:
        print("  PASS  collection_mutated=False")

    # cards.json unchanged (329)
    if CARDS_SOURCE.exists():
        cards_raw = json.loads(CARDS_SOURCE.read_text(encoding="utf-8"))
        cards_total = sum(c.get("quantity", 0) for c in cards_raw if isinstance(c, dict))
        if cards_total != 329:
            print(f"  ERROR: cards.json total={cards_total}, expected 329")
            errors += 1
        else:
            print("  PASS  cards.json total=329 (unchanged)")

    if errors == 0:
        print(f"\nVALIDATION PASSED  (model_confidence={mc}, top_rec={top5[0]['pack_name']})")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate or validate inferred pack recommendation report"
    )
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        sys.exit(0 if run_validate() else 1)

    print("\n=== generate_pack_recommendation_report.py ===")

    for p in (PACK_EV_JSON, COLLECTION_JSON):
        if not p.exists():
            print(f"ERROR: required input not found: {p}", file=sys.stderr)
            sys.exit(1)

    ev_data       = load_ev(PACK_EV_JSON)
    ev_readiness  = load_ev_readiness(EV_READINESS_JSON) if EV_READINESS_JSON.exists() else {}
    conf_meta     = load_confidence_meta(CONFIDENCE_JSON) if CONFIDENCE_JSON.exists() else {}
    deck_val      = load_deck_validation(DECK_VALIDATION_JSON)

    packs = ev_data["packs"]
    print(f"  EV packs loaded:      {len(packs)}")
    print(f"  Deck validations:     {len(deck_val)}")
    print(f"  Collection total:     {ev_data['meta']['collection_total']}")
    print(f"  Model confidence:     {ev_data['meta']['model_confidence']}")

    deck_targets = deck_target_pack_map(packs)
    buckets = build_buckets(packs, deck_targets, deck_val)

    out_data = write_json(ev_data, buckets, conf_meta, ev_readiness)
    write_csv(ev_data, buckets)
    write_md(out_data, ev_data, buckets, deck_val)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_CSV.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    print("\n=== Summary ===")
    top5 = out_data["top_5_by_adjusted_ev"]
    print("  Top packs by adjusted EV:")
    for i, p in enumerate(top5, 1):
        print(f"    {i}. {p['pack_name']:30s} adj={p['confidence_adjusted_ev']:.4f}  total={p['pack_total_ev']:.4f}")
    mc = out_data.get("model_confidence", "inferred")
    print(f"\n  Top recommendation: {top5[0]['pack_name']} (adj EV={top5[0]['confidence_adjusted_ev']:.4f})")
    print(f"  Model confidence: {mc} (×0.85 adjustment applied)")
    if mc == "third_party_verified":
        print("\n  ⚠ Rates are THIRD_PARTY_VERIFIED (Game8, ONE Esports, CGMagazine, ShackNews).")
        print("  NOT official in-app verified. Verify in PTCGP app for official confirmation.")
    else:
        print("\n  ⚠ Slot rates are INFERRED. Verify in-app before acting on these rankings.")
    print("\nDone.")


if __name__ == "__main__":
    main()
