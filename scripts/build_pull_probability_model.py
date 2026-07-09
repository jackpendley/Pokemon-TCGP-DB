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
  v0.6.0  A4 (Wisdom of Sea and Sky) verified from in-repo Offering Rates screenshots (2026-05-14).
          - Ho-Oh/Lugia: three-branch 91.620%/8.330%/0.050% (matches A4a); slot_6 confirmed
            (illustration_rare=12.900%, rare=87.100% — standard rarity, NOT shiny).
          - A4b (Deluxe Pack: ex): remains pending_verification (pack unavailable, 4 cards/pack).

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
sys.path.insert(0, str(ROOT / "scripts"))
from _collection_io import (  # noqa: E402 (after sys.path insert)
    RARITIES as RARITY_FIELDS, normalize_rarity, card_reference_by_coord,
    PACK_SOURCES_JSON, PZ_PACK_ODDS_JSON, CARD_REF_JSON, CURRENT_DIR,
    PULL_MODEL_JSON as OUT_JSON,
    A4B_SET_CODE, PROMO_SET_CODES,
)
# Reuse the EV computation's PZ loaders/slug-matcher so the per-rarity-per-pack
# probabilities are derived from the exact same Pokémon Zone source the EV model uses.
from build_pack_ev import load_pz_pack_odds, resolve_pz_slug  # noqa: E402

CONFIDENCE_SCORES_JSON = CURRENT_DIR / "pack_source_confidence_scores.json"
OUT_MD = ROOT / "review" / "pull_probability_model.md"

STANDARD_SLOT_MODEL = {
    "cards_per_pack": 5,
    "slot_count": 5,
    "notes": (
        "Standard PTCGP pack: 5 cards (or 6 in regular_pack_plus_one branch). "
        "Slot-level probability breakdown stored in slot_rates. "
        "Aggregate rarity_probabilities = expected copies/rarity/pack from Pokémon Zone drop chances."
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
    # A4 (Wisdom of Sea and Sky) — user in-app verified from in-repo screenshots 2026-05-14
    # Three-branch: regular=91.620%, regular_plus_one=8.330%, rare=0.050%
    # Matches Secluded Springs (A4a) branch percentages exactly.
    "A4":  "user_in_app_verified_a4",
    # A4b (Deluxe Pack: ex) — pack unavailable in app; Offering Rates inaccessible. 4 cards/pack.
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
    "uncommon":      0.90000,
    "rare":          0.05000,
    "double_rare":   0.01666,
    "illustration_rare": 0.02572,
    "super_rare":    0.00500,
    "immersive":     0.00222,
    "ultra_rare":    0.00040,
}
_STANDARD_SLOT_5 = {
    "uncommon":      0.60000,
    "rare":          0.20000,
    "double_rare":   0.06664,
    "illustration_rare": 0.10288,
    "super_rare":    0.02000,
    "immersive":     0.00888,
    "ultra_rare":    0.00160,
}
_STANDARD_RARE_PACK = {
    "illustration_rare": 0.40,
    "super_rare":        0.50,
    "immersive":         0.05,
    "ultra_rare":        0.05,
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
    "slots_1_3": {"common": 1.0},
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
    "slots_1_3": {"common": 1.0},
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
    "slots_1_3": {"common": 1.0},
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
    "slots_1_3": {"common": 1.0},
    "slot_4": {
        "uncommon":   0.90000,
        "rare": 0.05000,
        "double_rare":  0.01667,
        "illustration_rare":      0.02572,
        "super_rare":   0.00500,
        "immersive":   0.00222,
        "ultra_rare":         0.00040,
    },
    "slot_5": {
        "uncommon":   0.59998,
        "rare": 0.20000,
        "double_rare":  0.06667,
        "illustration_rare":      0.10286,
        "super_rare":   0.02000,
        "immersive":   0.00889,
        "ultra_rare":         0.00160,
    },
    "slot_6": {
        "shiny_rare": 0.68180,
        "shiny_super_rare": 0.31820,
        "note": (
            "Card 6 appears only in Regular Pack + 1 Card openings (5.238% of packs). "
            "Shiny cards (shiny_rare/shiny_super_rare) are NOT in pack_sources.json — "
            "card 6 EV contribution is pending addition of shiny pool data."
        ),
    },
    "rare_pack_all_5_slots": {
        "illustration_rare":              0.47058,
        "super_rare":           0.45098,
        "immersive":           0.03921,
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

# ---------------------------------------------------------------------------
# A4 (Wisdom of Sea and Sky) slot_6 — user in-app verified from in-repo screenshots
# Card 6 appears in Regular Pack +1 Card openings (8.330% of packs).
# Uses standard rarity cards (NOT shiny like B-series).
# Verified from IMG_1722 2.PNG: ☆=12.900% (Magby), ◇◇◇=87.100% (Magby/Smoochum/Tyrogue).
# ---------------------------------------------------------------------------
_A4_SLOT_6 = {
    "illustration_rare":      0.12900,
    "rare": 0.87100,
    "note": (
        "Card 6 in Regular Pack +1 Card openings (8.330% of packs). "
        "Verified from user in-app screenshots stored in 'Offering Rates screenshots/' "
        "(IMG_1722 2.PNG, 2026-05-14). "
        "illustration_rare (☆) = 12.900% (Magby), rare (◇◇◇) = 87.100% "
        "(Magby/Smoochum/Tyrogue). Standard rarity cards — NOT shiny."
    ),
}

# ---------------------------------------------------------------------------
# A4 (Wisdom of Sea and Sky) full slot rates — user in-app verified 2026-05-14
# Branch: regular=91.620%, regular_plus_one=8.330%, rare=0.050%
# Matches Secluded Springs (A4a) branch probabilities exactly.
# Source: in-repo screenshots IMG_1692 2.PNG – IMG_1722 2.PNG
# ---------------------------------------------------------------------------
A4_WISDOM_SLOT_RATES = {
    "regular_pack_probability": 0.91620,
    "rare_pack_probability": 0.00050,
    "regular_pack_plus_one_probability": 0.08330,
    "slots_1_3": {"common": 1.0},
    "slot_4": _STANDARD_SLOT_4,
    "slot_5": _STANDARD_SLOT_5,
    "slot_6": _A4_SLOT_6,
    "rare_pack_all_5_slots": _STANDARD_RARE_PACK,
    "confidence": "user_in_app_verified",
    "source_name": "user_in_app_screenshots_offering_rates",
    "source_url": BULBAPEDIA_URLS["A4"],
    "source_accessed_at": "2026-05-14",
    "source_notes": (
        "Branch selection (regular_pack=91.620%, regular_pack_plus_one=8.330%, rare_pack=0.050%) "
        "and slot_6 (illustration_rare=12.900%, rare=87.100%) verified from in-repo Offering "
        "Rates screenshots (IMG_1692 2.PNG – IMG_1722 2.PNG, 'Offering Rates screenshots/' folder). "
        "Ho-Oh (A4) verified directly; Lugia (A4) shares the same expansion — identical rates inferred. "
        "Branch probabilities match Secluded Springs (A4a) exactly. "
        "Rare pack shows apparent uniform per-card distribution (~2.564% = 1/39 pool cards); "
        "standard 40/50/5/5 tier placeholder retained pending explicit rate confirmation. "
        "Screenshots stored in 'Offering Rates screenshots/' (gitignored — not committed to repo)."
    ),
    "confidence_note": (
        "user_in_app_verified: branch selection and slot_6 rates confirmed from PTCGP app screenshots "
        "stored in 'Offering Rates screenshots/'. "
        "Slot 4/5 distributions match third_party_verified standard rates. "
        "NOT Bulbapedia-corroborated (page was inaccessible during prior verification pass)."
    ),
}

# Pending verification warning — used for A4b only
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


def _remap_rarity_keys(obj):
    """Recursively normalize legacy symbol-tier rarity keys to the new vocabulary
    (e.g. two_diamond→uncommon, one_shiny→shiny_rare). Non-rarity keys pass through
    unchanged. Rebuilds dicts/lists rather than mutating, so shared constant dicts
    used as slot-rate templates are never modified in place."""
    if isinstance(obj, dict):
        return {(normalize_rarity(k) if isinstance(k, str) else k): _remap_rarity_keys(v)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_remap_rarity_keys(v) for v in obj]
    return obj


def compute_rarity_probabilities_from_pz(pack_name, set_code, pz_raw, pz_odds, ref_rarity) -> dict | None:
    """Exact expected copies of each rarity per pack, summed INDEPENDENTLY per pack from
    Pokémon Zone per-card drop chances (the same source build_pack_ev uses for EV).

    For the pack's PZ entry, each card's drop_chance is added to its rarity bucket (rarity
    from card_reference). Returns {rarity: expected_copies_per_pack} over RARITY_FIELDS, or
    None when the pack has no PZ data (caller falls back to the slot model)."""
    slug = resolve_pz_slug(pack_name, set_code, pz_raw)
    card_odds = pz_odds.get(slug) if slug else None
    if not card_odds:
        return None
    out = {r: 0.0 for r in RARITY_FIELDS}
    for (sc, num), drop_dec in card_odds.items():
        rar = ref_rarity.get((sc, num))  # canonical rarity for this coord
        if rar not in out:
            # Coord missing from card_reference (None) or an off-vocabulary value — never
            # silently drop the pull mass: bucket it into 'unknown' so a stale/partial
            # card_reference surfaces as a visible nonzero 'unknown' rather than understating.
            rar = "unknown"
        out[rar] += drop_dec
    return {r: round(v, 8) for r, v in out.items()}


def _slot_model_expected_per_pack(slot_rates: dict) -> dict:
    """FALLBACK only (when a pack has no PZ data): approximate expected copies of each
    rarity per pack from the inferred branch + per-slot model. Slots 1–3 are Common;
    slot_6 (Card 6) appears only in the regular_pack_plus_one branch.
      E[R] = P_reg·(3·s13 + s4 + s5) + P_plus·(3·s13 + s4 + s5 + s6) + P_rare·(5·rare)
    Note: the slot model has no shiny/SIR keys, so those tiers read 0 here — PZ data is
    required for exact shiny/SIR/crown rates."""
    s13  = slot_rates.get("slots_1_3") or {}
    s4   = slot_rates.get("slot_4") or {}
    s5   = slot_rates.get("slot_5") or {}
    s6   = slot_rates.get("slot_6") or {}
    rare = slot_rates.get("rare_pack_all_5_slots") or {}
    p_reg  = slot_rates.get("regular_pack_probability") or 0.0
    p_plus = slot_rates.get("regular_pack_plus_one_probability") or 0.0
    p_rare = slot_rates.get("rare_pack_probability") or 0.0

    out: dict[str, float] = {}
    for r in RARITY_FIELDS:
        if r == "ultra_rare":
            # Crown is stored under either 'ultra_rare' OR the 'crown_or_highest_rare'
            # alias (never both) — pick whichever is present; don't sum (avoids double-count).
            rare_r = float(rare.get("ultra_rare") or rare.get("crown_or_highest_rare") or 0.0)
        else:
            rare_r = float(rare.get(r, 0.0))
        base = 3.0 * float(s13.get(r, 0.0)) + float(s4.get(r, 0.0)) + float(s5.get(r, 0.0))
        e = (p_reg * base
             + p_plus * (base + float(s6.get(r, 0.0)))
             + p_rare * (5.0 * rare_r))
        out[r] = round(e, 8) if e else 0.0
    return out


def load_existing_rates(path: Path) -> dict:
    """Load per-pack rate data from existing model JSON. Returns {pack_name: data}."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARN: could not load existing model from {path}: {e}", file=sys.stderr)
        return {}
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

    if branch_type == "user_in_app_verified_a4":
        return ({**A4_WISDOM_SLOT_RATES}, "user_in_app_verified", "three_branch", None, True)

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


# branch_type -> (bulbapedia_match, bulbapedia_notes) annotation pair recorded in
# each pack's metadata. A pure lookup keyed by the same SET_CODE_BRANCH_CONFIG
# routing as get_branch_model; the default covers third_party_two_branch.
_BRANCH_ANNOTATIONS: dict[str, tuple[str, str]] = {
    "user_in_app_plus_bulbapedia": (
        "branch_selection_corroborated",
        "Bulbapedia confirms three-branch structure (94.711%/5.238%/0.050%). "
        "User in-app verified rates are used; Bulbapedia corroborates branch selection.",
    ),
    "user_in_app_verified_a4": (
        "in_app_verified_bulbapedia_inaccessible",
        "Branch selection (91.620%/8.330%/0.050%) and slot_6 verified from in-repo "
        "Offering Rates screenshots (IMG_1692–IMG_1722, 2026-05-14). "
        "Bulbapedia page was inaccessible during prior verification pass. "
        "Branch probabilities match Secluded Springs (A4a) exactly.",
    ),
    "bulbapedia_three_branch_standard": (
        "branch_verified",
        "Offering rates section confirmed three-branch model: "
        "regular_pack=94.711%, regular_pack_plus_one=5.238%, rare_pack=0.050%.",
    ),
    "bulbapedia_secluded_springs": (
        "branch_verified_special_case",
        "Offering rates section confirmed unique three-branch model: "
        "regular_pack=91.620%, regular_pack_plus_one=8.330%, rare_pack=0.050%. "
        "Branch percentages differ from standard B-series three-branch model.",
    ),
    "bulbapedia_mega_shine": (
        "branch_verified_special_case",
        "Offering rates section confirmed four-branch model: "
        "regular_pack=94.706%, regular_pack_plus_one=5.238%, rare_pack=0.050%, "
        "themed_rare_pack=0.005% (guarantees Mega Evolution ex).",
    ),
    "bulbapedia_two_branch": (
        "two_branch_confirmed",
        "Offering rates section confirmed two-branch model: "
        "regular_pack=99.950%, rare_pack=0.050%. "
        "No Regular Pack + 1 Card branch for this expansion.",
    ),
    "pending": (
        "truncated_pending",
        "Bulbapedia offering rates section was not accessible (page truncated) "
        "during the 2026-05-13 verification pass. Branch model unconfirmed.",
    ),
}
_DEFAULT_BRANCH_ANNOTATION: tuple[str, str] = (
    "truncated_pending",
    "Bulbapedia offering rates section was not fully accessible during "
    "the 2026-05-13 verification pass. Two-branch model is consistent with "
    "confirmed A-series Bulbapedia data (A1a/A2a/A3a/A3b all two-branch).",
)


# Promo packs (PROMO-A/-B) are bought with a different currency and scored separately by
# build_promo_pack_ev — they are excluded from the hourglass pull model entirely.
_PROMO_SET_CODES = PROMO_SET_CODES
# Packs kept in the model but NOT purchasable with Pack Hourglasses → flagged
# hourglass_purchasable=False so the recommendation report filters them out of the default
# rankings unless --include-limited. Deluxe Pack: ex (A4b) is a limited/event pack.
# (Compared upper-cased.)
_NON_HOURGLASS_PURCHASABLE = {A4B_SET_CODE}


# branch_type → (official_status, user_evidence_note, notes). One row per branch
# type so adding a new type can't forget a field. The third_party_two_branch
# default is NOT in this table — its note embeds the per-set Bulbapedia URL, so
# it stays dynamic in build_pack_records.
BRANCH_NOTES: dict[str, tuple[str, str | None, str]] = {
    "user_in_app_plus_bulbapedia": (
        "user_in_app_verified",
        "User manually read Pulsing Aura Offering Rates from the PTCGP app "
        "on 2026-05-13 and provided values in a ChatGPT conversation. "
        "Screenshots are NOT stored in this repository.",
        "Three-branch model: regular_pack (94.711%) + rare_pack (0.050%) "
        "+ regular_pack_plus_one (5.238%). "
        "Source: user-provided in-app Offering Rates (ChatGPT, not in repo). "
        "Bulbapedia corroborates branch percentages. "
        "Rare pack distribution corrected from in-app data: 47.058/45.098/3.921/3.921. "
        "Card 6 shiny rates: shiny_rare=68.180%, shiny_super_rare=31.820% (EV pending shiny pool data).",
    ),
    "user_in_app_verified_a4": (
        "user_in_app_verified",
        "User-captured in-app Offering Rates screenshots stored in repo: "
        "'Offering Rates screenshots/IMG_1692 2.PNG' – 'IMG_1722 2.PNG' (2026-05-14). "
        "Ho-Oh verified directly; Lugia shares the same expansion — rates inferred identical.",
        "Three-branch model verified from in-repo screenshots: "
        "regular_pack (91.620%) + regular_pack_plus_one (8.330%) + rare_pack (0.050%). "
        "Branch probabilities match Secluded Springs (A4a) exactly. "
        "Slot 6: illustration_rare=12.900% (☆), rare=87.100% (◇◇◇) — standard rarity, NOT shiny. "
        "Slot 4/5 distributions match third_party_verified standard rates. "
        "Rare pack distribution uses 40/50/5/5 placeholder — screenshots suggest "
        "apparent uniform per-card distribution (~2.564%), pending explicit confirmation.",
    ),
    "bulbapedia_three_branch_standard": (
        "not_verified",
        None,
        "Three-branch model from Bulbapedia: regular_pack (94.711%) "
        "+ regular_pack_plus_one (5.238%) + rare_pack (0.050%). "
        "Slot 4/5 rarity distributions from third_party_verified sources. "
        "Card 6 shiny rates unknown — EV contribution = 0. "
        "Rare pack distribution (40/50/5/5) from third_party_verified sources.",
    ),
    "bulbapedia_secluded_springs": (
        "not_verified",
        None,
        "Unique three-branch model from Bulbapedia: regular_pack (91.620%) "
        "+ regular_pack_plus_one (8.330%) + rare_pack (0.050%). "
        "Branch percentages differ from standard B-series model. "
        "EV impact: P_combined = 0.91620+0.08330 = 0.99950 ≈ same as two-branch EV.",
    ),
    "bulbapedia_mega_shine": (
        "not_verified",
        None,
        "Four-branch model from Bulbapedia: regular_pack (94.706%) "
        "+ regular_pack_plus_one (5.238%) + rare_pack (0.050%) "
        "+ themed_rare_pack (0.005%). "
        "themed_rare_pack guarantees Mega Evolution ex — EV not modeled (card pool unknown). "
        "Card 6 shiny rates unknown — EV contribution = 0.",
    ),
    "bulbapedia_two_branch": (
        "not_verified",
        None,
        "Two-branch model confirmed from Bulbapedia: regular_pack (99.950%) "
        "+ rare_pack (0.050%). No Regular Pack + 1 Card branch for this expansion.",
    ),
    "pending": (
        "pending",
        None,
        "Branch model unconfirmed — Bulbapedia offering rates section was not "
        "accessible during 2026-05-13 verification pass. "
        "Placeholder two-branch rates applied. Verify in-app.",
    ),
}


def build_pack_records(records: list, existing_rates: dict,
                       pz_raw: dict, pz_odds: dict, ref_rarity: dict) -> list:
    """
    Return list of pack records — one per distinct pullable named pack.
    Shared-pool cards are folded into each named pack's combined_pool.
    Branch model applied per set_code from SET_CODE_BRANCH_CONFIG.
    rarity_probabilities are computed per pack from PZ drop chances (exact), with the
    slot model as fallback.
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

        # Promo packs use a different currency (scored by build_promo_pack_ev) — keep them
        # out of the hourglass pull model so they don't appear in pack EV / rankings.
        if set_code.upper() in _PROMO_SET_CODES:
            continue

        named_packs = d["named"]
        if not named_packs:
            continue

        slot_rates, confidence, branch_model_str, stale_warning, is_multi_branch = \
            _build_slot_rates_for_set(set_code)
        # Normalize any legacy symbol-tier keys in the slot distributions to the new
        # vocabulary (deep-copied so shared constants are not mutated).
        slot_rates = _remap_rarity_keys(slot_rates)

        bulbapedia_url = BULBAPEDIA_URLS.get(set_code)
        branch_type = SET_CODE_BRANCH_CONFIG.get(set_code, "third_party_two_branch")

        bulbapedia_match, bulbapedia_notes_str = _BRANCH_ANNOTATIONS.get(
            branch_type, _DEFAULT_BRANCH_ANNOTATION)

        for pn in sorted(named_packs):
            pack_cards = named_packs[pn]
            pack_by_rarity = rarity_counts(pack_cards)
            pack_total = len(pack_cards)
            combined_by_rarity = add_rarity_dicts(pack_by_rarity, shared_by_rarity)
            combined_total = pack_total + shared_total

            existing = existing_rates.get(pn, {})
            # Exact expected copies of each rarity per pack, summed independently per pack
            # from Pokémon Zone per-card drop chances (the same source the EV model uses),
            # falling back to the inferred slot model only when a pack has no PZ data.
            rarity_probs = (compute_rarity_probabilities_from_pz(pn, set_code, pz_raw, pz_odds, ref_rarity)
                            or _slot_model_expected_per_pack(slot_rates))

            slot_model = {
                **STANDARD_SLOT_MODEL,
                "branch_model": branch_model_str,
            }

            if branch_type in BRANCH_NOTES:
                official_status, user_evidence_note, notes = BRANCH_NOTES[branch_type]
            else:
                # third_party_two_branch — dynamic: embeds the per-set Bulbapedia URL
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
                # Purchasable with Pack Hourglasses? Limited/event packs (Deluxe Pack: ex /
                # A4b) are not — the recommendation report filters them unless --include-limited.
                "hourglass_purchasable": set_code.upper() not in _NON_HOURGLASS_PURCHASABLE,
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

    if has_top:
        if has_mid or has_low:
            return "third_party_verified_with_in_app_anchor"
        if "user_in_app_verified_plus_bulbapedia" in confs or "user_in_app_verified" in confs:
            return "third_party_verified_with_in_app_anchor"
        return "bulbapedia_branch_verified"

    # No top-tier anchor: never claim one. And a mid tier mixed with low-tier
    # packs is not fully third-party verified — label by the weakest link.
    if has_mid and not has_low:
        return "third_party_verified"
    if has_mid or "inferred" in confs:
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
        f"A4 in-app verified model (v0.6.0, 2026-05-14). "
        f"user_in_app_verified: {n_inapp} packs (A4 Ho-Oh/Lugia, in-repo screenshots). "
        f"user_in_app_verified_plus_bulbapedia: {n_inapp_b} pack (Pulsing Aura B3, user in-app + Bulbapedia). "
        f"bulbapedia_branch_verified: {n_bpv} packs (branch selection from Bulbapedia offering rates). "
        f"third_party_verified: {n_tpv} packs (two-branch, A-series, Bulbapedia truncated but pattern consistent). "
        f"pending_verification: {n_pending} packs (A4b Deluxe Pack: ex — pack unavailable in app, 4 cards/pack). "
        f"rarity_probabilities = exact expected copies of each rarity per pack, summed per pack from Pokémon Zone per-card drop chances (slot-model fallback only when PZ data is absent). "
        f"A4 (Wisdom of Sea and Sky): three-branch 91.620%/8.330%/0.050%, slot_6 verified (illustration_rare=12.9%, rare=87.1%). "
        f"Secluded Springs (A4a): unique three-branch (91.620%/8.330%/0.050%). "
        f"Mega Shine (B2b): four-branch with themed_rare_pack=0.005%."
    )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_pull_probability_model.py",
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_version": "0.6.0",
            "source_status": source_status,
            "verified_source": (
                "ptcgp_in_app_offering_rates" if source_status == "verified" else None
            ),
            "user_in_app_verified_packs": (
                ["Ho-Oh (A4)", "Lugia (A4)", "Pulsing Aura (B3)"]
                if n_inapp + n_inapp_b > 0 else None
            ),
            "user_in_app_evidence_note": (
                "Ho-Oh and Lugia (A4): verified from in-repo screenshots in 'Offering Rates screenshots/' (2026-05-14). "
                "Pulsing Aura (B3): verified by user from in-app Offering Rates screen (ChatGPT conversation, NOT in repo, 2026-05-13)."
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
                ["Deluxe Pack: ex (A4b) — pack unavailable in app; Offering Rates inaccessible; 4 cards/pack"]
                if n_pending > 0 else None
            ),
            "confidence_note": (
                "third_party_verified_with_in_app_anchor: "
                "A4 (Ho-Oh/Lugia) user_in_app_verified from in-repo screenshots (2026-05-14). "
                "Pulsing Aura (B3) user_in_app_verified_plus_bulbapedia (2026-05-13). "
                "Most other packs branch-verified via Bulbapedia (2026-05-13). "
                "A-series packs confirmed two-branch (Bulbapedia + third-party sources). "
                "A4b pending — pack unavailable in app, Offering Rates inaccessible. "
                "Rarity distributions within slots still third_party_verified. "
                "NOT official in-app verified for any non-A4/non-B3 pack."
            ),
            "notes": meta_notes,
        },
        "probability_source_required": {
            "status": "IN_APP_VERIFIED_PARTIAL",
            "description": (
                "A4 (Ho-Oh/Lugia) branch and slot_6 verified from in-repo screenshots (2026-05-14). "
                "Pulsing Aura (B3) verified by user in-app (2026-05-13). "
                "Most other packs branch-verified from Bulbapedia. "
                "Slot rarity distributions still from third_party_verified sources. "
                "Aggregate rarity_probabilities are PZ-exact (expected copies/rarity/pack from Pokémon Zone drop chances)."
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
        "> `rarity_probabilities` = exact expected copies of each rarity per pack, summed per pack from Pokémon Zone per-card drop chances (slot-model fallback only when PZ data is absent).",
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
        f"| rarity_probabilities | **PZ-exact** — expected copies of each rarity per pack from Pokémon Zone drop chances |",
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
            f"| {cp.get('common', 0)} "
            f"| {cp.get('uncommon', 0)} "
            f"| {cp.get('rare', 0)} "
            f"| {cp.get('double_rare', 0)} "
            f"| {cp.get('illustration_rare', 0)} "
            f"| {cp.get('super_rare', 0)} "
            f"| {cp.get('immersive', 0)} |"
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
        "`rarity_probabilities[r]` = exact expected number of cards of rarity *r* opened per pack,",
        "summed independently per pack from Pokémon Zone per-card drop chances (`pz_pack_odds.json`)",
        "joined to `card_reference` rarity. A slot-model approximation is used only when a pack",
        "has no PZ data. Values are expected counts (e.g. common ~2.9/pack), not [0,1] probabilities.",
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
        rp = p.get("rarity_probabilities") or {}
        for field, val in rp.items():
            # Values are EXPECTED COPIES of each rarity per pack (e.g. common ~2.9), so they
            # are non-negative reals, not [0,1] probabilities.
            if val is not None and not (isinstance(val, (int, float)) and val >= 0):
                print(f"  ERROR: {p['pack_name']}.{field} = {val} (must be null or >= 0)")
                prob_errors += 1
    if prob_errors:
        errors += prob_errors
    else:
        print("  PASS  all rarity_probabilities values are null or >= 0 (expected copies/pack)")

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
        if all(v is None for v in (p.get("rarity_probabilities") or {}).values())
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

    # PZ per-card drop chances + card_reference rarity → exact per-rarity-per-pack probs.
    pz_raw, pz_odds = load_pz_pack_odds(PZ_PACK_ODDS_JSON)
    ref_rarity = {coord: normalize_rarity(rec.get("rarity"))
                  for coord, rec in card_reference_by_coord(CARD_REF_JSON).items()}
    print(f"  PZ packs: {len(pz_raw)} | card_reference coords: {len(ref_rarity)}")

    pack_records = build_pack_records(records, existing_rates, pz_raw, pz_odds, ref_rarity)
    print(f"  Pullable packs: {len(pack_records)}")
    n_pz_probs = sum(1 for p in pack_records
                     if resolve_pz_slug(p["pack_name"], p["set_code"], pz_raw) in pz_odds)
    print(f"  rarity_probabilities from PZ (exact): {n_pz_probs}/{len(pack_records)} packs (rest use slot-model fallback)")

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
    print(f"  rarity_probabilities:               PZ-exact (expected copies/rarity/pack)")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
