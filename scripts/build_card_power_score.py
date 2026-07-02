#!/usr/bin/env python3
"""
Build a per-card power/value score from HP + attack damage + ability presence.

Reads card_reference.json (every printing) and card_combat_stats.json (fetched by
fetch_combat_stats.py, keyed by "SET|name"). Emits data/reference/card_power_scores.json
keyed by "SET:num" so the web layer can rank cards and show the strongest pulls.

Scoring (0–100, higher = stronger card):
    hp_score  = min(HP / 210, 1)                 # ex/Mega HP tops out ~210
    dmg_score = min(max_attack_damage / 200, 1)  # strongest single attack
    ability   = +0.12 when the card has an ability
    power     = round((0.47*hp + 0.41*dmg + ability) * 100, 1)

Pokémon in TCGdex-uncovered sets have HP (from card_reference) but no attack data,
so damage is proxied from HP and the entry is flagged `estimated`. Trainers (no HP)
get no score. This is deliberately independent of the EV model — it never touches
pack_ev.json.
"""

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARD_REF = ROOT / "data" / "reference" / "card_reference.json"
COMBAT = ROOT / "data" / "reference" / "card_combat_stats.json"
OUT = ROOT / "data" / "reference" / "card_power_scores.json"


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def power_score(hp, max_damage, has_ability: bool, has_attack_data: bool):
    """Pure scorer. Returns a 0–100 float, or None when HP is unknown."""
    if not hp:
        return None
    hp_score = min(hp / 210, 1.0)
    if has_attack_data:
        dmg_score = min((max_damage or 0) / 200, 1.0)
        ability = 0.12 if has_ability else 0.0
    else:
        # No attack data (uncovered set): proxy damage from HP; ability unknown.
        dmg_score = min((hp * 0.55) / 200, 1.0)
        ability = 0.0
    return round((0.47 * hp_score + 0.41 * dmg_score + ability) * 100, 1)


def main() -> int:
    ref = json.loads(CARD_REF.read_text(encoding="utf-8"))["records"]
    combat = json.loads(COMBAT.read_text(encoding="utf-8")) if COMBAT.exists() else {}

    scores: dict = {}
    scored = estimated = skipped = 0
    for r in ref:
        if r.get("card_category") != "Pokemon":
            skipped += 1
            continue
        key = f"{r['set_code']}|{_norm(r['name'])}"
        stats = combat.get(key)
        hp = (stats or {}).get("hp") or r.get("hp")
        has_attack = stats is not None
        ps = power_score(
            hp,
            (stats or {}).get("max_damage", 0),
            bool((stats or {}).get("ability_count")),
            has_attack,
        )
        if ps is None:
            skipped += 1
            continue
        scores[f"{r['set_code']}:{r['card_number']}"] = {
            "power_score": ps,
            "hp": hp,
            "max_damage": (stats or {}).get("max_damage"),
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
        f"  Power scores: {scored} cards ({estimated} estimated from HP), "
        f"{skipped} skipped (trainers / no HP)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
