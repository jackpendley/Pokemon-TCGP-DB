"""
Tests for trainer_power — the rule-text model that scores Trainer cards.

These assert the scorer's shape, its guardrails, and the *ordering* it produces
between cards whose relative usefulness isn't in dispute. They deliberately do
not pin exact scores for real cards: the weights are tunable, and freezing them
would make every future adjustment a test edit.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from trainer_power import trainer_features, trainer_power_score

EFFECTS = ROOT / "data" / "reference" / "card_trainer_effects.json"


# ── Shape ──────────────────────────────────────────────────────────────────

def test_empty_text_has_no_score():
    for empty in (None, "", "   "):
        assert trainer_power_score(empty) is None


def test_scores_stay_in_range():
    samples = [
        "Draw 2 cards.",
        "Put a random Basic Pokémon from your deck into your hand.",
        "Heal 90 damage from 1 of your Pokémon.",
        "During this turn, attacks used by your Pokémon do +200 damage.",
        "Nothing in particular happens.",
    ]
    for text in samples:
        score = trainer_power_score(text)
        assert score is not None
        assert 0 <= score <= 100


def test_plain_effect_is_above_the_floor():
    """Every Trainer does something, so nothing lands at zero."""
    assert trainer_power_score("Nothing in particular happens.") > 0


# ── Feature extraction ─────────────────────────────────────────────────────

def test_draw_scales_with_cards_drawn_then_caps():
    one = trainer_features("Draw 1 card.")["draw"]
    two = trainer_features("Draw 2 cards.")["draw"]
    assert two > one
    # Beyond 3 the benefit is capped, so a huge number can't run away.
    assert trainer_features("Draw 9 cards.")["draw"] == (
        trainer_features("Draw 3 cards.")["draw"]
    )


def test_damage_boost_is_capped():
    """Regression: '+80 damage to your Pawmot' outscored every generically
    useful Supporter before the cap existed."""
    big = trainer_features("attacks used by your Pokémon do +80 damage")
    mid = trainer_features("attacks used by your Pokémon do +30 damage")
    assert big["damage_boost"] == mid["damage_boost"]


def test_damage_boost_is_not_double_counted_as_direct_damage():
    """Regression: Giovanni's '+10 damage to your opponent's Active Pokémon'
    was scored as both a boost and direct damage."""
    f = trainer_features(
        "During this turn, attacks used by your Pokémon do +10 damage to "
        "your opponent's Active Pokémon."
    )
    assert "damage_boost" in f
    assert "direct_damage" not in f


def test_direct_damage_still_detected_when_it_is_not_a_boost():
    f = trainer_features("Do 20 damage to 1 of your opponent's Benched Pokémon.")
    assert "direct_damage" in f


def test_search_and_heal_and_switch_are_recognised():
    assert "search_deck" in trainer_features(
        "Put a random Basic Pokémon from your deck into your hand."
    )
    assert "heal" in trainer_features("Heal 50 damage from 1 of your Pokémon.")
    assert "force_switch" in trainer_features(
        "Switch out your opponent's Active Pokémon to the Bench."
    )


# ── Modifiers ──────────────────────────────────────────────────────────────

def test_coin_flip_discounts_an_effect():
    certain = trainer_power_score("Heal 60 damage from 1 of your Pokémon.")
    chancy = trainer_power_score(
        "Flip a coin. If heads, heal 60 damage from 1 of your Pokémon."
    )
    assert chancy < certain


def test_named_restriction_costs_more_than_a_type_restriction():
    generic = trainer_power_score(
        "During this turn, attacks used by your Pokémon do +30 damage."
    )
    typed = trainer_power_score(
        "During this turn, attacks used by your {W} Pokémon do +30 damage."
    )
    named = trainer_power_score(
        "During this turn, attacks used by your Pawmot do +30 damage."
    )
    assert generic > typed > named


def test_limitless_energy_symbol_spelling_is_recognised():
    """Limitless renders energy as '[ W ]' where TCGdex uses '{W}'."""
    braces = trainer_power_score(
        "During this turn, attacks used by your {F} Pokémon do +30 damage."
    )
    brackets = trainer_power_score(
        "During this turn, attacks used by your [ F ] Pokémon do +30 damage."
    )
    assert braces == brackets


# ── Against the real cached data ───────────────────────────────────────────

def test_every_cached_trainer_scores():
    """The cache only holds entries with rule text, so all of them must score."""
    if not EFFECTS.exists():
        return  # fetched artifact; absent in a clean checkout
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))
    assert effects, "trainer effects cache is empty"
    unscored = [k for k, v in effects.items() if trainer_power_score(v["effect"]) is None]
    assert not unscored, f"trainers with rule text but no score: {unscored[:5]}"


def test_no_artist_credit_leaked_into_rule_text():
    """Regression: the Limitless scrape swept up 'Illustrated by ...' because the
    marker class sits on the section element itself."""
    if not EFFECTS.exists():
        return
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))
    leaked = [k for k, v in effects.items() if "illustrated by" in v["effect"].lower()]
    assert not leaked, f"artist credit in rule text: {leaked[:5]}"


def test_staple_consistency_cards_outrank_deck_specific_payoffs():
    """Poké Ball works in every deck; Nemona only works alongside one Pokémon."""
    if not EFFECTS.exists():
        return
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))

    def score_of(name: str):
        for key, v in effects.items():
            if key.split("|", 1)[1] == name:
                return trainer_power_score(v["effect"])
        return None

    poke_ball = score_of("poké ball")
    nemona = score_of("nemona")
    if poke_ball is None or nemona is None:
        return  # card not in this data set
    assert poke_ball > nemona
