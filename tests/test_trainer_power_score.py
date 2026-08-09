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

from trainer_power import (
    _RE_NARROW_NAMED,
    _RE_NARROW_TYPE,
    trainer_boosts,
    trainer_features,
    trainer_power_score,
)

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


# ── Boost extraction ───────────────────────────────────────────────────────

def test_generic_trainers_boost_nothing_in_particular():
    """Emptiness is how "works in every deck" is represented."""
    for text in (
        "Draw 2 cards.",
        "Put 1 random Basic Pokémon from your deck into your hand.",
        "During this turn, attacks used by your Pokémon do +10 damage.",
        "",
    ):
        assert trainer_boosts(text) == {"names": [], "types": []}


def test_single_named_pokemon_is_extracted():
    assert trainer_boosts(
        "During this turn, attacks used by your Pawmot do +80 damage to your "
        "opponent's Active Pokémon ex."
    ) == {"names": ["Pawmot"], "types": []}


def test_every_name_in_a_list_is_extracted():
    """Regression: only the first name in a list used to be seen."""
    assert trainer_boosts(
        "During this turn, attacks used by your Ninetales, Rapidash, or Magmar "
        "do +30 damage to your opponent's Active Pokémon."
    )["names"] == ["Ninetales", "Rapidash", "Magmar"]
    assert trainer_boosts(
        "attacks used by your Snorlax, Heracross, and Staraptor cost 2 less"
    )["names"] == ["Snorlax", "Heracross", "Staraptor"]
    assert trainer_boosts("Put your Muk or Weezing in the Active Spot into your hand.")[
        "names"
    ] == ["Muk", "Weezing"]


def test_multi_word_and_ex_names_survive_intact():
    assert trainer_boosts(
        "attacks used by your Alolan Golem, Vikavolt, or Togedemaru do +30 damage"
    )["names"] == ["Alolan Golem", "Vikavolt", "Togedemaru"]
    assert trainer_boosts("Put your Mew ex in the Active Spot into your hand.")[
        "names"
    ] == ["Mew ex"]


def test_a_name_does_not_run_past_the_end_of_its_sentence():
    """Regression: "…to your Luxray. Attach 2 {L} Energy…" yielded
    "Luxray. Attach" while the name regex allowed periods mid-name."""
    assert trainer_boosts(
        "Choose 1 of your Electivire or Luxray. Attach 2 {L} Energy from your "
        "discard pile to that Pokémon."
    )["names"] == ["Electivire", "Luxray"]


def test_board_zones_and_card_traits_are_not_names():
    """"your Basic Pokémon" and "your Ultra Beasts" restrict the card, but they
    name no card, so there is nothing to recommend them alongside."""
    for text in (
        "Choose 1 of your Basic Pokémon in play.",
        "Choose 1 of your Ultra Beasts.",
        "Heal 60 damage from 1 of your Stage 2 Pokémon.",
        "Shuffle 1 of your Future Pokémon in play into your deck.",
        "Move all {L} Energy from your Benched Pokémon to your Active Pokémon.",
    ):
        assert trainer_boosts(text)["names"] == [], text


def test_energy_types_are_extracted_in_both_spellings():
    assert trainer_boosts("Heal 50 damage from 1 of your {G} Pokémon.")["types"] == [
        "Grass"
    ]
    assert trainer_boosts("Heal 50 damage from 1 of your [ G ] Pokémon.")["types"] == [
        "Grass"
    ]


def test_a_fossil_does_not_boost_colorless():
    """A fossil *becomes* a Colorless Pokémon; it doesn't help one."""
    assert trainer_boosts(
        "Play this card as if it were a 40-HP Basic {C} Pokémon. At any time "
        "during your turn, you may discard this card from play."
    ) == {"names": [], "types": []}


def test_a_boosting_card_always_took_the_narrowness_discount():
    """The two readings of narrowness must stay consistent in one direction: the
    scoring signal is broader (it also fires on trait groups), so anything the
    extractor claims must already have been discounted as narrow. If this fails,
    a card gained a boost relationship without paying for it."""
    if not EFFECTS.exists():
        return
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))
    for key, v in effects.items():
        boosts = trainer_boosts(v["effect"])
        if not (boosts["names"] or boosts["types"]):
            continue
        assert _RE_NARROW_NAMED.search(v["effect"]) or _RE_NARROW_TYPE.search(
            v["effect"]
        ), key


def test_real_cards_extract_the_expected_boosts():
    if not EFFECTS.exists():
        return
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))
    expected = {
        "A1|erika": {"names": [], "types": ["Grass"]},
        "B2a|nemona": {"names": ["Pawmot"], "types": []},
        "A1|blaine": {"names": ["Ninetales", "Rapidash", "Magmar"], "types": []},
        "A1|helix fossil": {"names": [], "types": []},
    }
    for key, want in expected.items():
        if key not in effects:
            continue  # card not in this data set
        assert trainer_boosts(effects[key]["effect"]) == want, key


def test_no_extracted_name_is_a_sentence_fragment():
    """A name with a period or a lowercase-initial word in it is a parse leak."""
    if not EFFECTS.exists():
        return
    effects = json.loads(EFFECTS.read_text(encoding="utf-8"))
    for key, v in effects.items():
        for name in trainer_boosts(v["effect"])["names"]:
            assert "." not in name or name.startswith("Mr."), f"{key}: {name!r}"
            for word in name.split()[1:]:
                assert word == "ex" or word[0].isupper(), f"{key}: {name!r}"


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
