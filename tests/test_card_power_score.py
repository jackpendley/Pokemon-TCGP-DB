"""
Tests for build_card_power_score.power_score — the HP + attack + ability model.
Kept separate from the EV model; these only assert the scorer's shape/ordering.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_card_power_score import power_score


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
