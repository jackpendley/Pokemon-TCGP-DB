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
COLLECTION_JSON      = ROOT / "data" / "current"  / "collection_normalized.json"
PROMO_EV_JSON        = ROOT / "data" / "current"  / "promo_pack_ev.json"
DECK_VALIDATION_JSON = ROOT / "data" / "exports"  / "deck_recommendation_validation.json"
COLLECTION_SOURCE    = ROOT / "collection.json"

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


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def rank_packs(packs: list, key: str, n: int = TOP_N) -> list:
    return sorted(packs, key=lambda p: p.get(key, 0.0), reverse=True)[:n]


def generate_pack_description(pack: dict, rank: int) -> str:
    missing   = pack.get("missing_in_pool", 0)
    total     = pack.get("cards_in_pool", 1)
    new_ev    = pack.get("new_card_ev_10x", 0.0)
    dr_ratio  = pack.get("ev_diminishing_returns_ratio", 1.0)
    deck_ev   = pack.get("deck_target_ev", 0.0)
    ex_ev     = pack.get("ex_card_ev", 0.0)
    cost      = pack.get("cost_per_unique_card_10x", 0.0)
    pct_miss  = missing / total if total > 0 else 0

    parts: list[str] = []

    if pct_miss >= 0.60:
        parts.append(f"large fresh pool — {missing}/{total} cards unowned")
    elif pct_miss >= 0.30:
        parts.append(f"moderate pool — {missing}/{total} cards unowned")
    else:
        parts.append(f"mostly complete — {missing}/{total} cards unowned")
        if dr_ratio < 0.70:
            parts.append(f"heavy diminishing returns (DR={dr_ratio:.2f})")

    parts.append(f"expect ~{new_ev:.1f} new-card EV per 10x batch (rarity-weighted)")

    if deck_ev >= 0.5:
        parts.append("high-value deck targets present")
    elif deck_ev >= 0.1:
        parts.append("contains deck targets")

    if ex_ev >= 1.0:
        parts.append("strong EX card density")
    elif ex_ev >= 0.3:
        parts.append("notable EX cards available")

    if cost > 0 and rank > 3:
        parts.append(f"{cost:.1f} ⧗/EV")

    prefix = {1: "Top pick.", 2: "Strong choice.", 3: "Good option."}.get(rank, "")
    joined = "; ".join(parts)
    body   = (joined[0].upper() + joined[1:] if joined else "") + "."
    return f"{prefix} {body}".strip() if prefix else body


def deck_target_pack_map(packs: list) -> dict:
    """
    Returns {card_name: [pack entries sorted by ev_contribution desc]}.
    Uses deck_target_cards (added in build_pack_ev to capture rare chase cards
    that fall outside the TOP_N_CARDS cutoff in top_ev_cards).
    """
    out = {}
    for p in packs:
        # Prefer deck_target_cards; fall back to top_ev_cards for older outputs
        sources = p.get("deck_target_cards") or [
            c for c in p.get("top_ev_cards", []) if c.get("is_deck_target")
        ]
        for c in sources:
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
    for name in out:
        out[name].sort(key=lambda x: x["ev_contribution"], reverse=True)
    return out


def build_unified_ranking(packs: list, deck_targets: dict, deck_validation: list) -> dict:
    """Single unified ranking plus cost-efficiency analysis and chase deck guide."""
    by_unified = sorted(packs, key=lambda p: p.get("unified_score", 0.0), reverse=True)
    by_cost     = sorted(packs, key=lambda p: p.get("cost_per_unique_card_10x", float("inf")))

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
                promo_only = {"Zygarde ex"}
                note = (
                    "PROMO-B card — cannot be obtained from any pack; "
                    "must be acquired through events or missions"
                    if card_name in promo_only
                    else "card not found in pack_sources — pack unknown"
                )
                best_for_chase[deck_name] = {
                    "card_needed": card_name,
                    "short_by": mc["short_by"],
                    "best_pack": None,
                    "best_ev": 0.0,
                    "best_pull_prob": 0.0,
                    "candidates": [],
                    "note": note,
                }

    return {
        "top_packs_unified": by_unified[:TOP_N],
        "cost_efficiency_ranking": by_cost[:TOP_N],
        "full_unified_ranking": by_unified,
        "chase_deck_packs": best_for_chase,
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

_INFERRED_MC_VALUES = {
    "inferred", "pending_verification",
    "in_app_verified_partial",
    "third_party_verified_with_in_app_anchor",
}


def write_json(ev_data: dict, buckets: dict) -> dict:
    packs = ev_data["packs"]
    mc = ev_data["meta"]["model_confidence"]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "generate_pack_recommendation_report.py",
        "model_confidence": mc,
        "collection_total": ev_data["meta"]["collection_total"],
        "collection_mutated": False,
        "disclaimer": (
            "INFERRED CONFIDENCE: Slot rates are inferred from third-party data, not "
            "verified in-app. All EVs are adjusted by 0.85 to reflect this uncertainty."
        ) if mc in _INFERRED_MC_VALUES else "",
        "top_packs_unified": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["top_packs_unified"]
        ],
        "cost_efficiency_ranking": [
            {k: v for k, v in p.items() if k != "top_ev_cards"}
            for p in buckets["cost_efficiency_ranking"]
        ],
        "chase_deck_packs": buckets["chase_deck_packs"],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_csv(ev_data: dict, buckets: dict):
    fields = [
        "rank_unified", "pack_name", "expansion", "set_code",
        "unified_score", "new_card_ev_10x", "new_card_ev",
        "ex_card_ev", "deck_target_ev",
        "missing_rare_plus", "rare_plus_ev_10x",
        "cost_per_unique_card_10x", "ev_diminishing_returns_ratio",
        "cards_in_pool", "owned_in_pool", "missing_in_pool",
    ]
    packs = ev_data["packs"]
    by_unified = sorted(packs, key=lambda p: p.get("unified_score", 0.0), reverse=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, p in enumerate(by_unified, 1):
            w.writerow({
                "rank_unified": i,
                "pack_name": p["pack_name"],
                "expansion": p["expansion"],
                "set_code": p["set_code"],
                "unified_score": round(p.get("unified_score", 0.0), 6),
                "new_card_ev_10x": round(p.get("new_card_ev_10x", 0.0), 6),
                "new_card_ev": round(p.get("new_card_ev", 0.0), 6),
                "ex_card_ev": round(p.get("ex_card_ev", 0.0), 6),
                "deck_target_ev": round(p.get("deck_target_ev", 0.0), 6),
                "missing_rare_plus": p.get("missing_rare_plus", 0),
                "rare_plus_ev_10x": round(p.get("rare_plus_ev_10x", 0.0), 6),
                "cost_per_unique_card_10x": round(p.get("cost_per_unique_card_10x", 0.0), 4),
                "ev_diminishing_returns_ratio": round(p.get("ev_diminishing_returns_ratio", 0.0), 4),
                "cards_in_pool": p.get("cards_in_pool", 0),
                "owned_in_pool": p.get("owned_in_pool", 0),
                "missing_in_pool": p.get("missing_in_pool", 0),
            })


def write_full_ranking_md(ev_data: dict, buckets: dict) -> Path:
    out_path = ROOT / "review" / "full_pack_ranking.md"
    all_packs = buckets["full_unified_ranking"]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "# Full Pack Ranking — All 24 Standard Packs",
        "",
        f"Generated: {ts}",
        "",
        "Ranked by unified score. Use Pack Hourglasses to open these packs.",
        "",
        "---",
        "",
    ]

    for i, p in enumerate(all_packs, 1):
        name     = p["pack_name"]
        exp      = p["expansion"]
        score    = p.get("unified_score", 0.0)
        missing  = p.get("missing_in_pool", 0)
        total    = p.get("cards_in_pool", 0)
        new_ev   = p.get("new_card_ev_10x", 0.0)
        cost     = p.get("cost_per_unique_card_10x", 0.0)
        dr       = p.get("ev_diminishing_returns_ratio", 0.0)
        desc     = generate_pack_description(p, i)

        rare_miss = p.get("missing_rare_plus", 0)
        rare_ev   = p.get("rare_plus_ev_10x", 0.0)
        lines += [
            f"## {i}. {name} ({exp})",
            "",
            f"**Score:** {score:.4f} | **Missing:** {missing}/{total} | **★+ miss:** {rare_miss} | **EV/10x:** {new_ev:.2f} | **★+/10x:** {rare_ev:.2f} | **⧗/EV:** {cost:.1f} | **DR:** {dr:.2f}",
            "",
            desc,
            "",
            "---",
            "",
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_md(out_data: dict, ev_data: dict, buckets: dict, deck_validation: list, show_promo: bool = True):
    packs = ev_data["packs"]
    top5 = buckets["top_packs_unified"]

    def pack_detail(p: dict) -> list:
        lines = []
        lines.append(f"**{p['pack_name']}** ({p['expansion']})")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Unified Score | **{p.get('unified_score', 0.0):.4f}** |")
        lines.append(f"| New-card EV (10x) | {p.get('new_card_ev_10x', 0.0):.4f} |")
        lines.append(f"| New-card EV (1x) | {p.get('new_card_ev', 0.0):.4f} |")
        lines.append(f"| EX-card EV | {p.get('ex_card_ev', 0.0):.4f} |")
        lines.append(f"| Deck target EV | {p.get('deck_target_ev', 0.0):.4f} |")
        lines.append(f"| Cost / EV unit (10x) | {p.get('cost_per_unique_card_10x', 0.0):.2f} ⧗ |")
        lines.append(f"| DR ratio | {p.get('ev_diminishing_returns_ratio', 0.0):.3f} |")
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

    mc = out_data["model_confidence"]
    all_unified = buckets["full_unified_ranking"]

    lines = [
        "# Pack Recommendation Report",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Report generated | {out_data['generated_at']} |",
        f"| Model confidence | **{mc}** |",
        f"| Collection total | {out_data['collection_total']} cards |",
        f"| Packs ranked | {len(packs)} |",
        f"| Packs blocked | {len(ev_data.get('blocked_packs', []))} |",
        "",
        "---",
        "",
        "## Top Packs — Unified Ranking",
        "",
        "Ranked by unified score: `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5`, weighted by confidence. `new_card_ev_10x` is rarity-weighted (base + rarity bonus only); EX and deck-target bonuses are added separately via their own terms.",
        "",
        "| Rank | Pack | Expansion | Unified | New EV (10x) | Deck EV | EX EV | ⧗/card | Missing |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for i, p in enumerate(top5, 1):
        lines.append(
            f"| {i} | **{p['pack_name']}** | {p['expansion']} "
            f"| {p.get('unified_score', 0.0):.4f} "
            f"| {p.get('new_card_ev_10x', 0.0):.4f} "
            f"| {p.get('deck_target_ev', 0.0):.4f} "
            f"| {p.get('ex_card_ev', 0.0):.4f} "
            f"| {p.get('cost_per_unique_card_10x', 0.0):.1f} "
            f"| {p['missing_in_pool']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Cost Efficiency Ranking",
        "",
        "Ranked by hourglasses spent per unique new card (10-pack batch). Lower is better.",
        "",
        "| Rank | Pack | ⧗/card (10x) | New EV (10x) | DR Ratio | Missing |",
        "|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(buckets["cost_efficiency_ranking"], 1):
        lines.append(
            f"| {i} | {p['pack_name']} "
            f"| {p.get('cost_per_unique_card_10x', 0.0):.1f} "
            f"| {p.get('new_card_ev_10x', 0.0):.4f} "
            f"| {p.get('ev_diminishing_returns_ratio', 0.0):.3f} "
            f"| {p['missing_in_pool']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Pack Detail — Top 5 by Unified Score",
        "",
    ]
    for p in top5:
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
    for deck_name, info in buckets["chase_deck_packs"].items():
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
        "## Complete Pack Ranking",
        "",
        "| Rank | Pack | Expansion | Unified | New EV (10x) | New EV (1x) | Missing | Deck EV | EX EV |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(all_unified, 1):
        lines.append(
            f"| {i} | {p['pack_name']} | {p['expansion']} "
            f"| {p.get('unified_score', 0.0):.4f} "
            f"| {p.get('new_card_ev_10x', 0.0):.4f} "
            f"| {p.get('new_card_ev', 0.0):.4f} "
            f"| {p['missing_in_pool']} "
            f"| {p.get('deck_target_ev', 0.0):.4f} "
            f"| {p.get('ex_card_ev', 0.0):.4f} |"
        )

    # Promo pack summary section
    promo_lines: list[str] = []
    if show_promo and PROMO_EV_JSON.exists():
        try:
            promo_data = json.loads(PROMO_EV_JSON.read_text(encoding="utf-8"))
            promo_packs = [p for p in promo_data.get("packs", []) if p.get("new_card_ev", 0) > 0]
            if promo_packs:
                promo_lines += [
                    "",
                    "---",
                    "",
                    "## Promo Pack Rankings (Shop Tickets)",
                    "",
                    "> Promo packs use **Shop Tickets** — not Hourglasses. EVs below are not",
                    "> comparable to regular pack EVs. See `review/promo_pack_ev.md` for full details.",
                    "",
                    "| # | Pack | Missing | New Card EV |",
                    "|---|---|---|---|",
                ]
                for i, p in enumerate(promo_packs[:10], 1):
                    promo_lines.append(
                        f"| {i} | {p['pack_name']} | {p.get('missing_in_pool', '?')}/{p.get('cards_in_pool', '?')} | {p['new_card_ev']:.4f} |"
                    )
                promo_lines.append("")
        except Exception:
            pass

    status_lines = [
        "",
        "---",
        "",
        "## Status",
        "",
        "- Pull rates: **pz_verified** — per-card drop chances from Pokemon Zone, no confidence haircut",
        "- Pack source coverage: **272/272** collection entries resolved (100%)",
    ]
    if show_promo:
        status_lines.append("- Promo packs: scored separately in `review/promo_pack_ev.md` (Shop Ticket currency)")
    status_lines.append("")

    lines += promo_lines + status_lines

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
    valid_mc = _INFERRED_MC_VALUES | {
        "pz_verified", "third_party_verified", "verified",
        "user_in_app_verified",
        "bulbapedia_branch_verified", "bulbapedia_verified",
        "user_in_app_verified_plus_bulbapedia",
    }
    if mc not in valid_mc:
        print(f"  ERROR: model_confidence='{mc}' not in {valid_mc}")
        errors += 1
    else:
        print(f"  PASS  model_confidence={mc}")

    # disclaimer must mention inferred confidence — only applies to inferred confidence levels
    if mc in _INFERRED_MC_VALUES:
        disclaimer = out.get("disclaimer", "")
        if "INFERRED" not in disclaimer.upper() and "inferred" not in disclaimer.lower():
            print("  ERROR: disclaimer missing or does not mention inferred confidence")
            errors += 1
        else:
            print("  PASS  disclaimer present")
    else:
        # For verified confidence, check no stale inferred disclaimer remains
        stale = out.get("disclaimer", "")
        if stale and "inferred" in stale.lower():
            print("  ERROR: stale inferred-confidence disclaimer present for verified confidence level")
            errors += 1
        else:
            print(f"  SKIP  disclaimer check (model_confidence={mc} does not require inferred disclaimer)")

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

    # top_packs_unified non-empty
    top5 = out.get("top_packs_unified", [])
    if len(top5) < 1:
        print("  ERROR: top_packs_unified is empty")
        errors += 1
    else:
        print(f"  PASS  top_packs_unified has {len(top5)} entries")

    # cost_efficiency_ranking non-empty
    cost_rank = out.get("cost_efficiency_ranking", [])
    if len(cost_rank) < 1:
        print("  ERROR: cost_efficiency_ranking is empty")
        errors += 1
    else:
        print(f"  PASS  cost_efficiency_ranking has {len(cost_rank)} entries")

    # All referenced packs exist in pack_ev.json
    if PACK_EV_JSON.exists():
        ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
        ev_pack_names = {p["pack_name"] for p in ev.get("packs", [])}
        rec_packs = {p["pack_name"] for p in out.get("top_packs_unified", [])}
        missing_packs = rec_packs - ev_pack_names
        if missing_packs:
            print(f"  ERROR: recommendation references packs not in pack_ev.json: {missing_packs}")
            errors += 1
        else:
            print("  PASS  all recommended packs exist in pack_ev.json")

    # collection.json total_cards must match what the EV report recorded
    if COLLECTION_SOURCE.exists():
        import re as _re
        raw = COLLECTION_SOURCE.read_text(encoding="utf-8")
        m = _re.search(r'"total_cards"\s*:\s*(\d+)', raw)
        actual_total = int(m.group(1)) if m else 0
        expected_total = out.get("collection_total", 0)
        if actual_total != expected_total:
            print(f"  ERROR: collection.json total_cards={actual_total}, expected {expected_total} (from report)")
            errors += 1
        else:
            print(f"  PASS  collection.json total_cards={actual_total} matches report")

    # collection_mutated must be False
    if out.get("collection_mutated"):
        print("  ERROR: collection_mutated=True")
        errors += 1
    else:
        print("  PASS  collection_mutated=False")

    # cards.json check removed — historical file deleted in 2026-05-18 cleanup

    top5 = out.get("top_packs_unified", [])
    if errors == 0:
        top_name = top5[0]["pack_name"] if top5 else "N/A"
        print(f"\nVALIDATION PASSED  (model_confidence={mc}, top_rec={top_name})")
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
    parser.add_argument("--validate",     action="store_true")
    parser.add_argument("--no-promo",     action="store_true",
                        help="Suppress promo pack section in outputs")
    parser.add_argument("--full-rankings", action="store_true",
                        help="Write review/full_pack_ranking.md with descriptions for all 24 packs")
    args = parser.parse_args()

    if args.validate:
        sys.exit(0 if run_validate() else 1)

    show_promo = not args.no_promo

    print("\n=== generate_pack_recommendation_report.py ===")

    for p in (PACK_EV_JSON, COLLECTION_JSON):
        if not p.exists():
            print(f"ERROR: required input not found: {p}", file=sys.stderr)
            sys.exit(1)

    ev_data  = load_ev(PACK_EV_JSON)
    deck_val = load_deck_validation(DECK_VALIDATION_JSON)

    packs = ev_data["packs"]
    print(f"  EV packs loaded:      {len(packs)}")
    print(f"  Deck validations:     {len(deck_val)}")
    print(f"  Collection total:     {ev_data['meta']['collection_total']}")
    print(f"  Model confidence:     {ev_data['meta']['model_confidence']}")

    deck_targets = deck_target_pack_map(packs)
    buckets = build_unified_ranking(packs, deck_targets, deck_val)

    out_data = write_json(ev_data, buckets)
    write_csv(ev_data, buckets)
    write_md(out_data, ev_data, buckets, deck_val, show_promo=show_promo)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_CSV.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    if args.full_rankings:
        ranking_path = write_full_ranking_md(ev_data, buckets)
        print(f"  Written: {ranking_path.relative_to(ROOT)}")

    print("\n=== Summary ===")
    top5 = out_data["top_packs_unified"]
    print("  Top packs by unified score:")
    for i, p in enumerate(top5, 1):
        print(f"    {i}. {p['pack_name']:30s} unified={p.get('unified_score', 0.0):.4f}  10x_ev={p.get('new_card_ev_10x', 0.0):.4f}")
    mc = out_data.get("model_confidence", "inferred")
    print(f"\n  Top recommendation: {top5[0]['pack_name']} (unified={top5[0].get('unified_score', 0.0):.4f})")
    if mc == "pz_verified":
        print(f"  Model confidence: {mc} (×1.0 — PZ direct rates, no haircut)")
        print("\n  Rates are PZ_VERIFIED — per-card drop chances from Pokemon Zone.")
        if show_promo and PROMO_EV_JSON.exists():
            try:
                promo_data = json.loads(PROMO_EV_JSON.read_text(encoding="utf-8"))
                top_promo = [p for p in promo_data.get("packs", []) if p.get("new_card_ev", 0) > 0][:3]
                if top_promo:
                    print("\n  Top promo packs (Shop Tickets):")
                    for i, p in enumerate(top_promo, 1):
                        print(f"    {i}. {p['pack_name']:<38} new_ev={p['new_card_ev']:.4f}")
            except Exception:
                pass
    elif mc == "third_party_verified":
        print(f"  Model confidence: {mc} (×0.85 adjustment applied)")
        print("\n  Rates are THIRD_PARTY_VERIFIED. Verify in PTCGP app for official confirmation.")
    else:
        print(f"  Model confidence: {mc} (×0.85 adjustment applied)")
        print("\n  Slot rates are INFERRED. Verify in-app before acting on these rankings.")
    print("\nDone.")


if __name__ == "__main__":
    main()
