#!/usr/bin/env python3
"""
Build the pull probability model scaffold for all PTCGP packs.

Card pool counts per rarity are derived from pack_sources.json.
Pull probability slot rates are sourced from trusted external references
(confidence=inferred) until overridden by verified in-app offering rates
(confidence=verified).

rarity_probabilities (aggregate per-pack rates) remain null until explicitly
populated from verified in-app Offering Rates or computed from slot_rates.

The in-app Offering Rates are the ONLY trusted source for verified pull
probabilities. To upgrade from inferred to verified: record the "Offering Rates"
values from each pack detail screen in the PTCGP app, update rarity_probabilities
and slot_rates, and set confidence='verified'.

Inputs:
    data/reference/pack_sources.json
    data/current/pack_source_confidence_scores.json

Outputs:
    data/reference/pull_probability_model.json
    review/pull_probability_model.md

Usage:
    python3 scripts/build_pull_probability_model.py
    python3 scripts/build_pull_probability_model.py --validate
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
CONFIDENCE_SCORES_JSON = ROOT / "data" / "current" / "pack_source_confidence_scores.json"
OUT_JSON = ROOT / "data" / "reference" / "pull_probability_model.json"
OUT_MD = ROOT / "review" / "pull_probability_model.md"

RARITY_FIELDS = [
    "one_diamond", "two_diamond", "three_diamond", "four_diamond",
    "one_star", "double_star", "triple_star", "crown", "promo", "unknown",
]

# Standard PTCGP pack: 5 cards per pack.
STANDARD_SLOT_MODEL = {
    "cards_per_pack": 5,
    "slot_count": 5,
    "notes": (
        "Standard PTCGP pack: 5 cards. "
        "Slot-level probability breakdown stored in slot_rates. "
        "Aggregate rarity_probabilities null until computed from verified slot_rates."
    ),
}

# ---------------------------------------------------------------------------
# Inferred slot rates
# Source: Game8 PTCGP offering rates guide (https://game8.co/games/Pokemon-TCG-Pocket/archives/482685),
# corroborated by ShackNews and cgmagonline.com. Multiple independent trusted sources
# report these same specific values, consistent with in-game Offering Rates disclosure.
# Rates apply to packs without shiny rarities. pack_sources.json has no shiny cards
# for any of the 24 modeled packs. Confidence: inferred — verify in-app to upgrade.
# Slot 4 total: 0.90+0.05+0.01666+0.02572+0.005+0.00222+0.0004 = 1.00000
# Slot 5 total: 0.60+0.20+0.06664+0.10288+0.02+0.00888+0.0016 = 1.00000
# ---------------------------------------------------------------------------
INFERRED_SLOT_RATES = {
    "regular_pack_probability": 0.9995,
    "rare_pack_probability": 0.0005,
    "slots_1_3": {
        "one_diamond": 1.0
    },
    "slot_4": {
        "two_diamond":   0.90000,
        "three_diamond": 0.05000,
        "four_diamond":  0.01666,
        "one_star":      0.02572,
        "double_star":   0.00500,
        "triple_star":   0.00222,
        "crown":         0.00040,
    },
    "slot_5": {
        "two_diamond":   0.60000,
        "three_diamond": 0.20000,
        "four_diamond":  0.06664,
        "one_star":      0.10288,
        "double_star":   0.02000,
        "triple_star":   0.00888,
        "crown":         0.00160,
    },
    "rare_pack_all_5_slots": {
        "one_star":    0.40,
        "double_star": 0.50,
        "triple_star": 0.05,
        "crown":       0.05,
    },
    "confidence": "inferred",
    "source_name": "game8_co_ptcgp_offering_rates",
    "source_url": "https://game8.co/games/Pokemon-TCG-Pocket/archives/482685",
    "source_accessed_at": "2026-05-12",
    "source_notes": (
        "Per-slot rates sourced from Game8 (trusted third-party PTCGP guide), "
        "corroborated by ShackNews (shacknews.com) and cgmagonline.com. "
        "Multiple independent trusted sources reproduce these specific decimal values "
        "consistently, which are consistent with the in-game Offering Rates disclosure. "
        "The game legally discloses rates in-app; these numbers match that level of specificity. "
        "Rates confirmed universal across expansions: cgmagonline article explicitly states "
        "rates stayed the same between Space-Time Smackdown and Triumphant Light. "
        "These rates apply to packs WITHOUT shiny rarities. "
        "Shiny rarities (introduced with Shining Revelry/A2b) are not present in "
        "pack_sources.json for any pack, so these rates are applied to all 24 modeled packs. "
        "IMPORTANT: Confidence is 'inferred', not 'verified'. To upgrade to verified: "
        "open each pack in the PTCGP app -> Pack details -> Offering Rates and confirm."
    ),
}


def rarity_counts(cards: list) -> dict:
    raw = Counter(c.get("rarity") for c in cards)
    out = {}
    for r in RARITY_FIELDS:
        v = raw.get(r, 0)
        if v > 0:
            out[r] = v
    unknowns = sum(v for k, v in raw.items() if k not in RARITY_FIELDS)
    if unknowns > 0:
        out["unknown"] = out.get("unknown", 0) + unknowns
    return out


def add_rarity_dicts(a: dict, b: dict) -> dict:
    keys = set(a) | set(b)
    return {k: a.get(k, 0) + b.get(k, 0) for k in keys}


def load_existing_rates(path: Path) -> dict:
    """Load per-pack rate data from existing model JSON. Returns {pack_name: data}."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = {}
        for p in raw.get("packs", []):
            pn = p.get("pack_name")
            if pn:
                result[pn] = {
                    "confidence": p.get("confidence", "unknown"),
                    "source_url": p.get("source_url"),
                    "source_name": p.get("source_name"),
                    "source_accessed_at": p.get("source_accessed_at"),
                    "slot_rates": p.get("slot_rates"),
                    "rarity_probabilities": p.get("rarity_probabilities"),
                    "notes": p.get("notes"),
                }
        return result
    except Exception:
        return {}


def build_pack_records(records: list, existing_rates: dict) -> list:
    """
    Return list of pack records — one per distinct pullable named pack.
    Shared-pool cards are folded into each named pack's combined_pool.
    Existing slot_rates and rarity_probabilities are preserved when present.
    """
    by_exp_pack = defaultdict(list)
    for r in records:
        exp = r.get("expansion", "")
        pn = r.get("pack_name")
        by_exp_pack[(exp, pn)].append(r)

    expansions = defaultdict(lambda: {"named": {}, "shared": []})
    for (exp, pn), cards in by_exp_pack.items():
        if pn is None:
            expansions[exp]["shared"] = cards
        else:
            expansions[exp]["named"][pn] = cards

    pack_records = []
    for exp in sorted(expansions):
        d = expansions[exp]
        shared = d["shared"]
        shared_by_rarity = rarity_counts(shared)
        shared_total = len(shared)

        all_exp_cards = shared + [c for cc in d["named"].values() for c in cc]
        set_code = all_exp_cards[0].get("set_code", "") if all_exp_cards else ""

        named_packs = d["named"]
        if not named_packs:
            continue

        for pn in sorted(named_packs):
            pack_cards = named_packs[pn]
            pack_by_rarity = rarity_counts(pack_cards)
            pack_total = len(pack_cards)
            combined_by_rarity = add_rarity_dicts(pack_by_rarity, shared_by_rarity)
            combined_total = pack_total + shared_total

            # Preserve existing rates; fall back to inferred rates for new packs
            existing = existing_rates.get(pn, {})
            prev_conf = existing.get("confidence", "unknown")

            # Preserve existing slot_rates if they exist; otherwise apply inferred
            existing_slot_rates = existing.get("slot_rates")
            slot_rates = existing_slot_rates if existing_slot_rates else INFERRED_SLOT_RATES.copy()

            # Confidence: preserve verified > inferred; apply inferred if unknown
            if prev_conf == "verified":
                confidence = "verified"
                source_url = existing.get("source_url")
                source_name = existing.get("source_name")
                source_accessed_at = existing.get("source_accessed_at")
                notes = existing.get("notes")
            else:
                confidence = "inferred"
                source_url = (existing.get("source_url")
                              or INFERRED_SLOT_RATES["source_url"])
                source_name = (existing.get("source_name")
                               or INFERRED_SLOT_RATES["source_name"])
                source_accessed_at = (existing.get("source_accessed_at")
                                      or INFERRED_SLOT_RATES["source_accessed_at"])
                notes = (
                    "Slot-level pull rates sourced from trusted third-party references "
                    "(confidence=inferred). rarity_probabilities are null — aggregate "
                    "per-pack rates must come from verified in-app Offering Rates. "
                    "To verify: open this pack in PTCGP app -> Pack details -> Offering Rates."
                )

            # Preserve rarity_probabilities if explicitly set (not all-null)
            prev_rarity_probs = existing.get("rarity_probabilities")
            if prev_rarity_probs and any(v is not None for v in prev_rarity_probs.values()):
                rarity_probs = prev_rarity_probs
            else:
                rarity_probs = {f: None for f in RARITY_FIELDS}

            pack_records.append({
                "pack_name": pn,
                "expansion": exp,
                "set_code": set_code,
                "is_shared_pool": False,
                "source_url": source_url,
                "source_name": source_name,
                "source_accessed_at": source_accessed_at,
                "confidence": confidence,
                "slot_model": STANDARD_SLOT_MODEL,
                "slot_rates": slot_rates,
                "card_pool": {
                    "pack_specific_total": pack_total,
                    "shared_pool_total": shared_total,
                    "combined_total": combined_total,
                    "pack_specific_by_rarity": pack_by_rarity,
                    "shared_pool_by_rarity": shared_by_rarity,
                    "combined_by_rarity": combined_by_rarity,
                },
                "rarity_probabilities": rarity_probs,
                "notes": notes,
            })

    return pack_records


def determine_source_status(pack_records: list) -> str:
    """Compute meta.source_status from pack confidence levels."""
    confs = {p.get("confidence") for p in pack_records}
    if "verified" in confs and "inferred" not in confs and "unknown" not in confs:
        return "verified"
    if "inferred" in confs:
        return "inferred"
    return "scaffold_only"


def write_json(pack_records: list) -> dict:
    source_status = determine_source_status(pack_records)
    n_verified = sum(1 for p in pack_records if p.get("confidence") == "verified")
    n_inferred = sum(1 for p in pack_records if p.get("confidence") == "inferred")
    n_unknown = sum(1 for p in pack_records if p.get("confidence") == "unknown")

    if source_status == "verified":
        meta_notes = (
            "All pack slot rates are verified from official in-app Offering Rates."
        )
    elif source_status == "inferred":
        meta_notes = (
            "Slot rates (slot_rates) are populated with confidence=inferred from trusted "
            "third-party sources (Game8, ShackNews, cgmagonline) that reproduce the in-game "
            "Offering Rates. rarity_probabilities (aggregate per-pack rates) remain null — "
            "these require in-app verification. "
            f"Inferred: {n_inferred}, Verified: {n_verified}, Unknown: {n_unknown}."
        )
    else:
        meta_notes = (
            "This is a scaffold model. Card pool counts per rarity are derived from "
            "pack_sources.json (Limitless TCG Pocket). "
            "Pull probability rates (rarity_probabilities) are ALL null — "
            "they must be populated from the official in-app Offering Rates screen "
            "or the official Pokémon TCG Pocket probability disclosure page. "
            "Do not invent or estimate pull rates. "
            "Required source: open each pack in the PTCGP app > Pack details > Offering Rates."
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_pull_probability_model.py",
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_version": "0.2.0",
            "source_status": source_status,
            "verified_source": (
                "ptcgp_in_app_offering_rates" if source_status == "verified" else None
            ),
            "inferred_source": (
                "game8_co_ptcgp_offering_rates" if source_status == "inferred" else None
            ),
            "notes": meta_notes,
        },
        "probability_source_required": {
            "status": "INFERRED" if source_status == "inferred" else
                      "VERIFIED" if source_status == "verified" else "MISSING",
            "description": (
                "Slot-level rates (slot_rates) are inferred from trusted third-party "
                "sources. Aggregate rarity_probabilities are still null and require "
                "in-app verification."
                if source_status == "inferred" else
                "Verified in-app offering rates have not been recorded. "
                "All rarity_probabilities are null."
            ),
            "how_to_verify": (
                "In the Pokémon TCG Pocket app: tap a pack > view 'Offering Rates' / "
                "'Card Rates' section. Compare to slot_rates in this file. "
                "If they match, set confidence='verified' and populate rarity_probabilities. "
                "If they differ, update slot_rates and set confidence='verified'."
            ),
            "inferred_slot_rates_source": (
                "https://game8.co/games/Pokemon-TCG-Pocket/archives/482685 "
                "(corroborated by ShackNews, cgmagonline)"
            ),
        },
        "packs": pack_records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_md(out: dict, pack_records: list):
    source_status = out["meta"]["source_status"]
    n_packs = len(pack_records)
    n_inferred = sum(1 for p in pack_records if p.get("confidence") == "inferred")
    n_verified = sum(1 for p in pack_records if p.get("confidence") == "verified")

    lines = [
        "# Pull Probability Model",
        "",
    ]

    if source_status == "inferred":
        lines += [
            "> **Slot rates populated with confidence=inferred from trusted external sources.**",
            "> `rarity_probabilities` (aggregate per-pack rates) are still null.",
            "> Verify slot_rates against in-app Offering Rates to upgrade to confidence=verified.",
            "",
        ]
    else:
        lines += [
            "> **Scaffold only — pull rates are NOT populated.**",
            "> All `rarity_probabilities` values are `null`.",
            "> Card pool counts (how many cards of each rarity exist per pack) are from `pack_sources.json`.",
            "> Pull rates must come from the official in-app Offering Rates screen.",
            "",
        ]

    lines += [
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Model version | {out['meta']['model_version']} |",
        f"| Source status | **{source_status}** |",
        f"| Inferred source | {out['meta'].get('inferred_source') or 'None'} |",
        f"| Verified source | {out['meta'].get('verified_source') or 'None'} |",
        f"| Total packs modeled | {n_packs} |",
        f"| Packs with inferred slot rates | {n_inferred} |",
        f"| Packs with verified rates | {n_verified} |",
        f"| rarity_probabilities values | **all null** (aggregate rates not yet verified) |",
        "",
    ]

    if source_status == "inferred":
        sr = INFERRED_SLOT_RATES
        lines += [
            "## Inferred Slot Rates (Applied to All 24 Packs)",
            "",
            f"Source: [{sr['source_name']}]({sr['source_url']}) — accessed {sr['source_accessed_at']}",
            "",
            "Corroborated by ShackNews and cgmagonline. Rates confirmed universal across expansions.",
            "Applies to packs without shiny rarities (all 24 packs in pack_sources.json).",
            "",
            "### Regular Pack (99.95% of all packs)",
            "",
            "| Slot | Rarity | Rate |",
            "|---|---|---|",
            "| 1–3 | one_diamond (◆) | 100% each |",
            f"| 4 | two_diamond (◆◆) | {sr['slot_4']['two_diamond']*100:.3f}% |",
            f"| 4 | three_diamond (◆◆◆) | {sr['slot_4']['three_diamond']*100:.3f}% |",
            f"| 4 | four_diamond (◆◆◆◆) | {sr['slot_4']['four_diamond']*100:.3f}% |",
            f"| 4 | one_star (☆) | {sr['slot_4']['one_star']*100:.3f}% |",
            f"| 4 | double_star (☆☆) | {sr['slot_4']['double_star']*100:.3f}% |",
            f"| 4 | triple_star (☆☆☆) | {sr['slot_4']['triple_star']*100:.3f}% |",
            f"| 4 | crown (♕) | {sr['slot_4']['crown']*100:.3f}% |",
            f"| 5 | two_diamond (◆◆) | {sr['slot_5']['two_diamond']*100:.3f}% |",
            f"| 5 | three_diamond (◆◆◆) | {sr['slot_5']['three_diamond']*100:.3f}% |",
            f"| 5 | four_diamond (◆◆◆◆) | {sr['slot_5']['four_diamond']*100:.3f}% |",
            f"| 5 | one_star (☆) | {sr['slot_5']['one_star']*100:.3f}% |",
            f"| 5 | double_star (☆☆) | {sr['slot_5']['double_star']*100:.3f}% |",
            f"| 5 | triple_star (☆☆☆) | {sr['slot_5']['triple_star']*100:.3f}% |",
            f"| 5 | crown (♕) | {sr['slot_5']['crown']*100:.3f}% |",
            "",
            "### Rare/God Pack (0.05% of all packs)",
            "",
            "All 5 slots draw from the same distribution:",
            "",
            "| Rarity | Rate per slot |",
            "|---|---|",
            f"| one_star (☆) | {sr['rare_pack_all_5_slots']['one_star']*100:.0f}% |",
            f"| double_star (☆☆) | {sr['rare_pack_all_5_slots']['double_star']*100:.0f}% |",
            f"| triple_star (☆☆☆) | {sr['rare_pack_all_5_slots']['triple_star']*100:.0f}% |",
            f"| crown (♕) | {sr['rare_pack_all_5_slots']['crown']*100:.0f}% |",
            "",
        ]

    lines += [
        "## How to Upgrade to Verified",
        "",
        "1. Open the Pokémon TCG Pocket app.",
        "2. Navigate to the pack you want to verify.",
        "3. View the **Offering Rates** / **Card Rates** section (disclosed in-app).",
        "4. Compare the in-app rates to `slot_rates` in `data/reference/pull_probability_model.json`.",
        "5. If they match, set `confidence: 'verified'` and populate `rarity_probabilities`.",
        "6. If they differ, update `slot_rates` with the correct values and set `confidence: 'verified'`.",
        "7. Re-run `python3 scripts/validate_pull_probability_model.py`.",
        "",
        "## Pack Pool Summary",
        "",
        "| Pack | Expansion | Set | Pool Total | 1◆ | 2◆ | 3◆ | 4◆ | ☆ | ☆☆ | ☆☆☆ |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for p in pack_records:
        cp = p["card_pool"]["combined_by_rarity"]
        lines.append(
            f"| {p['pack_name']} | {p['expansion']} | {p['set_code']} "
            f"| {p['card_pool']['combined_total']} "
            f"| {cp.get('one_diamond', 0)} "
            f"| {cp.get('two_diamond', 0)} "
            f"| {cp.get('three_diamond', 0)} "
            f"| {cp.get('four_diamond', 0)} "
            f"| {cp.get('one_star', 0)} "
            f"| {cp.get('double_star', 0)} "
            f"| {cp.get('triple_star', 0)} |"
        )

    lines += [
        "",
        "## rarity_probabilities Status",
        "",
        "All aggregate `rarity_probabilities` values are currently `null`.",
        "These represent P(at least one card of this rarity in a 5-card pack).",
        "They will be computed once slot_rates are verified from in-app Offering Rates.",
        "",
        "## Rarity Field Mapping",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| `one_diamond` | Common (◆) |",
        "| `two_diamond` | Uncommon (◆◆) |",
        "| `three_diamond` | Rare (◆◆◆) |",
        "| `four_diamond` | EX / Ultra Rare (◆◆◆◆) |",
        "| `one_star` | Full Art / Illustration Rare (☆) |",
        "| `double_star` | Special Art (☆☆) |",
        "| `triple_star` | Immersive / Rainbow (☆☆☆) |",
        "| `crown` | Crown / Gold |",
        "| `promo` | Promo card |",
        "",
    ]

    (ROOT / "review").mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _check_slot_sum(slot_dict: dict, label: str, errors_list: list):
    """Validate that slot probabilities sum to ~1.0."""
    if not slot_dict:
        return
    total = sum(v for v in slot_dict.values() if isinstance(v, (int, float)))
    if abs(total - 1.0) > 0.001:
        errors_list.append(f"{label} rates sum to {total:.5f} (expected 1.0 ± 0.001)")


def run_validate() -> bool:
    print("\n=== build_pull_probability_model.py [VALIDATE] ===")
    errors = 0

    if not OUT_JSON.exists():
        print("  ERROR: output JSON not found — run without --validate first")
        return False

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    for field in ("meta", "packs"):
        if field not in out:
            print(f"  ERROR: missing top-level field '{field}'")
            errors += 1
    if errors:
        return False
    print("  PASS  meta and packs fields present")

    packs = out["packs"]

    bad_identity = [p for p in packs
                    if not p.get("pack_name") and not p.get("is_shared_pool")]
    if bad_identity:
        print(f"  ERROR: {len(bad_identity)} packs missing pack_name/is_shared_pool")
        errors += 1
    else:
        print("  PASS  all packs have pack_name or is_shared_pool")

    bad_exp = [p for p in packs if not p.get("expansion")]
    if bad_exp:
        print(f"  ERROR: {len(bad_exp)} packs missing expansion")
        errors += 1
    else:
        print("  PASS  all packs have expansion")

    bad_sc = [p for p in packs if not p.get("set_code")]
    if bad_sc:
        print(f"  ERROR: {len(bad_sc)} packs missing set_code")
        errors += 1
    else:
        print("  PASS  all packs have set_code")

    # rarity_probabilities in [0, 1]
    prob_errors = 0
    for p in packs:
        rp = p.get("rarity_probabilities", {})
        for field, val in rp.items():
            if val is not None and not (isinstance(val, (int, float)) and 0 <= val <= 1):
                print(f"  ERROR: {p['pack_name']}.{field} = {val} (must be null or 0–1)")
                prob_errors += 1
    if prob_errors:
        errors += prob_errors
    else:
        print("  PASS  all rarity_probabilities values are null or in [0, 1]")

    valid_conf = {"verified", "inferred", "unknown"}
    bad_conf = [p for p in packs if p.get("confidence") not in valid_conf]
    if bad_conf:
        print(f"  ERROR: {len(bad_conf)} packs have invalid confidence value")
        errors += 1
    else:
        print("  PASS  all confidence values valid")

    bad_verified = [p for p in packs
                    if p.get("confidence") == "verified"
                    and not p.get("source_url") and not p.get("source_name")]
    if bad_verified:
        print(f"  ERROR: {len(bad_verified)} verified packs missing source attribution")
        errors += 1
    else:
        print("  PASS  verified packs have source attribution (or none are verified yet)")

    bad_inferred = [p for p in packs
                    if p.get("confidence") == "inferred"
                    and not (p.get("source_url") or p.get("source_name")
                             or (p.get("slot_rates") or {}).get("source_url"))]
    if bad_inferred:
        print(f"  ERROR: {len(bad_inferred)} inferred packs missing source attribution")
        errors += 1
    else:
        print("  PASS  inferred packs have source attribution")

    bad_pools = [
        p for p in packs
        if p.get("card_pool", {}).get("combined_total", -1) < 0
    ]
    if bad_pools:
        print(f"  ERROR: {len(bad_pools)} packs have negative combined_total")
        errors += 1
    else:
        print("  PASS  all card pool totals non-negative")

    # Validate slot_rates sums if present
    slot_sum_errors = []
    for p in packs:
        sr = p.get("slot_rates")
        if not sr:
            continue
        _check_slot_sum(sr.get("slot_4"), f"{p['pack_name']}.slot_4", slot_sum_errors)
        _check_slot_sum(sr.get("slot_5"), f"{p['pack_name']}.slot_5", slot_sum_errors)
        _check_slot_sum(sr.get("rare_pack_all_5_slots"),
                        f"{p['pack_name']}.rare_pack_all_5_slots", slot_sum_errors)
    if slot_sum_errors:
        for e in slot_sum_errors:
            print(f"  ERROR: slot sum: {e}")
        errors += len(slot_sum_errors)
    else:
        n_with_slots = sum(1 for p in packs if p.get("slot_rates"))
        if n_with_slots:
            print(f"  PASS  slot rate sums valid ({n_with_slots} packs with slot_rates)")

    # Report status
    unknown_rarity_probs = sum(
        1 for p in packs
        if all(v is None for v in p.get("rarity_probabilities", {}).values())
    )
    n_inferred = sum(1 for p in packs if p.get("confidence") == "inferred")
    n_verified = sum(1 for p in packs if p.get("confidence") == "verified")
    source_status = out["meta"]["source_status"]

    print(f"  INFO  {n_inferred}/{len(packs)} packs have inferred slot rates")
    print(f"  INFO  {n_verified}/{len(packs)} packs have verified rates")
    print(f"  INFO  {unknown_rarity_probs}/{len(packs)} packs have all-null rarity_probabilities")

    if errors == 0:
        print(f"\nVALIDATION PASSED  ({len(packs)} packs, source_status={source_status})")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build or validate the pull probability model"
    )
    parser.add_argument("--validate", action="store_true",
                        help="Validate existing output rather than regenerating")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    print("\n=== build_pull_probability_model.py ===")

    if not PACK_SOURCES_JSON.exists():
        print(f"ERROR: {PACK_SOURCES_JSON} not found", file=sys.stderr)
        sys.exit(1)

    ps_raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = ps_raw["records"] if isinstance(ps_raw, dict) else ps_raw
    print(f"  Pack sources: {len(records)} records")

    existing_rates = load_existing_rates(OUT_JSON)
    if existing_rates:
        print(f"  Existing rates loaded: {len(existing_rates)} packs")

    pack_records = build_pack_records(records, existing_rates)
    print(f"  Pullable packs: {len(pack_records)}")

    source_status = determine_source_status(pack_records)
    n_inferred = sum(1 for p in pack_records if p.get("confidence") == "inferred")
    n_verified = sum(1 for p in pack_records if p.get("confidence") == "verified")

    out = write_json(pack_records)
    write_md(out, pack_records)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")
    print(f"\n=== Summary ===")
    print(f"  Packs modeled:            {len(pack_records)}")
    print(f"  Source status:            {source_status}")
    print(f"  Inferred slot rates:      {n_inferred}/24 packs")
    print(f"  Verified rates:           {n_verified}/24 packs")
    print(f"  rarity_probabilities:     all null (requires in-app verification)")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
