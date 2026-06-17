"""Shared setup + helpers for the new-card-addition test suite.

Loads sync_collection and the real reference data once, and exposes the
match/build helpers the split test_new_card_*.py files import. Underscore
name so pytest does not collect it as a test module.
"""

#!/usr/bin/env python3
"""
Simulation: new card additions from all packs.

Tests that every category of card the sync pipeline will encounter
is handled correctly when the card doesn't yet exist in the collection.

Scenarios:
  1.  Simple new card — pack_sources match, not in collection
  2.  Multi-set new card — same card from two different sets, dedup to one entry
  3.  New alt-art (illustration_rare rarity) — base already owned, alt art is new
  4.  New super_rare alt art — same as above, super_rare rarity is_alt path
  5.  New immersive — another star-tier new card
  6.  Both variants new — neither base nor alt yet owned; PZ returns both
  7.  A1 numbering mismatch, card NOT owned — must use PZ raw_name, not pack_sources
  8.  A1 numbering mismatch, card OWNED — existing behavior preserved
  9.  New PROMO-A card (override)
 10.  New PROMO-B card (override)
 11.  New card not in pack_sources or collection (raw-name fallback)
 12.  New Trainer card — direct normalized-name match (not in pack_sources)
 13.  Multi-variant: base owned, PZ returns base + alt art simultaneously
 14.  New card whose name collides with known card after normalization
 15.  Cross-set parallel: card owned, PZ returns it from three set codes
 16.  All known A1/A4 numbering mismatches (not owned)
 17.  Smoke test: first unowned card from every set code
 18.  All super_rare/immersive → is_alt=True
 19.  Nidoran♀ + Nidoran♂ both new — dedup must produce 2 entries, not 1
 20.  build_auto_entry blank card_category — hp/stage/type populated from ext_ref
 21.  Nidoran♀ + Nidoran♂ both owned — exact-name shortcut routes each correctly
 22.  Mismatch slot with alt-art rarity, card OWNED → MATCHED (not NEW_CARD)
 23.  Mismatch slot with alt-art rarity, card NOT owned → NEW_CARD with correct name
 24.  All illustration_rare + crown rarities → alt art routing (extends scenario 18)
 25.  Comprehensive: every unowned non-mismatch card across all packs → NEW_CARD
 26.  Phase 4b alt-art tagging — build_auto_entry + name guard tags all alt rarities
 27.  Phase 4c Case A simulation — alt art added marks base entry stale
 28.  Phase 4c Case B — fixed threshold fires at 3rd consecutive miss (not 4th)
 29.  Phase 4e — stale entry names excluded from write_review_queue call
 30.  Phase 4c Case A regression — Nidoran♀ alt-art does NOT mark Nidoran♂ base stale
 31.  Phase 4c Case A — pre-existing MATCHED alt-art triggers Case A for missing base

Usage:
    python3 -m pytest tests/test_new_card_additions.py
    python3 tests/test_new_card_additions.py
"""

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load sync_collection without running main()
# ---------------------------------------------------------------------------

spec = importlib.util.spec_from_file_location(
    "sync_collection", ROOT / "scripts" / "sync_collection.py"
)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

PZCard             = sc.PZCard
MatchResult        = sc.MatchResult
match_pz_cards     = sc.match_pz_cards
build_auto_entry   = sc.build_auto_entry
_normalize         = sc._normalize
_PROMO_A_OVERRIDES = sc._PROMO_A_OVERRIDES
_PROMO_B_OVERRIDES = sc._PROMO_B_OVERRIDES
# Use the production alt-rarity vocabulary so the test tracks the real constant
# (a change to RARE_PLUS_RARITIES propagates here instead of silently diverging).
_ALT_RARITIES = sc.RARE_PLUS_RARITIES

# ---------------------------------------------------------------------------
# Load real reference data — via the production loaders, so the tests exercise
# the exact parsing the sync pipeline uses (no private copies to drift).
# ---------------------------------------------------------------------------

PACK_SOURCES = sc.load_pack_sources()
EXT_REF      = sc.load_ext_ref()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "  ✓"
FAIL = "  ✗"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"{PASS}  {name}")
    else:
        msg = f"{name}" + (f": {detail}" if detail else "")
        print(f"{FAIL}  {msg}")
        _failures.append(msg)
        # Raise so pytest registers a real failure (script mode exits 1 via main).
        assert cond, msg


def pz(raw_name, count=1, set_code=None, card_number=None) -> PZCard:
    return PZCard(set_code=set_code, card_number=card_number,
                  raw_name=raw_name, count=count)


def entry(name, count=1, hp=None, variant=None, card_type="Pokemon") -> dict:
    e = {"name": name, "count": count, "card_type": card_type, "is_ex": False}
    if hp is not None:
        e["hp"] = hp
    if variant is not None:
        e["variant"] = variant
    return e


def run(pz_cards, collection, label=""):
    """Convenience: run match_pz_cards with real reference data."""
    return match_pz_cards(pz_cards, collection, PACK_SOURCES, EXT_REF)
