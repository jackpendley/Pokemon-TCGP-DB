"""
Guards card_reference.json completeness so the web Cards/Sets views never show a
typeless ("—") card and the deck rules engine is never left guessing:
  - every Pokémon has a pokemon_type, a stage and an hp,
  - every Trainer has a trainer_subtype (Item/Supporter/Stadium/Pokemon Tool),
  - every card is classified (no null card_category),
  - pokemon_type only ever holds a real energy type (never a trainer token).
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CARD_REF = ROOT / "data" / "reference" / "card_reference.json"

ENERGY_TYPES = {
    "Grass", "Fire", "Water", "Lightning", "Psychic", "Fighting",
    "Darkness", "Metal", "Dragon", "Colorless",
}
TRAINER_SUBTYPES = {"Item", "Supporter", "Stadium", "Pokemon Tool"}
# card_reference stores the spaceless TCGdex spelling (see _EXT_STAGE_TO_TCGDEX).
STAGES = {"Basic", "Stage1", "Stage2"}


@pytest.fixture(scope="module")
def records():
    assert CARD_REF.exists(), "card_reference.json missing — run scripts/build_card_reference.py"
    return json.loads(CARD_REF.read_text(encoding="utf-8"))["records"]


def _coord(r):
    return f"{r['set_code']}/{r['card_number']} {r['name']}"


def test_every_card_classified(records):
    bad = [_coord(r) for r in records if r.get("card_category") not in ("Pokemon", "Trainer")]
    assert not bad, f"{len(bad)} cards with no Pokemon/Trainer category: {bad[:10]}"


def test_every_pokemon_has_type(records):
    bad = [_coord(r) for r in records
           if r.get("card_category") == "Pokemon" and not r.get("pokemon_type")]
    assert not bad, f"{len(bad)} Pokémon missing a type: {bad[:10]}"


def test_pokemon_type_is_energy_type(records):
    bad = [_coord(r) for r in records
           if r.get("pokemon_type") and r["pokemon_type"] not in ENERGY_TYPES]
    assert not bad, f"{len(bad)} cards with a non-energy pokemon_type: {bad[:10]}"


def test_every_trainer_has_subtype(records):
    bad = [_coord(r) for r in records
           if r.get("card_category") == "Trainer" and not r.get("trainer_subtype")]
    assert not bad, f"{len(bad)} Trainers missing a subtype: {bad[:10]}"


def test_trainer_subtype_vocabulary(records):
    bad = [(_coord(r), r.get("trainer_subtype")) for r in records
           if r.get("trainer_subtype") and r["trainer_subtype"] not in TRAINER_SUBTYPES]
    assert not bad, f"unexpected trainer_subtype values: {bad[:10]}"


def test_every_pokemon_has_a_stage(records):
    """The deck builder's "at least 1 Basic" rule can only be checked when every
    Pokémon has a stage. 190 didn't (B3b 96, PROMO-B 74, PROMO-A 17, A4b 3), so the
    rule degraded to an "unverifiable-basic" warning for any deck containing one.
    """
    bad = [_coord(r) for r in records
           if r.get("card_category") == "Pokemon" and not r.get("stage")]
    assert not bad, f"{len(bad)} Pokémon missing a stage: {bad[:10]}"


def test_stage_vocabulary(records):
    bad = [(_coord(r), r.get("stage")) for r in records
           if r.get("stage") and r["stage"] not in STAGES]
    assert not bad, f"unexpected stage values: {bad[:10]}"


def test_every_pokemon_has_hp(records):
    """HP feeds the power-score model, which skipped any Pokémon without it."""
    bad = [_coord(r) for r in records
           if r.get("card_category") == "Pokemon" and not r.get("hp")]
    assert not bad, f"{len(bad)} Pokémon missing HP: {bad[:10]}"


def test_no_card_shows_dash(records):
    """A card renders '—' in the UI only if it has neither a type nor a subtype."""
    bad = [_coord(r) for r in records
           if not r.get("pokemon_type") and not r.get("trainer_subtype")]
    assert not bad, f"{len(bad)} cards would render '—': {bad[:10]}"
