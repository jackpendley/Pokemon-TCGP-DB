"""
Golden integration lock for compute_pack_ev_record.

test_ev.py covers the EV *primitives* (rarity ordering, the 10x formula in
isolation, the unified-score helper) and test_output_contract.py pins the field
*shape*. Neither pins how compute_pack_ev_record *wires the primitives together*
end-to-end: the pool aggregation, the within-batch 10x accumulation, the
confidence haircut, cost efficiency, and rounding.

This module fills that gap with a frozen synthetic pack. Expected values are
recomputed independently from the public primitives + constants, so any refactor
that changes the integration math (not just a primitive) fails loudly. It uses a
fixed fixture rather than the live pack_ev.json, so it does NOT drift when the
collection changes on each sync.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pack_ev as bev
from _collection_io import HOURGLASS_PER_PACK, RARE_PLUS_RARITIES


# ---------------------------------------------------------------------------
# Frozen fixture: one pack, four cards spanning the interesting paths.
#   1. common  owned=2  → capped (value 0, excluded from card list)
#   2. common  owned=0  → multi-slot rarity (p_pull > 1.0 → back-calc 10x path)
#   3. double_rare owned=0 → rare-pack contribution + rarity bonus
#   4. ultra_rare owned=1 → copy_ev path (no 10x), rare-pack-only pull
# ---------------------------------------------------------------------------

POOL = [
    {"card_name": "Comm A", "rarity": "common", "set_code": "A1", "card_number": 1},
    {"card_name": "Comm B", "rarity": "common", "set_code": "A1", "card_number": 2},
    {"card_name": "DR C", "rarity": "double_rare", "set_code": "A1", "card_number": 3},
    {"card_name": "UR D", "rarity": "ultra_rare", "set_code": "A1", "card_number": 4},
]

COMBINED_BY_RARITY = {"common": 2, "double_rare": 1, "ultra_rare": 1}

SLOT_RATES = {
    "branch_model": "two_branch",
    "regular_pack_probability": 0.9995,
    "rare_pack_probability": 0.0005,
    "slot_4": {"double_rare": 0.05, "ultra_rare": 0.0},
    "slot_5": {"double_rare": 0.03, "ultra_rare": 0.0},
    "rare_pack_all_5_slots": {"double_rare": 0.02, "ultra_rare": 0.005},
    "confidence": "inferred_unverified",  # not in _VERIFIED_SLOT_CONFIDENCES → 0.85 haircut
}

# Ownership by (set_code_upper, card_number).
COLLECTION_BY_CARD = {("A1", 1): 2, ("A1", 4): 1}

PACK_RECORD = {
    "pack_name": "Golden Pack",
    "expansion": "Test Expansion",
    "set_code": "A1",
    "slot_rates": SLOT_RATES,
    "card_pool": {"combined_by_rarity": COMBINED_BY_RARITY},
}


@pytest.fixture(scope="module")
def record():
    return bev.compute_pack_ev_record(
        PACK_RECORD, POOL, collection={}, deck_targets={},
        pz_card_odds=None, pz_name_odds=None,
        collection_by_card=COLLECTION_BY_CARD,
    )


# --- Independently recomputed expectations (mirror _accumulate_pool_ev) ------

def _expected():
    """Recompute the aggregate from the primitives, written out longhand so the
    integration wiring is verified rather than re-asserted from itself."""
    p_commB = bev.card_pull_ev("common", COMBINED_BY_RARITY, SLOT_RATES)
    p_drC = bev.card_pull_ev("double_rare", COMBINED_BY_RARITY, SLOT_RATES)
    p_urD = bev.card_pull_ev("ultra_rare", COMBINED_BY_RARITY, SLOT_RATES)

    v_commB = bev.value_of_next_copy(0, "common", {}, "comm b")
    v_drC = bev.value_of_next_copy(0, "double_rare", {}, "dr c")
    v_urD = bev.value_of_next_copy(1, "ultra_rare", {}, "ur d")  # owned=1 → copy

    # new_card_ev: owned==0 cards only (Comm B, DR C).
    new_card_ev = p_commB * v_commB + p_drC * v_drC
    # copy_ev: owned==1 card (UR D).
    copy_ev = p_urD * v_urD

    # 10x within-batch accumulation.
    def p10(p):
        if p > 1.0:  # multi-slot common back-calc
            per_slot = p / 3.0
            at_least_one = 1.0 - (1.0 - min(per_slot, 1.0)) ** 3
        else:
            at_least_one = min(p, 1.0)
        return 1.0 - (1.0 - at_least_one) ** 10

    new_card_ev_10x = (
        p10(p_commB) * (1.0 + bev.RARITY_BONUS["common"])
        + p10(p_drC) * (1.0 + bev.RARITY_BONUS["double_rare"])
    )

    # confidence weight: no PZ, unverified slot rates → inferred haircut.
    cw = bev.INFERRED_CONFIDENCE_WEIGHT
    unified = (
        new_card_ev_10x * bev.UNIFIED_WEIGHTS["new_card_10x"]
        + copy_ev * bev.UNIFIED_WEIGHTS["copy"]
    ) * cw  # no deck_targets → deck term omitted

    return {
        "new_card_ev": new_card_ev,
        "new_card_ev_10x": new_card_ev_10x,
        "copy_ev": copy_ev,
        "confidence_weight": cw,
        "unified_score": unified,
        "p_commB": p_commB,
        "p_drC": p_drC,
        "p_urD": p_urD,
    }


# ---------------------------------------------------------------------------
# Pool counters
# ---------------------------------------------------------------------------

def test_pool_counts(record):
    assert record["cards_in_pool"] == 4
    assert record["owned_in_pool"] == 2          # Comm A + UR D
    assert record["missing_in_pool"] == 2        # Comm B + DR C
    assert record["base_cards_in_pool"] == 3     # 2 commons + 1 double_rare
    assert record["base_owned_in_pool"] == 1     # Comm A only


def test_rare_plus_count_matches_constant(record):
    # DR C (double_rare, owned=0) is the only missing card; counts iff double_rare is rare+.
    expected = 1 if "double_rare" in RARE_PLUS_RARITIES else 0
    assert record["missing_rare_plus"] == expected


# ---------------------------------------------------------------------------
# Aggregate EV scores (the integration lock)
# ---------------------------------------------------------------------------

def test_aggregate_scores_match_independent_recompute(record):
    exp = _expected()
    assert record["new_card_ev"] == pytest.approx(exp["new_card_ev"], abs=1e-6)
    assert record["new_card_ev_10x"] == pytest.approx(exp["new_card_ev_10x"], abs=1e-6)
    assert record["copy_ev"] == pytest.approx(exp["copy_ev"], abs=1e-6)
    assert record["confidence_weight"] == pytest.approx(exp["confidence_weight"])
    assert record["unified_score"] == pytest.approx(exp["unified_score"], abs=1e-6)


def test_confidence_adjusted_and_dr_ratio(record):
    exp = _expected()
    pack_total = exp["new_card_ev"] + exp["copy_ev"]
    assert record["pack_total_ev"] == pytest.approx(pack_total, abs=1e-6)
    assert record["confidence_adjusted_ev"] == pytest.approx(
        pack_total * exp["confidence_weight"], abs=1e-6
    )
    dr = record["new_card_ev_10x"] / (record["new_card_ev"] * 10)
    assert record["ev_diminishing_returns_ratio"] == pytest.approx(round(dr, 4), abs=1e-4)


def test_cost_efficiency(record):
    exp = _expected()
    c1 = HOURGLASS_PER_PACK / max(exp["new_card_ev"], 0.001)
    c10 = (HOURGLASS_PER_PACK * 10) / max(exp["new_card_ev_10x"], 0.001)
    assert record["cost_per_unique_card_1x"] == pytest.approx(round(c1, 2), abs=0.01)
    assert record["cost_per_unique_card_10x"] == pytest.approx(round(c10, 2), abs=0.01)


# ---------------------------------------------------------------------------
# top_ev_cards content + ordering
# ---------------------------------------------------------------------------

def test_top_ev_cards_excludes_capped_and_orders_by_contribution(record):
    cards = record["top_ev_cards"]
    names = [c["name"] for c in cards]
    assert "Comm A" not in names  # capped (owned=2, value 0) → excluded
    assert set(names) == {"Comm B", "DR C", "UR D"}
    contribs = [c["ev_contribution"] for c in cards]
    assert contribs == sorted(contribs, reverse=True)
    assert len(cards) <= bev.TOP_N_CARDS


def test_source_status_inferred(record):
    assert record["source_status"] == "inferred"
    assert record["slot_rates_confidence"] == "inferred_unverified"
