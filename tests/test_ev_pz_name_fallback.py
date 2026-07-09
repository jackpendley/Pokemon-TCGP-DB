"""
Regression lock for the PZ name-fallback in pack EV.

The fallback assigns PZ drop rates to pool printings whose (set_code,
card_number) has no direct PZ match, keyed by normalized name. Each unmatched
PZ rate must be consumed at most once per pack: before this lock, a single PZ
rate was handed to *every* same-name pool printing, double-counting that
card's pull mass in new_card_ev / pack rankings (observed on real data for
Lugia ex, Mew ex, Dialga ex).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pack_ev as bev

LUGIA_KEY = bev._norm_name("Lugia ex")

POOL = [
    {"card_name": "Lugia ex", "rarity": "double_rare", "set_code": "A2", "card_number": 100},
    {"card_name": "Lugia ex", "rarity": "special_art_rare", "set_code": "A2", "card_number": 201},
    {"card_name": "Pidgey", "rarity": "common", "set_code": "A2", "card_number": 1},
]

PACK_RECORD = {
    "pack_name": "Fallback Pack",
    "expansion": "Test Expansion",
    "set_code": "A2",
    "slot_rates": None,
    "card_pool": {"combined_by_rarity": {"common": 1, "double_rare": 1, "special_art_rare": 1}},
}


def _record(pz_name_odds):
    # Pidgey matches by coord; both Lugia printings miss and hit the name fallback.
    pz_card_odds = {("A2", 1): 0.02}
    return bev.compute_pack_ev_record(
        PACK_RECORD, POOL, collection={}, deck_targets={},
        pz_card_odds=pz_card_odds, pz_name_odds=pz_name_odds,
        collection_by_card={},
    )


def test_single_rate_consumed_once_not_per_printing():
    record = _record({LUGIA_KEY: [0.005]})
    lugia = [c for c in record["top_ev_cards"] if c["name"] == "Lugia ex"]
    assert len(lugia) == 1, "one PZ rate must credit exactly one printing"
    assert lugia[0]["pull_prob"] == 0.005
    # The unmatched second printing is treated like any other card absent
    # from PZ odds: non-pullable, not silently double-counted, so new_card_ev
    # carries the 0.005 mass exactly once.
    pidgey = next(c for c in record["top_ev_cards"] if c["name"] == "Pidgey")
    expected = 0.005 * lugia[0]["value"] + 0.02 * pidgey["value"]
    assert abs(record["new_card_ev"] - expected) < 1e-9


def test_multiple_rates_distribute_without_duplication():
    record = _record({LUGIA_KEY: sorted([0.004, 0.001], reverse=True)})
    lugia = [c for c in record["top_ev_cards"] if c["name"] == "Lugia ex"]
    assert len(lugia) == 2
    # Total PZ mass is preserved: each rate used exactly once.
    assert sorted(c["pull_prob"] for c in lugia) == [0.001, 0.004]


def test_excess_rates_assign_lowest_first():
    # More PZ rates than pool printings: the single printing must get the
    # LOWEST rate (old "lower rate wins" conservatism), not the highest.
    pool = [POOL[0], POOL[2]]  # one Lugia printing + Pidgey
    record = bev.compute_pack_ev_record(
        PACK_RECORD, pool, collection={}, deck_targets={},
        pz_card_odds={("A2", 1): 0.02},
        pz_name_odds={LUGIA_KEY: sorted([0.02, 0.0004], reverse=True)},
        collection_by_card={},
    )
    lugia = [c for c in record["top_ev_cards"] if c["name"] == "Lugia ex"]
    assert len(lugia) == 1
    assert lugia[0]["pull_prob"] == 0.0004


def test_build_collects_name_rates_as_list():
    pz_raw = {
        "test-pack": {
            "cards": [
                {"name": "Lugia ex", "set_code": "A2", "card_number": 999, "drop_chance_pct": 0.4},
                {"name": "Lugia ex", "set_code": "A2", "card_number": 998, "drop_chance_pct": 0.1},
            ]
        }
    }
    pool_keys = {("A2", 100), ("A2", 201)}
    odds = bev.build_pz_name_odds(pz_raw["test-pack"], pool_keys)
    assert odds == {LUGIA_KEY: [0.004, 0.001]}  # descending; pop() hands out lowest first
