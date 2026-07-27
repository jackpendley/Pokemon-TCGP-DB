"""
Tests for assign_collection_coords.reconcile_hp — making card_reference the
authority for a Pokémon entry's HP.

Regression: 33 owned entries carried a *sibling printing's* HP (the collection's
Caterpie read 50, which is A1/5's HP, while its coord B3b/1 is a 40-HP card —
confirmed against the card art). The coords were right; the HP was stale.

This matters beyond tidiness because HP is pick_candidate's primary filter, so a
wrong HP steers coord assignment to the wrong printing. It was inert while ext_ref
had no HP for B3b/PROMO-B — nothing to filter on — and became a hazard as soon as
those sets gained it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from assign_collection_coords import reconcile_hp


def test_corrects_a_sibling_printings_hp():
    # The real Caterpie case: 50 is A1/5's HP, B3b/1 is a 40-HP card.
    entry = {"name": "Caterpie", "card_type": "Pokemon", "hp": 50}
    assert reconcile_hp(entry, 40) == "corrected"
    assert entry["hp"] == 40


def test_backfills_missing_hp():
    entry = {"name": "Pikachu", "card_type": "Pokemon"}
    assert reconcile_hp(entry, 60) == "backfilled"
    assert entry["hp"] == 60


def test_noop_when_already_correct():
    entry = {"name": "Bulbasaur", "card_type": "Pokemon", "hp": 70}
    assert reconcile_hp(entry, 70) is None
    assert entry["hp"] == 70


def test_ignores_trainers():
    entry = {"name": "Potion", "card_type": "Trainer", "hp": None}
    assert reconcile_hp(entry, 60) is None
    assert entry.get("hp") is None


def test_noop_without_reference_hp():
    entry = {"name": "Mystery", "card_type": "Pokemon", "hp": 90}
    assert reconcile_hp(entry, None) is None
    assert entry["hp"] == 90  # never blanks an existing HP
