"""
Tests for assign_collection_coords.reconcile_pokemon_type — making card_reference
the authority for a Pokémon's energy type.

Regression: a same-name card spans printings with different types (Sableye A3:70
is Psychic, B3a:40 is Darkness). The assignment used to only backfill a *missing*
type, so an entry that carried a sibling's type stayed wrong and tripped the coord
validator's FATAL type cross-check.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from assign_collection_coords import reconcile_pokemon_type


def test_corrects_wrong_type_to_reference():
    entry = {"name": "Sableye", "card_type": "Pokemon", "type": "Darkness"}
    assert reconcile_pokemon_type(entry, "Psychic") == "corrected"
    assert entry["type"] == "Psychic"


def test_backfills_missing_type():
    entry = {"name": "Pikachu", "card_type": "Pokemon"}
    assert reconcile_pokemon_type(entry, "Lightning") == "backfilled"
    assert entry["type"] == "Lightning"


def test_noop_when_already_correct():
    entry = {"name": "Bulbasaur", "card_type": "Pokemon", "type": "Grass"}
    assert reconcile_pokemon_type(entry, "Grass") is None
    assert entry["type"] == "Grass"


def test_ignores_trainers():
    entry = {"name": "Potion", "card_type": "Trainer", "type": None}
    assert reconcile_pokemon_type(entry, "Psychic") is None
    assert entry.get("type") is None


def test_noop_without_reference_type():
    entry = {"name": "Mystery", "card_type": "Pokemon", "type": "Fire"}
    assert reconcile_pokemon_type(entry, None) is None
    assert entry["type"] == "Fire"  # never blanks an existing type
