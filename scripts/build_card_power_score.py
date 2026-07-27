#!/usr/bin/env python3
"""
Build a per-card power/value score from HP + best *effective* attack + ability.

Reads card_reference.json (every printing) and card_combat_stats.json (fetched by
fetch_combat_stats.py, keyed "SET|name", carrying per-attack cost/damage/drawbacks).
Emits data/reference/card_power_scores.json keyed "SET:num" so the web layer can
rank cards and show the strongest pulls.

A card can only use one attack per turn, so it's represented by its single best
*effective* attack, not the sum. Effectiveness reflects TCG Pocket tempo:
    ramp_adj = damage - RAMP_PER_ENERGY * (cost - 2)   # energy = one-time ramp/tempo
    if the attack discards its own energy:  × DISCARD_PENALTY   # not repeatable
    if the attack damages itself:           − SELF_DMG_WEIGHT × self_damage_amount

Scoring (0–100, higher = stronger card):
    hp_score  = min(HP / 210, 1)                 # ex/Mega HP tops out ~210
    dmg_score = min(effective_damage / 200, 1)   # best effective attack
    ability   = +0.12 when the card has an ability
    retreat   = +RETREAT_BONUS when retreat cost ≤ 1
    power     = round(min(0.47*hp + 0.41*dmg + ability + retreat, 1) * 100, 1)

Pokémon in sets with no combat data get HP-proxied damage and are flagged
`estimated`.

Trainers have no HP or attacks, so they are scored from their rule text by a
separate model (trainer_power.py, fed by fetch_trainer_effects.py). Every entry
carries `score_kind` — "pokemon" or "trainer" — because the two scales measure
different things and must not be ranked against each other. Trainer scores
occupy a lower band by construction; they are deliberately *not* normalised to
the observed maximum, which would rescale every existing card each time a new
set landed.

Deliberately independent of the EV model — it never touches pack_ev.json.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trainer_power import trainer_power_score

ROOT = Path(__file__).resolve().parent.parent
CARD_REF = ROOT / "data" / "reference" / "card_reference.json"
COMBAT = ROOT / "data" / "reference" / "card_combat_stats.json"
TRAINER_EFFECTS = ROOT / "data" / "reference" / "card_trainer_effects.json"
OUT = ROOT / "data" / "reference" / "card_power_scores.json"

# Tunable model constants (see module docstring).
RAMP_PER_ENERGY = 20.0   # effective damage traded per energy vs a 2-cost baseline
DISCARD_PENALTY = 0.6    # multiplier for one-shot (energy-discard) attacks
SELF_DMG_WEIGHT = 0.5    # effective damage lost per point of self-damage
RETREAT_BONUS = 0.03     # blend bonus for a retreat cost ≤ 1


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def best_effective_attack(attacks) -> float:
    """Highest tempo-adjusted damage among a card's attacks (0 if none)."""
    best = 0.0
    for a in attacks or []:
        eff = (a.get("damage") or 0) - RAMP_PER_ENERGY * ((a.get("cost") or 0) - 2)
        if a.get("discards_energy"):
            eff *= DISCARD_PENALTY
        if a.get("self_damage"):
            eff -= SELF_DMG_WEIGHT * (a.get("self_damage_amount") or 0)
        best = max(best, eff)
    return max(0.0, best)


def power_score(hp, effective_damage, has_ability: bool, has_attack_data: bool,
                retreat=None):
    """Pure scorer. Returns a 0–100 float, or None when HP is unknown."""
    if not hp:
        return None
    hp_score = min(hp / 210, 1.0)
    if has_attack_data:
        dmg_score = min((effective_damage or 0) / 200, 1.0)
        ability = 0.12 if has_ability else 0.0
    else:
        # No attack data (uncovered set): proxy damage from HP; ability unknown.
        dmg_score = min((hp * 0.55) / 200, 1.0)
        ability = 0.0
    retreat_bonus = RETREAT_BONUS if (retreat is not None and retreat <= 1) else 0.0
    total = 0.47 * hp_score + 0.41 * dmg_score + ability + retreat_bonus
    return round(min(total, 1.0) * 100, 1)


def main() -> int:
    ref = json.loads(CARD_REF.read_text(encoding="utf-8"))["records"]
    combat = json.loads(COMBAT.read_text(encoding="utf-8")) if COMBAT.exists() else {}
    effects = (
        json.loads(TRAINER_EFFECTS.read_text(encoding="utf-8"))
        if TRAINER_EFFECTS.exists()
        else {}
    )

    scores: dict = {}
    scored = estimated = skipped = trainers = 0
    for r in ref:
        key = f"{r['set_code']}|{_norm(r['name'])}"

        if r.get("card_category") == "Trainer":
            effect = (effects.get(key) or {}).get("effect")
            ts = trainer_power_score(effect) if effect else None
            if ts is None:
                skipped += 1
                continue
            scores[f"{r['set_code']}:{r['card_number']}"] = {
                "power_score": ts,
                "score_kind": "trainer",
                "trainer_subtype": r.get("trainer_subtype"),
            }
            scored += 1
            trainers += 1
            continue

        if r.get("card_category") != "Pokemon":
            skipped += 1
            continue
        stats = combat.get(key)
        hp = (stats or {}).get("hp") or r.get("hp")
        has_attack = stats is not None
        eff = best_effective_attack((stats or {}).get("attacks")) if has_attack else 0.0
        ps = power_score(
            hp,
            eff,
            bool((stats or {}).get("ability_count")),
            has_attack,
            (stats or {}).get("retreat"),
        )
        if ps is None:
            skipped += 1
            continue
        scores[f"{r['set_code']}:{r['card_number']}"] = {
            "power_score": ps,
            "score_kind": "pokemon",
            "hp": hp,
            "effective_damage": round(eff, 1) if has_attack else None,
            "has_ability": bool((stats or {}).get("ability_count")),
            "estimated": not has_attack,
        }
        scored += 1
        if not has_attack:
            estimated += 1

    OUT.write_text(
        json.dumps(
            {"generated_at": date.today().isoformat(), "scores": scores},
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(
        f"  Power scores: {scored} cards "
        f"({scored - trainers} Pokémon, {estimated} estimated from HP; "
        f"{trainers} Trainers), {skipped} skipped (no HP / no rule text)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
