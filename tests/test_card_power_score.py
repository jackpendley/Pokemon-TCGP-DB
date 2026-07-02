"""
Tests for build_card_power_score.power_score — the HP + attack + ability model.
Kept separate from the EV model; these only assert the scorer's shape/ordering.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_card_power_score import power_score, best_effective_attack


def _atk(damage, cost, **kw):
    return {"damage": damage, "cost": cost,
            "discards_energy": kw.get("discards_energy", False),
            "self_damage": kw.get("self_damage", False),
            "self_damage_amount": kw.get("self_damage_amount", 0)}


def test_none_hp_returns_none():
    assert power_score(None, 100, True, True) is None
    assert power_score(0, 100, True, True) is None


def test_scores_are_in_range():
    for hp in (30, 90, 150, 210, 400):
        for dmg in (0, 60, 150, 300):
            s = power_score(hp, dmg, False, True)
            assert 0.0 <= s <= 100.0


def test_more_hp_scores_higher():
    assert power_score(160, 60, False, True) > power_score(60, 60, False, True)


def test_more_damage_scores_higher():
    assert power_score(90, 120, False, True) > power_score(90, 40, False, True)


def test_ability_adds_bonus():
    assert power_score(90, 60, True, True) > power_score(90, 60, False, True)


def test_strong_ex_beats_weak_common():
    ex = power_score(190, 100, False, True)
    common = power_score(50, 20, False, True)
    assert ex > common


def test_estimated_uses_hp_proxy_when_no_attack_data():
    # No attack data → damage proxied from HP, so a high-HP card still scores.
    est = power_score(150, 0, False, False)
    assert est > power_score(60, 0, False, False)
    # The same HP scores higher with real attack data than with the HP proxy.
    assert power_score(150, 150, False, True) > power_score(150, 0, False, False)


def test_scores_capped_at_100_with_bonuses():
    # HP + big attack + ability + low-retreat bonus must not exceed 100.
    assert power_score(210, 300, True, True, retreat=0) <= 100.0


def test_low_retreat_adds_bonus():
    assert power_score(90, 60, False, True, retreat=0) > power_score(90, 60, False, True, retreat=3)


# ── best_effective_attack: one attack per turn, tempo-adjusted ──────────────
def test_picks_higher_effective_not_higher_raw():
    # A cheap 60 (2 energy) beats a costly 90 (4 energy): 60 vs 90-40=50.
    assert best_effective_attack([_atk(60, 2), _atk(90, 4)]) == 60


def test_cheaper_attack_scores_higher_for_same_damage():
    cheap = power_score(90, best_effective_attack([_atk(80, 1)]), False, True)
    costly = power_score(90, best_effective_attack([_atk(80, 3)]), False, True)
    assert cheap > costly


def test_energy_discard_attack_demoted_below_repeatable():
    repeatable = best_effective_attack([_atk(100, 3)])
    one_shot = best_effective_attack([_atk(100, 3, discards_energy=True)])
    assert one_shot < repeatable


def test_self_damage_lowers_effective():
    clean = best_effective_attack([_atk(80, 2)])
    hurts = best_effective_attack([_atk(80, 2, self_damage=True, self_damage_amount=30)])
    assert hurts < clean


def test_effective_never_negative():
    assert best_effective_attack([_atk(0, 4)]) == 0.0
    assert best_effective_attack([]) == 0.0
