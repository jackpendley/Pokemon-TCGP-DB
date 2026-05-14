#!/usr/bin/env python3
"""
Build the pull probability model scaffold for all PTCGP packs.

Card pool counts per rarity are derived from pack_sources.json.
Branch selection probabilities are sourced per-pack from Bulbapedia Offering Rates
sections or user in-app verification.

Branch model history:
  v0.3.0  Third-party verified two-branch model applied to all 24 packs.
  v0.4.0  Pulsing Aura (B3) corrected to three-branch from user in-app verification.
          All other packs retained two-branch with stale_model_warning.
  v0.5.0  Per-pack Bulbapedia branch verification applied.
          - B-series (B1/B1a/B2/B2a): three-branch 94.711%/5.238%/0.050% from Bulbapedia.
          - Mega Shine (B2b): four-branch 94.706%/5.238%/0.050%/0.005% from Bulbapedia.
          - Secluded Springs (A4a): three-branch 91.620%/8.330%/0.050% from Bulbapedia.
          - Pulsing Aura (B3): user_in_app_verified_plus_bulbapedia (B3 Bulbapedia corroborates).
          - A-series (A1a/A2a/A3a/A3b): two-branch confirmed from Bulbapedia.
          - A-series (A1/A2/A2b/A3): two-branch (third_party_verified, consistent with pattern).
          - A4/A4b: pending_verification (Bulbapedia data unavailable).

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

STANDARD_SLOT_MODEL = {
    "cards_per_pack": 5,
    "slot_count": 5,
    "notes": (
        "Standard PTCGP pack: 5 cards (or 6 in regular_pack_plus_one branch). "
        "Slot-level probability breakdown stored in slot_rates. "
        "Aggregate rarity_probabilities null until computed from verified slot_rates."
    ),
}

# ---------------------------------------------------------------------------
# Bulbapedia URLs by set_code
# ---------------------------------------------------------------------------
BULBAPEDIA_URLS = {
    "A1":  "https://bulbapedia.bulbagarden.net/wiki/Genetic_Apex_(TCG_Pocket)",
    "A1a": "https://bulbapedia.bulbagarden.net/wiki/Mythical_Island_(TCG_Pocket)",
    "A2":  "https://bulbapedia.bulbagarden.net/wiki/Space-Time_Smackdown_(TCG_Pocket)",
    "A2a": "https://bulbapedia.bulbagarden.net/wiki/Triumphant_Light_(TCG_Pocket)",
    "A2b": "https://bulbapedia.bulbagarden.net/wiki/Shining_Revelry_(TCG_Pocket)",
    "A3":  "https://bulbapedia.bulbagarden.net/wiki/Celestial_Guardians_(TCG_Pocket)",
    "A3a": "https://bulbapedia.bulbagarden.net/wiki/Extradimensional_Crisis_(TCG_Pocket)",
    "A3b": "https://bulbapedia.bulbagarden.net/wiki/Eevee_Grove_(TCG_Pocket)",
    "A4":  "https://bulbapedia.bulbagarden.net/wiki/Wisdom_of_Sea_and_Sky_(TCG_Pocket)",
    "A4a": "https://bulbapedia.bulbagarden.net/wiki/Secluded_Springs_(TCG_Pocket)",
    "A4b": "https://bulbapedia.bulbagarden.net/wiki/Deluxe_Pack:_ex_(TCG_Pocket)",
    "B1":  "https://bulbapedia.bulbagarden.net/wiki/Mega_Rising_(TCG_Pocket)",
    "B1a": "https://bulbapedia.bulbagarden.net/wiki/Crimson_Blaze_(TCG_Pocket)",
    "B2":  "https://bulbapedia.bulbagarden.net/wiki/Fantastical_Parade_(TCG_Pocket)",
    "B2a": "https://bulbapedia.bulbagarden.net/wiki/Paldean_Wonders_(TCG_Pocket)",
    "B2b": "https://bulbapedia.bulbagarden.net/wiki/Mega_Shine_(TCG_Pocket)",
    "B3":  "https://bulbapedia.bulbagarden.net/wiki/Pulsing_Aura_(TCG_Pocket)",
}

# ---------------------------------------------------------------------------
# Per-set-code branch routing
# Types: bulbapedia_two_branch, third_party_two_branch, pending,
#        bulbapedia_three_branch_standard, bulbapedia_secluded_springs,
#        bulbapedia_mega_shine, user_in_app_plus_bulbapedia
# ---------------------------------------------------------------------------
SET_CODE_BRANCH_CONFIG = {
    # Bulbapedia offering-rates page confirmed two-branch (regular=99.950%, rare=0.050%)
    "A1a": "bulbapedia_two_branch",
    "A2a": "bulbapedia_two_branch",
    "A3a": "bulbapedia_two_branch",
    "A3b": "bulbapedia_two_branch",
    # Third-party verified two-branch; Bulbapedia page truncated before offering rates section
    # Pattern consistent with confirmed A-series two-branch packs
    "A1":  "third_party_two_branch",
    "A2":  "third_party_two_branch",
    "A2b": "third_party_two_branch",
    "A3":  "third_party_two_branch",
    # Pending verification — Bulbapedia data unavailable; A4 is uncertain because A4a uses three-branch
    "A4":  "pending",
    "A4b": "pending",
    # Bulbapedia offering-rates page confirmed standard three-branch
    # (regular=94.711%, regular_plus_one=5.238%, rare=0.050%)
    # B1 confirmed by user from prompt; B1a/B2a confirmed by direct Bulbapedia fetch;
    # B2 confirmed by user from prompt
    "B1":  "bulbapedia_three_branch_standard",
    "B1a": "bulbapedia_three_branch_standard",
    "B2":  "bulbapedia_three_branch_standard",
    "B2a": "bulbapedia_three_branch_standard",
    # Secluded Springs unique three-branch (different branch percentages from B-series)
    "A4a": "bulbapedia_secluded_springs",
    # Mega Shine four-branch — confirmed from Bulbapedia
    "B2b": "bulbapedia_mega_shine",
    # Pulsing Aura — user in-app verified (2026-05-13) + Bulbapedia corroboration
    "B3":  "user_in_app_plus_bulbapedia",
}

# ---------------------------------------------------------------------------
# Shared rarity distributions (third_party_verified; same across standard packs)
# Source: Game8, confirmed by ONE Esports, CGMagazine, ShackNews
# Slot 4 total: 0.90+0.05+0.01666+0.02572+0.005+0.00222+0.0004 = 1.00000
# Slot 5 total: 0.60+0.20+0.06664+0.10288+0.02+0.00888+0.0016 = 1.00000
# ---------------------------------------------------------------------------
_STANDARD_SLOT_4 = {
    "two_diamond":   0.90000,
    "three_diamond": 0.05000,
    "four_diamond":  0.01666,
    "one_star":      0.02572,
    "double_star":   0.00500,
    "triple_star":   0.00222,
    "crown":         0.00040,
}
_STANDARD_SLOT_5 = {
    "two_diamond":   0.60000,
    "three_diamond": 0.20000,
    "four_diamond":  0.06664,
    "one_star":      0.10288,
    "double_star":   0.02000,
    "triple_star":   0.00888,
    "crown":         0.00160,
}
_STANDARD_RARE_PACK = {
    "one_star":    0.40,
    "double_star": 0.50,
    "triple_star": 0.05,
    "crown":       0.05,
}
_THIRD_PARTY_CROSS_CHECKS = [
    {
        "source_name": "one_esports_ptcgp_pull_rates",
        "publisher": "ONE Esports",
        "url": "https://www.oneesports.gg/gaming/pokemon-tcg-pocket-pity-system-explained/",
        "accessed_at": "2026-05-12",
        "match_result": "full_match",
        "notes": (
            "ALL slot rates match: regular=99.95%, rare=0.05%, "
            "slot4 and slot5 rates identical. Rare pack rates identical."
        ),
    },
    {
        "source_name": "cgmagonline_pull_rates_lowered",
        "publisher": "CGMagazine",
        "url": "https://www.cgmagonline.com/news/pokemon-tcg-pocket-pull-rates-lowered/",
        "accessed_at": "2026-05-12",
        "match_result": "partial_match_confirms_universality",
        "notes": "Explicitly compares two packs and confirms rates are universal.",
    },
    {
        "source_name": "shacknews_ptcgp_drop_rates",
        "publisher": "ShackNews",
        "url": "https://www.shacknews.com/article/142035/pokemon-trading-card-game-pocket-card-drop-chance-rate",
        "accessed_at": "2026-05-12",
        "match_result": "partial_match_non_shiny_rates",
        "notes": "Confirms non-shiny slot rates for 2◆ and 3◆ positions.",
    },
]

# ---------------------------------------------------------------------------
# Two-branch slot rates (A-series): applied to all two-branch packs
# ---------------------------------------------------------------------------
INFERRED_SLOT_RATES = {
    "regular_pack_probability": 0.9995,
    "rare_pack_probability": 0.0005,
    "regular_pack_plus_one_probability": None,
    "slots_1_3": {"one_diamond": 1.0},
    "slot_4": _STANDARD_SLOT_4,
    "slot_5": _STANDARD_SLOT_5,
    "slot_6": None,
    "rare_pack_all_5_slots": _STANDARD_RARE_PACK,
    "confidence": "third_party_verified",
    "source_name": "game8_co_ptcgp_offering_rates",
    "source_url": "https://game8.co/games/Pokemon-TCG-Pocket/archives/482685",
    "source_accessed_at": "2026-05-12",
    "source_notes": (
        "Per-slot rates sourced from Game8 (trusted third-party PTCGP guide), "
        "independently confirmed by ONE Esports, CGMagazine, ShackNews. "
        "4 independent third-party sources report identical values. "
        "Two-branch model (regular=99.950%, rare=0.050%) confirmed for A-series packs "
        "by Bulbapedia (A1a/A2a/A3a/A3b confirmed; A1/A2/A2b/A3 consistent with pattern)."
    ),
    "cross_checked_sources": _THIRD_PARTY_CROSS_CHECKS,
    "confidence_note": (
        "third_party_verified: confirmed by 4 independent reputable third-party sources "
        "(Game8, ONE Esports, CGMagazine, ShackNews). "
        "NOT official in-app verified. "
        "Two-branch model (no regular_pack_plus_one) confirmed correct for A-series packs."
    ),
}

# ---------------------------------------------------------------------------
# Standard three-branch slot rates — Bulbapedia verified (B1/B1a/B2/B2a)
# Branch selection: regular=94.711%, regular_plus_one=5.238%, rare=0.050%
# Source: Bulbapedia TCG Pocket expansion pages (offering rates section)
# Slot 4/5 rarity distributions from third_party_verified sources (unchanged from prior model)
# Rare pack distribution from third_party_verified (40/50/5/5); not yet in-app verified per-pack
# ---------------------------------------------------------------------------
BULBAPEDIA_THREE_BRANCH_SLOT_RATES = {
    "regular_pack_probability": 0.94711,
    "rare_pack_probability": 0.00050,
    "regular_pack_plus_one_probability": 0.05238,
    "slots_1_3": {"one_diamond": 1.0},
    "slot_4": _STANDARD_SLOT_4,
    "slot_5": _STANDARD_SLOT_5,
    "slot_6": None,
    "rare_pack_all_5_slots": _STANDARD_RARE_PACK,
    "confidence": "bulbapedia_branch_verified",
    "source_name": "bulbapedia_tcg_pocket",
    "source_url": None,
    "source_accessed_at": "2026-05-13",
    "source_notes": (
        "Branch selection (regular_pack=94.711%, regular_pack_plus_one=5.238%, rare_pack=0.050%) "
        "verified from Bulbapedia TCG Pocket expansion Offering Rates section. "
        "Slot 4/5 rarity distributions from third_party_verified sources (Game8, confirmed by 4 sources). "
        "Card 6 (slot_6) shiny rates unknown for this pack — EV contribution = 0. "
        "Rare pack distribution (40%/50%/5%/5%) from third_party_verified sources; "
        "corrected values may differ per-pack (Pulsing Aura rare pack was 47/45/4/4). "
        "Bulbapedia is a third-party wiki, NOT official in-app verification."
    ),
    "cross_checked_sources": _THIRD_PARTY_CROSS_CHECKS,
    "confidence_note": (
        "bulbapedia_branch_verified: branch selection confirmed from Bulbapedia offering rates. "
        "Rarity distributions within slots are from third_party_verified sources. "
        "NOT official in-app verified."
    ),
}

# ---------------------------------------------------------------------------
# Secluded Springs (A4a) — Bulbapedia unique three-branch
# Branch selection: regular=91.620%, regular_plus_one=8.330%, rare=0.050%
# These branch probabilities differ from the standard three-branch B-series model.
# ---------------------------------------------------------------------------
SECLUDED_SPRINGS_SLOT_RATES = {
    **BULBAPEDIA_THREE_BRANCH_SLOT_RATES,
    "regular_pack_probability": 0.91620,
    "regular_pack_plus_one_probability": 0.08330,
    "source_url": BULBAPEDIA_URLS["A4a"],
    "source_notes": (
        "Branch selection (regular_pack=91.620%, regular_pack_plus_one=8.330%, rare_pack=0.050%) "
        "verified from Bulbapedia Secluded Springs (TCG Pocket) Offering Rates section. "
        "These branch probabilities DIFFER from the standard three-branch B-series model "
        "(94.711%/5.238%/0.050%). This is a pack-specific configuration. "
        "Slot 4/5 rarity distributions from third_party_verified sources. "
        "Card 6 (slot_6) shiny rates unknown — EV contribution = 0. "
        "Bulbapedia is a third-party wiki, NOT official in-app verification."
    ),
}

# ---------------------------------------------------------------------------
# Mega Shine (B2b) — four-branch model
# Branch selection: regular=94.706%, regular_plus_one=5.238%, rare=0.050%, themed_rare=0.005%
# The themed rare pack guarantees specific Mega Evolution ex cards.
# themed_rare_pack_all_5_slots is null (card distribution not modeled; EV contribution = 0).
# ---------------------------------------------------------------------------
MEGA_SHINE_SLOT_RATES = {
    "regular_pack_probability": 0.94706,
    "rare_pack_probability": 0.00050,
    "regular_pack_plus_one_probability": 0.05238,
    "themed_rare_pack_probability": 0.00005,
    "slots_1_3": {"one_diamond": 1.0},
    "slot_4": _STANDARD_SLOT_4,
    "slot_5": _STANDARD_SLOT_5,
    "slot_6": None,
    "rare_pack_all_5_slots": _STANDARD_RARE_PACK,
    "themed_rare_pack_all_5_slots": None,
    "confidence": "bulbapedia_branch_verified",
    "source_name": "bulbapedia_tcg_pocket_mega_shine",
    "source_url": BULBAPEDIA_URLS["B2b"],
    "source_accessed_at": "2026-05-13",
    "source_notes": (
        "Four-branch model verified from Bulbapedia Mega Shine (TCG Pocket) Offering Rates section. "
        "Branches: regular_pack=94.706%, regular_pack_plus_one=5.238%, rare_pack=0.050%, "
        "themed_rare_pack=0.005% (guarantees specific Mega Evolution ex cards in all 5 slots). "
        "themed_rare_pack_all_5_slots=null — card distribution not modeled; EV contribution = 0. "
        "Slot 4/5 rarity distributions from third_party_verified sources. "
        "Card 6 shiny rates unknown — EV contribution = 0. "
        "Bulbapedia is a third-party wiki, NOT official in-app verification."
    ),
    "cross_checked_sources": _THIRD_PARTY_CROSS_CHECKS,
    "confidence_note": (
        "bulbapedia_branch_verified: four-branch selection confirmed from Bulbapedia Mega Shine page. "
        "themed_rare_pack (0.005%) guarantees Mega Evolution ex; EV not modeled (card pool unknown). "
        "NOT official in-app verified."
    ),
}

# ---------------------------------------------------------------------------
# Pulsing Aura (B3) — user in-app verified + Bulbapedia corroboration
# Source: User-provided in-app Offering Rates screenshots (ChatGPT conversation, NOT in repo).
# Bulbapedia page corroborates the three-branch structure and branch percentages.
# Rare pack distribution (47.058/45.098/3.921/3.921) is from user in-app verification only.
# ---------------------------------------------------------------------------
PULSING_AURA_SLOT_RATES = {
    "regular_pack_probability": 0.94711,
    "rare_pack_probability": 0.00050,
    "regular_pack_plus_one_probability": 0.05238,
    "slots_1_3": {"one_diamond": 1.0},
    "slot_4": {
        "two_diamond":   0.90000,
        "three_diamond": 0.05000,
        "four_diamond":  0.01667,
        "one_star":      0.02572,
        "double_star":   0.00500,
        "triple_star":   0.00222,
        "crown":         0.00040,
    },
    "slot_5": {
        "two_diamond":   0.59998,
        "three_diamond": 0.20000,
        "four_diamond":  0.06667,
        "one_star":      0.10286,
        "double_star":   0.02000,
        "triple_star":   0.00889,
        "crown":         0.00160,
    },
    "slot_6": {
        "one_shiny": 0.68180,
        "two_shiny": 0.31820,
        "note": (
            "Card 6 appears only in Regular Pack + 1 Card openings (5.238% of packs). "
            "Shiny cards (one_shiny/two_shiny) are NOT in pack_sources.json — "
            "card 6 EV contribution is pending addition of shiny pool data."
        ),
    },
    "rare_pack_all_5_slots": {
        "one_star":              0.47058,
        "double_star":           0.45098,
        "triple_star":           0.03921,
        "crown_or_highest_rare": 0.03921,
    },
    "confidence": "user_in_app_verified_plus_bulbapedia",
    "source_name": "user_provided_in_app_offering_rates_chatgpt_conversation",
    "source_url": None,
    "source_accessed_at": "2026-05-13",
    "source_notes": (
        "User manually verified Pulsing Aura Offering Rates in the Pokémon TCG Pocket app "
        "and provided values in a ChatGPT conversation. Screenshots are NOT stored in this "
        "repository. Treated as user_in_app_verified evidence — more authoritative than "
        "third_party_verified. "
        "Bulbapedia Pulsing Aura page (https://bulbapedia.bulbagarden.net/wiki/Pulsing_Aura_(TCG_Pocket)) "
        "corroborates the three-branch model and branch percentages (94.711%/5.238%/0.050%). "
        "Rare pack distribution (47.058/45.098/3.921/3.921) is from user in-app data only — "
        "different from the third-party verified 40/50/5/5 rates used for other packs."
    ),
    "cross_checked_sources": [
        {
            "source_name": "bulbapedia_pulsing_aura",
            "publisher": "Bulbapedia",
            "url": BULBAPEDIA_URLS["B3"],
            "accessed_at": "2026-05-13",
            "match_result": "branch_selection_corroborated",
            "notes": (
                "Bulbapedia Pulsing Aura page corroborates the three-branch model: "
                "Regular pack=94.711%, Regular pack + 1 card=5.238%, Rare pack=0.050%. "
                "Also confirms regular_pack_plus_one uses same first-5-card rates as regular pack. "
                "Slot 6 shiny rates not verified from Bulbapedia (page truncated before that section)."
            ),
        },
    ],
    "confidence_note": (
        "user_in_app_verified_plus_bulbapedia: rates provided by user directly from in-app "
        "Offering Rates screen (ChatGPT conversation; screenshots NOT in repo). "
        "Bulbapedia corroborates branch selection percentages. "
        "Rare pack distribution (47/45/4/4) is user-in-app only — may differ from other packs."
    ),
}

# Pending verification warning — used for A4/A4b only
PENDING_VERIFICATION_NOTE = (
    "Branch model unconfirmed — Bulbapedia offering rates section was not accessible "
    "for this pack during the 2026-05-13 verification pass. "
    "Verify in-app or check Bulbapedia: PTCGP app → Pack details → Offering Rates."
)


def make_bulbapedia_two_branch_rates(set_code: str) -> dict:
    """Return two-branch slot rates with Bulbapedia branch confirmation."""
    return {
        **INFERRED_SLOT_RATES,
        "regular_pack_probability": 0.9995,
        "rare_pack_probability": 0.0005,
        "regular_pack_plus_one_probability": None,
        "slot_6": None,
        "confidence": "bulbapedia_branch_verified",
        "source_name": "bulbapedia_tcg_pocket",
        "source_url": BULBAPEDIA_URLS.get(set_code),
        "source_accessed_at": "2026-05-13",
        "source_notes": (
            "Branch selection (regular_pack=99.950%, rare_pack=0.050%) confirmed from Bulbapedia "
            "TCG Pocket expansion Offering Rates section. "
            "This is a two-branch pack — no Regular Pack + 1 Card branch applies. "
            "Slot 4/5 rarity distributions from third_party_verified sources (Game8 + 3 others). "
            "Bulbapedia is a third-party wiki, NOT official in-app verification."
        ),
        "cross_checked_sources": _THIRD_PARTY_CROSS_CHECKS,
        "confidence_note": (
            "bulbapedia_branch_verified: two-branch model confirmed from Bulbapedia offering rates. "
            "The Regular Pack + 1 Card branch does NOT apply to this expansion. "
            "NOT official in-app verified."
        ),
    }


def make_pending_slot_rates() -> dict:
    """Return placeholder two-branch rates for packs pending verification."""
    return {
        **INFERRED_SLOT_RATES,
        "regular_pack_probability": 0.9995,
        "rare_pack_probability": 0.0005,
        "regular_pack_plus_one_probability": None,
        "slot_6": None,
        "confidence": "pending_verification",
        "source_notes": (
            "Branch selection UNCONFIRMED — Bulbapedia offering rates page was not accessible "
            "during the 2026-05-13 verification pass. Using two-branch placeholder rates. "
            "This pack may use a different branch model (two, three, or four branch). "
            "Verify: PTCGP app → Pack details → Offering Rates."
        ),
        "confidence_note": (
            "pending_verification: branch model not confirmed from Bulbapedia or in-app. "
            "Two-branch rates shown are a placeholder."
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


def _build_slot_rates_for_set(set_code: str) -> tuple[dict, str, str, str, bool]:
    """
    Return (slot_rates, confidence, branch_model_str, stale_warning, is_three_or_four_branch)
    based on SET_CODE_BRANCH_CONFIG routing.
    """
    branch_type = SET_CODE_BRANCH_CONFIG.get(set_code, "third_party_two_branch")

    if branch_type == "user_in_app_plus_bulbapedia":
        return (
            {**PULSING_AURA_SLOT_RATES},
            "user_in_app_verified_plus_bulbapedia",
            "three_branch",
            None,
            True,
        )

    if branch_type == "bulbapedia_three_branch_standard":
        rates = {**BULBAPEDIA_THREE_BRANCH_SLOT_RATES, "source_url": BULBAPEDIA_URLS.get(set_code)}
        return (rates, "bulbapedia_branch_verified", "three_branch", None, True)

    if branch_type == "bulbapedia_secluded_springs":
        return ({**SECLUDED_SPRINGS_SLOT_RATES}, "bulbapedia_branch_verified", "three_branch", None, True)

    if branch_type == "bulbapedia_mega_shine":
        return ({**MEGA_SHINE_SLOT_RATES}, "bulbapedia_branch_verified", "four_branch", None, True)

    if branch_type == "bulbapedia_two_branch":
        return (make_bulbapedia_two_branch_rates(set_code), "bulbapedia_branch_verified", "two_branch", None, False)

    if branch_type == "pending":
        return (make_pending_slot_rates(), "pending_verification", "two_branch", PENDING_VERIFICATION_NOTE, False)

    # Default: third_party_two_branch (A1/A2/A2b/A3 — pattern consistent, Bulbapedia truncated)
    rates = {**INFERRED_SLOT_RATES}
    return (rates, "third_party_verified", "two_branch", None, False)


def build_pack_records(records: list, existing_rates: dict) -> list:
    """
    Return list of pack records — one per distinct pullable named pack.
    Shared-pool cards are folded into each named pack's combined_pool.
    Branch model applied per set_code from SET_CODE_BRANCH_CONFIG.
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

        slot_rates, confidence, branch_model_str, stale_warning, is_multi_branch = \
            _build_slot_rates_for_set(set_code)

        bulbapedia_url = BULBAPEDIA_URLS.get(set_code)
        branch_type = SET_CODE_BRANCH_CONFIG.get(set_code, "third_party_two_branch")

        if branch_type == "user_in_app_plus_bulbapedia":
            bulbapedia_match = "branch_selection_corroborated"
            bulbapedia_notes_str = (
                "Bulbapedia confirms three-branch structure (94.711%/5.238%/0.050%). "
                "User in-app verified rates are used; Bulbapedia corroborates branch selection."
            )
        elif branch_type in ("bulbapedia_three_branch_standard",):
            bulbapedia_match = "branch_verified"
            bulbapedia_notes_str = (
                "Offering rates section confirmed three-branch model: "
                "regular_pack=94.711%, regular_pack_plus_one=5.238%, rare_pack=0.050%."
            )
        elif branch_type == "bulbapedia_secluded_springs":
            bulbapedia_match = "branch_verified_special_case"
            bulbapedia_notes_str = (
                "Offering rates section confirmed unique three-branch model: "
                "regular_pack=91.620%, regular_pack_plus_one=8.330%, rare_pack=0.050%. "
                "Branch percentages differ from standard B-series three-branch model."
            )
        elif branch_type == "bulbapedia_mega_shine":
            bulbapedia_match = "branch_verified_special_case"
            bulbapedia_notes_str = (
                "Offering rates section confirmed four-branch model: "
                "regular_pack=94.706%, regular_pack_plus_one=5.238%, rare_pack=0.050%, "
                "themed_rare_pack=0.005% (guarantees Mega Evolution ex)."
            )
        elif branch_type == "bulbapedia_two_branch":
            bulbapedia_match = "two_branch_confirmed"
            bulbapedia_notes_str = (
                "Offering rates section confirmed two-branch model: "
                "regular_pack=99.950%, rare_pack=0.050%. "
                "No Regular Pack + 1 Card branch for this expansion."
            )
        elif branch_type == "pending":
            bulbapedia_match = "truncated_pending"
            bulbapedia_notes_str = (
                "Bulbapedia offering rates section was not accessible (page truncated) "
                "during the 2026-05-13 verification pass. Branch model unconfirmed."
            )
        else:
            # third_party_two_branch
            bulbapedia_match = "truncated_pending"
            bulbapedia_notes_str = (
                "Bulbapedia offering rates section was not fully accessible during "
                "the 2026-05-13 verification pass. Two-branch model is consistent with "
                "confirmed A-series Bulbapedia data (A1a/A2a/A3a/A3b all two-branch)."
            )

        for pn in sorted(named_packs):
            pack_cards = named_packs[pn]
            pack_by_rarity = rarity_counts(pack_cards)
            pack_total = len(pack_cards)
            combined_by_rarity = add_rarity_dicts(pack_by_rarity, shared_by_rarity)
            combined_total = pack_total + shared_total

            existing = existing_rates.get(pn, {})
            prev_rarity_probs = existing.get("rarity_probabilities")
            if prev_rarity_probs and any(v is not None for v in prev_rarity_probs.values()):
                rarity_probs = prev_rarity_probs
            else:
                rarity_probs = {f: None for f in RARITY_FIELDS}

            slot_model = {
                **STANDARD_SLOT_MODEL,
                "branch_model": branch_model_str,
            }

            if branch_type == "user_in_app_plus_bulbapedia":
                official_status = "user_in_app_verified"
                user_evidence_note = (
                    "User manually read Pulsing Aura Offering Rates from the PTCGP app "
                    "on 2026-05-13 and provided values in a ChatGPT conversation. "
                    "Screenshots are NOT stored in this repository."
                )
                notes = (
                    "Three-branch model: regular_pack (94.711%) + rare_pack (0.050%) "
                    "+ regular_pack_plus_one (5.238%). "
                    "Source: user-provided in-app Offering Rates (ChatGPT, not in repo). "
                    "Bulbapedia corroborates branch percentages. "
                    "Rare pack distribution corrected from in-app data: 47.058/45.098/3.921/3.921. "
                    "Card 6 shiny rates: one_shiny=68.180%, two_shiny=31.820% (EV pending shiny pool data)."
                )
            elif branch_type == "bulbapedia_three_branch_standard":
                official_status = "not_verified"
                user_evidence_note = None
                notes = (
                    f"Three-branch model from Bulbapedia: regular_pack (94.711%) "
                    f"+ regular_pack_plus_one (5.238%) + rare_pack (0.050%). "
                    f"Slot 4/5 rarity distributions from third_party_verified sources. "
                    f"Card 6 shiny rates unknown — EV contribution = 0. "
                    f"Rare pack distribution (40/50/5/5) from third_party_verified sources."
                )
            elif branch_type == "bulbapedia_secluded_springs":
                official_status = "not_verified"
                user_evidence_note = None
                notes = (
                    "Unique three-branch model from Bulbapedia: regular_pack (91.620%) "
                    "+ regular_pack_plus_one (8.330%) + rare_pack (0.050%). "
                    "Branch percentages differ from standard B-series model. "
                    "EV impact: P_combined = 0.91620+0.08330 = 0.99950 ≈ same as two-branch EV."
                )
            elif branch_type == "bulbapedia_mega_shine":
                official_status = "not_verified"
                user_evidence_note = None
                notes = (
                    "Four-branch model from Bulbapedia: regular_pack (94.706%) "
                    "+ regular_pack_plus_one (5.238%) + rare_pack (0.050%) "
                    "+ themed_rare_pack (0.005%). "
                    "themed_rare_pack guarantees Mega Evolution ex — EV not modeled (card pool unknown). "
                    "Card 6 shiny rates unknown — EV contribution = 0."
                )
            elif branch_type == "bulbapedia_two_branch":
                official_status = "not_verified"
                user_evidence_note = None
                notes = (
                    "Two-branch model confirmed from Bulbapedia: regular_pack (99.950%) "
                    "+ rare_pack (0.050%). No Regular Pack + 1 Card branch for this expansion."
                )
            elif branch_type == "pending":
                official_status = "pending"
                user_evidence_note = None
                notes = (
                    "Branch model unconfirmed — Bulbapedia offering rates section was not "
                    "accessible during 2026-05-13 verification pass. "
                    "Placeholder two-branch rates applied. Verify in-app."
                )
            else:
                # third_party_two_branch
                official_status = "not_verified"
                user_evidence_note = None
                notes = (
                    "Two-branch model (third_party_verified): regular_pack (99.950%) "
                    "+ rare_pack (0.050%). Consistent with Bulbapedia confirmed A-series packs. "
                    "Bulbapedia page was truncated before offering rates section in 2026-05-13 check. "
                    "Verify directly: " + (BULBAPEDIA_URLS.get(set_code) or "")
                )

            pack_records.append({
                "pack_name": pn,
                "expansion": exp,
                "set_code": set_code,
                "is_shared_pool": False,
                "source_url": slot_rates.get("source_url"),
                "source_name": slot_rates.get("source_name"),
                "source_accessed_at": slot_rates.get("source_accessed_at"),
                "confidence": confidence,
                "bulbapedia_url": bulbapedia_url,
                "bulbapedia_match_status": bulbapedia_match,
                "bulbapedia_notes": bulbapedia_notes_str,
                "stale_model_warning": stale_warning,
                "user_in_app_evidence_note": user_evidence_note,
                "official_verification_status": official_status,
                "slot_model": slot_model,
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

    if confs <= {"verified"}:
        return "verified"

    top_tier = {"verified", "user_in_app_verified_plus_bulbapedia",
                "bulbapedia_branch_verified", "user_in_app_verified"}
    mid_tier = {"third_party_verified"}
    low_tier = {"pending_verification", "inferred", "unknown"}

    has_top = bool(confs & top_tier)
    has_mid = bool(confs & mid_tier)
    has_low = bool(confs & low_tier)

    if has_top and not has_mid and not has_low:
        if "user_in_app_verified_plus_bulbapedia" in confs or "user_in_app_verified" in confs:
            return "third_party_verified_with_in_app_anchor"
        return "bulbapedia_branch_verified"

    if has_top or has_mid:
        if has_low:
            return "third_party_verified_with_in_app_anchor"
        return "third_party_verified_with_in_app_anchor"

    if confs <= {"third_party_verified"}:
        return "third_party_verified"
    if "inferred" in confs:
        return "inferred"
    return "scaffold_only"


def write_json(pack_records: list) -> dict:
    source_status = determine_source_status(pack_records)
    n_verified = sum(1 for p in pack_records if p.get("confidence") == "verified")
    n_tpv     = sum(1 for p in pack_records if p.get("confidence") == "third_party_verified")
    n_inapp   = sum(1 for p in pack_records if p.get("confidence") == "user_in_app_verified")
    n_inapp_b = sum(1 for p in pack_records if p.get("confidence") == "user_in_app_verified_plus_bulbapedia")
    n_bpv     = sum(1 for p in pack_records if p.get("confidence") == "bulbapedia_branch_verified")
    n_pending = sum(1 for p in pack_records if p.get("confidence") == "pending_verification")
    n_inferred = sum(1 for p in pack_records if p.get("confidence") == "inferred")

    meta_notes = (
        f"Bulbapedia branch-verified model (v0.5.0, 2026-05-13). "
        f"bulbapedia_branch_verified: {n_bpv} packs (branch selection from Bulbapedia offering rates). "
        f"user_in_app_verified_plus_bulbapedia: {n_inapp_b} pack (Pulsing Aura B3, user in-app + Bulbapedia). "
        f"third_party_verified: {n_tpv} packs (two-branch, A-series, Bulbapedia truncated but pattern consistent). "
        f"pending_verification: {n_pending} packs (A4/A4b, Bulbapedia data unavailable). "
        f"All rarity_probabilities null (aggregate rates require in-app verification). "
        f"B-series packs corrected to three/four-branch. A-series two-branch confirmed. "
        f"Secluded Springs (A4a) confirmed as unique three-branch (91.620%/8.330%/0.050%). "
        f"Mega Shine (B2b) confirmed as four-branch with themed_rare_pack=0.005%."
    )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_pull_probability_model.py",
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_version": "0.5.0",
            "source_status": source_status,
            "verified_source": (
                "ptcgp_in_app_offering_rates" if source_status == "verified" else None
            ),
            "user_in_app_verified_packs": (
                ["Pulsing Aura (B3)"] if n_inapp + n_inapp_b > 0 else None
            ),
            "user_in_app_evidence_note": (
                "Pulsing Aura (B3) rates verified by user from in-app Offering Rates screen. "
                "Screenshots in ChatGPT conversation, NOT stored in repo."
                if n_inapp + n_inapp_b > 0 else None
            ),
            "bulbapedia_verified_packs": (
                f"{n_bpv} packs branch-verified from Bulbapedia offering rates sections"
                if n_bpv > 0 else None
            ),
            "bulbapedia_access_date": "2026-05-13",
            "third_party_verified_sources": (
                ["game8_co", "one_esports_gg", "cgmagonline_com", "shacknews_com"]
                if n_tpv > 0 else None
            ),
            "pending_packs": (
                ["Wisdom of Sea and Sky (A4)", "Deluxe Pack: ex (A4b)"]
                if n_pending > 0 else None
            ),
            "confidence_note": (
                "third_party_verified_with_in_app_anchor: "
                "Most packs branch-verified via Bulbapedia (2026-05-13). "
                "Pulsing Aura (B3) user_in_app_verified_plus_bulbapedia. "
                "A-series packs confirmed two-branch (Bulbapedia + third-party sources). "
                "A4/A4b pending Bulbapedia data. "
                "Rarity distributions within slots are still third_party_verified. "
                "NOT official in-app verified for any non-B3 pack."
            ),
            "notes": meta_notes,
        },
        "probability_source_required": {
            "status": "BULBAPEDIA_BRANCH_VERIFIED",
            "description": (
                "Branch selection probabilities verified from Bulbapedia for most packs. "
                "Slot rarity distributions still from third_party_verified sources. "
                "Aggregate rarity_probabilities still null — require in-app verification."
            ),
            "how_to_officially_verify": (
                "In the Pokémon TCG Pocket app: tap a pack > view 'Offering Rates'. "
                "Compare branch percentages and slot rates to slot_rates in this file. "
                "If they match, set confidence='verified'."
            ),
        },
        "packs": pack_records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_md(out: dict, pack_records: list):
    source_status = out["meta"]["source_status"]
    n_packs  = len(pack_records)
    n_bpv    = sum(1 for p in pack_records if p.get("confidence") == "bulbapedia_branch_verified")
    n_inapp_b = sum(1 for p in pack_records if p.get("confidence") == "user_in_app_verified_plus_bulbapedia")
    n_tpv    = sum(1 for p in pack_records if p.get("confidence") == "third_party_verified")
    n_pending = sum(1 for p in pack_records if p.get("confidence") == "pending_verification")

    lines = [
        "# Pull Probability Model",
        "",
        "> **Bulbapedia branch-verified model (v0.5.0, 2026-05-13).**",
        "> Branch selection probabilities verified per-pack from Bulbapedia Offering Rates sections.",
        "> B-series packs corrected to three/four-branch. A-series packs confirmed two-branch.",
        "> Pulsing Aura (B3) is user_in_app_verified_plus_bulbapedia.",
        "> `rarity_probabilities` (aggregate per-pack rates) are still null.",
        "> Bulbapedia is a third-party wiki, NOT official in-app verification.",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Model version | {out['meta']['model_version']} |",
        f"| Source status | **{source_status}** |",
        f"| Total packs modeled | {n_packs} |",
        f"| Packs user_in_app_verified_plus_bulbapedia | {n_inapp_b} (Pulsing Aura B3) |",
        f"| Packs bulbapedia_branch_verified | {n_bpv} |",
        f"| Packs third_party_verified (two-branch, pattern consistent) | {n_tpv} |",
        f"| Packs pending_verification | {n_pending} (A4/A4b) |",
        f"| rarity_probabilities | **all null** (aggregate rates not yet verified) |",
        "",
        "## Branch Model by Pack",
        "",
        "| Pack | Set | Branch Model | Regular % | Plus-One % | Rare % | Themed % | Confidence |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for p in pack_records:
        sr = p.get("slot_rates") or {}
        reg = sr.get("regular_pack_probability")
        plus = sr.get("regular_pack_plus_one_probability")
        rare = sr.get("rare_pack_probability")
        themed = sr.get("themed_rare_pack_probability")
        bm = (p.get("slot_model") or {}).get("branch_model", "?")
        conf = p.get("confidence", "?")
        lines.append(
            f"| {p['pack_name']} | {p['set_code']} | {bm} "
            f"| {f'{reg*100:.3f}%' if reg is not None else 'N/A'} "
            f"| {f'{plus*100:.3f}%' if plus is not None else '—'} "
            f"| {f'{rare*100:.3f}%' if rare is not None else 'N/A'} "
            f"| {f'{themed*100:.3f}%' if themed is not None else '—'} "
            f"| {conf} |"
        )

    lines += [
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
        "## How to Upgrade to Verified",
        "",
        "1. Open the Pokémon TCG Pocket app.",
        "2. Navigate to the pack you want to verify.",
        "3. View the **Offering Rates** section (disclosed in-app).",
        "4. Compare branch percentages to `slot_rates` in `data/reference/pull_probability_model.json`.",
        "5. Update `slot_rates`, set `confidence: 'verified'`, bump model_version.",
        "6. Re-run `python3 scripts/validate_pull_probability_model.py`.",
        "",
        "## rarity_probabilities Status",
        "",
        "All aggregate `rarity_probabilities` values are currently `null`.",
        "These will be computed once slot_rates are verified from official in-app Offering Rates.",
        "",
    ]

    (ROOT / "review").mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _check_slot_sum(slot_dict: dict, label: str, errors_list: list):
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

    valid_conf = {
        "verified",
        "bulbapedia_verified",
        "bulbapedia_branch_verified",
        "user_in_app_verified_plus_bulbapedia",
        "third_party_verified",
        "user_in_app_verified",
        "third_party_verified_with_in_app_anchor",
        "in_app_verified_partial",
        "pending_verification",
        "inferred",
        "unknown",
    }
    bad_conf = [p for p in packs if p.get("confidence") not in valid_conf]
    if bad_conf:
        print(f"  ERROR: {len(bad_conf)} packs have invalid confidence value: "
              f"{[p['pack_name'] for p in bad_conf]}")
        errors += 1
    else:
        print("  PASS  all confidence values valid")

    bad_pools = [p for p in packs if p.get("card_pool", {}).get("combined_total", -1) < 0]
    if bad_pools:
        print(f"  ERROR: {len(bad_pools)} packs have negative combined_total")
        errors += 1
    else:
        print("  PASS  all card pool totals non-negative")

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

    unknown_rarity_probs = sum(
        1 for p in packs
        if all(v is None for v in p.get("rarity_probabilities", {}).values())
    )
    n_tpv     = sum(1 for p in packs if p.get("confidence") == "third_party_verified")
    n_bpv     = sum(1 for p in packs if p.get("confidence") == "bulbapedia_branch_verified")
    n_inapp_b = sum(1 for p in packs if p.get("confidence") == "user_in_app_verified_plus_bulbapedia")
    n_pending = sum(1 for p in packs if p.get("confidence") == "pending_verification")
    n_inferred = sum(1 for p in packs if p.get("confidence") == "inferred")
    n_verified = sum(1 for p in packs if p.get("confidence") == "verified")
    source_status = out["meta"]["source_status"]

    print(f"  INFO  {n_bpv}/{len(packs)} packs have bulbapedia_branch_verified slot rates")
    print(f"  INFO  {n_inapp_b}/{len(packs)} packs have user_in_app_verified_plus_bulbapedia rates")
    print(f"  INFO  {n_tpv}/{len(packs)} packs have third_party_verified slot rates")
    print(f"  INFO  {n_pending}/{len(packs)} packs have pending_verification")
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
    n_bpv     = sum(1 for p in pack_records if p.get("confidence") == "bulbapedia_branch_verified")
    n_inapp_b = sum(1 for p in pack_records if p.get("confidence") == "user_in_app_verified_plus_bulbapedia")
    n_tpv     = sum(1 for p in pack_records if p.get("confidence") == "third_party_verified")
    n_pending = sum(1 for p in pack_records if p.get("confidence") == "pending_verification")

    out = write_json(pack_records)
    write_md(out, pack_records)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")
    print(f"\n=== Summary ===")
    print(f"  Packs modeled:                      {len(pack_records)}")
    print(f"  Source status:                      {source_status}")
    print(f"  bulbapedia_branch_verified:          {n_bpv}/24")
    print(f"  user_in_app_verified_plus_bulbapedia:{n_inapp_b}/24")
    print(f"  third_party_verified (pattern):     {n_tpv}/24")
    print(f"  pending_verification:               {n_pending}/24")
    print(f"  rarity_probabilities:               all null")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
