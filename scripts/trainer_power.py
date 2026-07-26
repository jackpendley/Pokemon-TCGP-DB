#!/usr/bin/env python3
"""
Utility scoring for Trainer cards, from their rule text.

Why this is a separate model: a Pokémon's power comes from HP and attack damage,
which are numbers on the card. A Trainer has neither — everything it is worth is
in its effect text. So build_card_power_score.py scored all 287 Trainers as null
until this existed.

**What this measures.** The breadth and magnitude of what a Trainer does: how
many cards it draws, how much damage it adds, how much it heals, whether it
tutors, accelerates energy or forces a switch. It is a *utility* heuristic read
off the text, not a competitive tier list — no meta data, play rates or deck
context feed it. A card whose value is situational (Misty's coin flips) will
score below its real standing in a deck built around it.

For that reason a Trainer score is emitted with `score_kind: "trainer"` and must
not be ranked against a Pokémon's `score_kind: "pokemon"`: the two scales measure
different things and share only their 0–100 range.

Model shape mirrors the Pokémon one — explicit tunable constants, a linear blend,
capped at 100:

    raw   = BASE + Σ(feature weights)
    score = min(raw × coin-flip mult × narrowness mult, 100)
"""

import re

# Every Trainer does something; this keeps a plain effect off the floor.
BASE = 12.0

# Feature weights. Magnitudes below are per unit where the text states a number
# (cards drawn, damage, HP), otherwise flat for the effect being present.
W_DRAW_PER_CARD = 9.0        # card advantage compounds; 2 cards is a strong turn
W_SEARCH_DECK = 20.0         # tutoring is consistency, the scarcest resource
W_ENERGY_ACCEL = 22.0        # energy is the game's hard tempo limit
W_DAMAGE_BOOST_PER_PT = 0.8  # +10 damage often converts a 2HKO into a OHKO
# Boosts above this are always gated on one named Pokémon, and the marginal
# value of overkill damage falls off fast — without a cap, "+80 damage to your
# Pawmot" outscored every generically useful Supporter in the game.
DAMAGE_BOOST_CAP = 30
W_DIRECT_DAMAGE_PER_PT = 0.55
W_HEAL_PER_PT = 0.35         # healing trades at a discount to damage
W_FORCE_SWITCH = 20.0        # dragging up a benched target is a tempo swing
W_SELF_SWITCH = 9.0
W_RETREAT_REDUCTION = 9.0
W_HP_BOOST_PER_PT = 0.6      # tools; HP is durable across turns
W_DISRUPTION = 15.0          # opponent discards / shuffles / reveals
W_DISCARD_RECOVERY = 13.0
W_EVOLVE_ACCEL = 16.0

# Effects gated on a coin flip are worth roughly their expected value.
COIN_FLIP_MULT = 0.75
# Restriction tiers. A card that only works with one named Pokémon is far
# narrower than one that works with a whole energy type, so they can't share a
# multiplier.
NARROW_NAMED_MULT = 0.55
NARROW_TYPE_MULT = 0.85

_RE_DRAW = re.compile(r"draw\s+(\d+|a)\s+card", re.I)
_RE_SEARCH = re.compile(
    r"(from your deck|look at the top \d+ cards of your deck)", re.I
)
_RE_ENERGY_ACCEL = re.compile(
    r"(take|attach)\s+.{0,60}?energy\s+.{0,40}?(from your energy zone|and attach)", re.I
)
_RE_DAMAGE_BOOST = re.compile(r"do\s*\+\s*(\d+)\s+damage", re.I)
# The negative lookbehind keeps "do +10 damage to your opponent" out of this —
# that is a damage *boost*, and was being counted twice.
_RE_DIRECT_DAMAGE = re.compile(
    r"(?<!\+)\b(\d+)\s+damage\s+to\s+(?:1 of\s+)?your opponent", re.I
)
_RE_HEAL = re.compile(r"heal\s+(\d+)\s+damage", re.I)
_RE_FORCE_SWITCH = re.compile(r"switch\s+out\s+your\s+opponent", re.I)
_RE_SELF_SWITCH = re.compile(r"switch\s+(in|out)\s+your\b(?!.*opponent)", re.I)
_RE_RETREAT = re.compile(r"retreat cost", re.I)
_RE_HP_BOOST = re.compile(r"gets\s*\+\s*(\d+)\s*HP", re.I)
_RE_DISRUPTION = re.compile(
    r"your opponent(?:'s)?\b[^.]{0,60}\b(shuffles?|discards?|reveals?)", re.I
)
_RE_DISCARD_RECOVERY = re.compile(r"(from|in)\s+your\s+discard pile", re.I)
_RE_EVOLVE = re.compile(r"\bevolve\b", re.I)

_RE_COIN = re.compile(r"flip a coin", re.I)
# Energy-type restriction. Sources render the symbol as "{W}" (TCGdex) or
# "[ W ]" (Limitless), so both spellings have to be recognised.
_RE_NARROW_TYPE = re.compile(r"(\{[A-Z]\}|\[\s*[A-Z]\s*\])\s*Pok[eé]mon")
# Named-Pokémon restriction ("your Pawmot", "your Ninetales, Rapidash, or
# Magmar"). The lookahead excludes the generic board nouns that follow "your".
_RE_NARROW_NAMED = re.compile(
    r"\byour\s+(?!Pok[eé]mon|Bench|Active|Energy|Deck|Hand|Discard|Opponent)"
    r"[A-Z][A-Za-z'\u2019\-]+"
)


def _first_int(pattern: re.Pattern, text: str, default: int = 0) -> int:
    m = pattern.search(text)
    if not m:
        return default
    raw = m.group(1)
    if raw.lower() == "a":
        return 1
    return int(raw)


def trainer_features(effect: str) -> dict[str, float]:
    """Weighted contribution of each recognised effect. Exposed for testing and
    so a score can be explained rather than just asserted."""
    text = effect or ""
    f: dict[str, float] = {}

    drawn = _first_int(_RE_DRAW, text)
    if drawn:
        f["draw"] = W_DRAW_PER_CARD * min(drawn, 3)
    if _RE_SEARCH.search(text):
        f["search_deck"] = W_SEARCH_DECK
    if _RE_ENERGY_ACCEL.search(text):
        f["energy_accel"] = W_ENERGY_ACCEL

    boost = _first_int(_RE_DAMAGE_BOOST, text)
    if boost:
        f["damage_boost"] = W_DAMAGE_BOOST_PER_PT * min(boost, DAMAGE_BOOST_CAP)
    direct = _first_int(_RE_DIRECT_DAMAGE, text)
    if direct:
        f["direct_damage"] = W_DIRECT_DAMAGE_PER_PT * direct
    healed = _first_int(_RE_HEAL, text)
    if healed:
        f["heal"] = W_HEAL_PER_PT * healed
    hp = _first_int(_RE_HP_BOOST, text)
    if hp:
        f["hp_boost"] = W_HP_BOOST_PER_PT * hp

    if _RE_FORCE_SWITCH.search(text):
        f["force_switch"] = W_FORCE_SWITCH
    elif _RE_SELF_SWITCH.search(text):
        f["self_switch"] = W_SELF_SWITCH
    if _RE_RETREAT.search(text):
        f["retreat_reduction"] = W_RETREAT_REDUCTION
    if _RE_DISRUPTION.search(text):
        f["disruption"] = W_DISRUPTION
    if _RE_DISCARD_RECOVERY.search(text):
        f["discard_recovery"] = W_DISCARD_RECOVERY
    if _RE_EVOLVE.search(text):
        f["evolve_accel"] = W_EVOLVE_ACCEL
    return f


def trainer_power_score(effect: str) -> float | None:
    """0–100 utility score for a Trainer, or None when there's no rule text."""
    if not (effect or "").strip():
        return None
    features = trainer_features(effect)
    raw = BASE + sum(features.values())
    if _RE_COIN.search(effect):
        raw *= COIN_FLIP_MULT
    if _RE_NARROW_NAMED.search(effect):
        raw *= NARROW_NAMED_MULT
    elif _RE_NARROW_TYPE.search(effect):
        raw *= NARROW_TYPE_MULT
    return round(min(raw, 100.0), 1)
