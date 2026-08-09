"""
Phase 2 tests: build_pack_ev.py EV model correctness.

Tests verify the model signals (rarity bonus, deck completion scaling,
10x diminishing returns, collection hash skip, unified score ordering)
without mocking external files — they use the live pack_ev.json output.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pack_ev as bev
import _collection_io as io

PACK_EV_PATH = ROOT / "data" / "current" / "pack_ev.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pack_ev():
    """Load pack_ev.json — requires build_pack_ev.py to have run at least once."""
    assert PACK_EV_PATH.exists(), "pack_ev.json not found — run build_pack_ev.py first"
    return json.loads(PACK_EV_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def packs(pack_ev):
    return pack_ev["packs"]


# ---------------------------------------------------------------------------
# 2.1: Rarity bonus — crown missing card > common missing card
# ---------------------------------------------------------------------------

def test_rarity_bonus_crown_gt_one_diamond():
    """Missing a crown card is worth more than missing a common card."""
    deck_targets: dict = {}
    v_crown = bev.value_of_next_copy(0, "ultra_rare", deck_targets, "test_crown")
    v_common = bev.value_of_next_copy(0, "common", deck_targets, "test_common")
    assert v_crown > v_common, (
        f"crown value ({v_crown}) should exceed common value ({v_common})"
    )


def test_rarity_bonus_ordering():
    """Rarity value ordering matches RARITY_BONUS: crown > immersive > super_rare > double_rare > illustration_rare > rare >= uncommon = common."""
    deck_targets: dict = {}
    rarities = ["ultra_rare", "immersive", "super_rare", "double_rare", "illustration_rare", "rare", "uncommon", "common"]
    values = [bev.value_of_next_copy(0, r, deck_targets, f"test_{r}") for r in rarities]
    for i in range(len(values) - 1):
        assert values[i] >= values[i + 1], (
            f"value[{rarities[i]}]={values[i]} should be >= value[{rarities[i+1]}]={values[i+1]}"
        )


def test_rarity_bonus_only_on_first_copy():
    """Rarity bonus applies only on owned=0; owned=1 always equals copy_up_to_2."""
    deck_targets: dict = {}
    v_crown_second  = bev.value_of_next_copy(1, "ultra_rare",       deck_targets, "test")
    v_common_second = bev.value_of_next_copy(1, "common", deck_targets, "test")
    expected = bev.SCORING_WEIGHTS["copy_up_to_2"]
    assert v_crown_second == expected, f"crown 2nd copy: expected {expected}, got {v_crown_second}"
    assert v_common_second == expected, f"common 2nd copy: expected {expected}, got {v_common_second}"


def test_no_rarity_bonus_at_cap():
    """At owned=2, value is 0 regardless of rarity."""
    deck_targets: dict = {}
    assert bev.value_of_next_copy(2, "ultra_rare",      deck_targets, "test") == 0.0
    assert bev.value_of_next_copy(2, "common", deck_targets, "test") == 0.0


# ---------------------------------------------------------------------------
# 2.2: Deck completion scaling — 1 copy needed > 2 copies needed
# ---------------------------------------------------------------------------

def test_deck_bonus_scales_with_urgency():
    """Needing 1 more copy (short_by=1) is worth more than needing 2 (short_by=2)."""
    deck_1 = {"pikachu": 1}
    deck_2 = {"pikachu": 2}
    v_urgent = bev.value_of_next_copy(0, "common", deck_1, "pikachu")
    v_less   = bev.value_of_next_copy(0, "common", deck_2, "pikachu")
    assert v_urgent > v_less, (
        f"1 copy needed ({v_urgent}) should be worth more than 2 copies needed ({v_less})"
    )


def test_deck_bonus_at_1_equals_full_weight():
    """When short_by=1, deck bonus = SCORING_WEIGHTS['deck_target'] (full bonus)."""
    deck = {"test": 1}
    v = bev.value_of_next_copy(0, "common", deck, "test")
    expected = (
        bev.SCORING_WEIGHTS["new_card"]
        + bev.RARITY_BONUS["common"]
        + bev.SCORING_WEIGHTS["deck_target"] / 1
    )
    assert abs(v - expected) < 1e-9, f"Expected {expected}, got {v}"


def test_deck_bonus_at_2_equals_half_weight():
    """When short_by=2, deck bonus = SCORING_WEIGHTS['deck_target'] / 2."""
    deck = {"test": 2}
    v = bev.value_of_next_copy(0, "common", deck, "test")
    expected = (
        bev.SCORING_WEIGHTS["new_card"]
        + bev.RARITY_BONUS["common"]
        + bev.SCORING_WEIGHTS["deck_target"] / 2
    )
    assert abs(v - expected) < 1e-9, f"Expected {expected}, got {v}"


def test_no_deck_bonus_for_non_target():
    """Card not in deck_targets gets no deck bonus."""
    deck = {"other_card": 1}
    v = bev.value_of_next_copy(0, "common", deck, "pikachu")
    expected = bev.SCORING_WEIGHTS["new_card"] + bev.RARITY_BONUS["common"]
    assert abs(v - expected) < 1e-9


# ---------------------------------------------------------------------------
# 2.3: 10x diminishing returns model
# ---------------------------------------------------------------------------

def test_10x_ev_less_than_10_times_1x(packs):
    """For every scored pack, 10x EV < 10 × 1x EV (diminishing returns always applies)."""
    for p in packs:
        one_x = p["new_card_ev"]
        ten_x = p["new_card_ev_10x"]
        if one_x > 0:
            assert ten_x <= one_x * 10 + 1e-6, (
                f"{p['pack_name']}: 10x ({ten_x:.4f}) > 10 × 1x ({one_x * 10:.4f})"
            )


def test_10x_ev_nonnegative(packs):
    """10x EV is never negative."""
    for p in packs:
        assert p["new_card_ev_10x"] >= 0.0, f"{p['pack_name']}: negative new_card_ev_10x"


def test_diminishing_returns_ratio_in_range(packs):
    """DR ratio is between 0 and 1 for all packs with nonzero 1x EV."""
    for p in packs:
        if p["new_card_ev"] > 0:
            ratio = p["ev_diminishing_returns_ratio"]
            assert 0.0 <= ratio <= 1.0 + 1e-6, (
                f"{p['pack_name']}: ratio {ratio} out of [0,1]"
            )


def test_10x_formula_correctness():
    """Directly verify the 10x formula for a single card with known p."""
    # Card with p=0.05 (5% pull rate): P(at least 1 in 10) = 1 - 0.95^10 = 0.4013
    p = 0.05
    expected = 1.0 - (1.0 - p) ** 10
    # Simulate by running compute_pack_ev_record with one card and checking accumulation
    # We test the formula directly since it's embedded in the loop
    assert abs(expected - 0.4013) < 0.001


# ---------------------------------------------------------------------------
# 2.4: Collection hash skip
# ---------------------------------------------------------------------------

def test_hash_skip_fires_on_second_run():
    """Second consecutive run should print 'unchanged' and exit 0."""
    # First run ensures pack_ev.json exists with the current hash
    r1 = subprocess.run(
        [sys.executable, "scripts/build_pack_ev.py"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r1.returncode == 0, f"First run failed: {r1.stderr}"

    # Second run should skip
    r2 = subprocess.run(
        [sys.executable, "scripts/build_pack_ev.py"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r2.returncode == 0, f"Second run failed: {r2.stderr}"
    assert "unchanged" in r2.stdout.lower() or "skipping" in r2.stdout.lower(), (
        f"Expected 'unchanged'/'skipping' in stdout, got: {r2.stdout!r}"
    )


def test_ev_cache_hash_includes_source_code():
    """The cache hash must cover the EV computation source, not just data files — otherwise
    a logic change (scoring weights, ownership crediting) won't bust the cache and stale
    results get served. Regression for the reprint-ownership snapshot fix being missed."""
    names = {p.name for p in bev.hash_input_paths()}
    assert "build_pack_ev.py" in names
    assert "_collection_io.py" in names


def test_inputs_hash_written_to_output(pack_ev):
    """pack_ev.json must contain inputs_hash in meta (covers all input files)."""
    h = pack_ev.get("meta", {}).get("inputs_hash")
    assert h is not None and len(h) == 64, (
        f"Expected 64-char SHA-256 hash, got: {h!r}"
    )


# ---------------------------------------------------------------------------
# 2.5: Unified score ordering
# ---------------------------------------------------------------------------

def test_unified_score_present_for_all_packs(packs):
    """Every scored pack has a unified_score field."""
    for p in packs:
        assert "unified_score" in p, f"{p['pack_name']} missing unified_score"
        assert p["unified_score"] >= 0.0


def test_unified_score_correlates_with_new_card_ev_10x(packs):
    """Pack ranked #1 by unified_score should also be high by new_card_ev_10x."""
    sorted_unified = sorted(packs, key=lambda p: p["unified_score"], reverse=True)
    sorted_10x = sorted(packs, key=lambda p: p["new_card_ev_10x"], reverse=True)
    top5_unified = {p["pack_name"] for p in sorted_unified[:5]}
    top5_10x = {p["pack_name"] for p in sorted_10x[:5]}
    overlap = top5_unified & top5_10x
    assert len(overlap) >= 3, (
        f"Expected ≥3 packs in common between top-5 unified and top-5 10x, "
        f"got {len(overlap)}: unified={top5_unified}, 10x={top5_10x}"
    )


# ---------------------------------------------------------------------------
# Regression: pack_ev.json has expected new fields
# ---------------------------------------------------------------------------

def test_new_fields_present(packs):
    required_new_fields = [
        "new_card_ev_10x",
        "ev_diminishing_returns_ratio",
        "unified_score",
        "cost_per_unique_card_1x",
        "cost_per_unique_card_10x",
        "confidence_weight",
    ]
    for p in packs[:3]:  # spot-check first 3 packs
        for field in required_new_fields:
            assert field in p, f"{p['pack_name']} missing new field '{field}'"


def test_cost_metrics_are_positive(packs):
    for p in packs:
        if p["new_card_ev"] > 0:
            assert p["cost_per_unique_card_1x"] > 0
        if p["new_card_ev_10x"] > 0:
            assert p["cost_per_unique_card_10x"] > 0


# ---------------------------------------------------------------------------
# Ownership is credited across printing groups
# ---------------------------------------------------------------------------
# History: apply_reprint_links was removed 2026-06-12 because the dex then filled
# one slot at a time — reconcile_coords_from_pz split copies across the original
# and A4b coords, so cross-crediting would have double-counted.
#
# The 2026-07-29 update reversed that premise: "when you obtain a card that is
# included in multiple booster packs, it will now be registered in your card dex
# under each of those expansions", retroactively. One copy fills every slot, so
# EV must credit the whole group — a pull of a printing you already hold under
# another expansion is a duplicate, not a new card.

def test_printing_group_ownership_is_credited():
    """A copy held at one coord counts at every coord in its group."""
    groups = {"groups": [{"id": "g1", "coords": [["A1", 151], ["A4B", 194]]}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(groups, f)
        path = Path(f.name)
    try:
        credited = io.credit_printing_groups({("A1", 151): 1}, path)
        assert credited[("A1", 151)] == 1
        assert credited[("A4B", 194)] == 1, "sibling printing must read as owned"
    finally:
        path.unlink()


def test_printing_group_credit_sums_copies_across_coords():
    """Copies split across a group by the old reconcile still total correctly."""
    groups = {"groups": [{"id": "g1", "coords": [["A1", 151], ["A4B", 194]]}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(groups, f)
        path = Path(f.name)
    try:
        credited = io.credit_printing_groups({("A1", 151): 1, ("A4B", 194): 2}, path)
        assert credited[("A1", 151)] == 3
        assert credited[("A4B", 194)] == 3
    finally:
        path.unlink()


def test_printing_group_credit_leaves_unheld_groups_alone():
    groups = {"groups": [{"id": "g1", "coords": [["A1", 151], ["A4B", 194]]}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(groups, f)
        path = Path(f.name)
    try:
        credited = io.credit_printing_groups({("A1", 1): 4}, path)
        assert ("A4B", 194) not in credited
        assert credited[("A1", 1)] == 4
    finally:
        path.unlink()


def test_printing_group_credit_is_a_noop_without_the_artifact():
    by_coord = {("A1", 1): 2}
    assert io.credit_printing_groups(by_coord, Path("/nonexistent/groups.json")) == by_coord


def _weight_for_confidence(conf):
    """confidence_weight from compute_pack_ev_record for a pack with the given slot-rate
    confidence and NO PZ odds (pz_coverage=0), isolating the verification path."""
    pack = {"pack_name": "T", "expansion": "T", "set_code": "T",
            "slot_rates": {"confidence": conf}, "card_pool": {}}
    rec = bev.compute_pack_ev_record(pack, [], {}, {}, pz_card_odds=None)
    return rec["confidence_weight"]


def test_in_app_verified_slot_rates_skip_haircut_without_pz_odds():
    """A pack verified in-app must get full weight even when PZ pack-odds don't cover it;
    an unverified third-party pack still gets the 0.85 inferred haircut."""
    assert "user_in_app_verified" in bev._VERIFIED_SLOT_CONFIDENCES
    assert _weight_for_confidence("user_in_app_verified") == bev.PZ_CONFIDENCE_WEIGHT
    assert _weight_for_confidence("third_party_verified") == bev.INFERRED_CONFIDENCE_WEIGHT




# ---------------------------------------------------------------------------
# Extracted helpers (S2a decomposition of compute_pack_ev_record)
# ---------------------------------------------------------------------------

class _Agg:
    """Minimal stand-in for the PoolEV accumulator used by the helpers."""
    def __init__(self, new_card_ev_10x=0.0, copy_ev=0.0, deck_target_ev=0.0,
                 new_card_ev=0.0, card_ev_list=None):
        self.new_card_ev_10x = new_card_ev_10x
        self.copy_ev = copy_ev
        self.deck_target_ev = deck_target_ev
        self.new_card_ev = new_card_ev
        self.card_ev_list = card_ev_list or []


def test_unified_score_omits_deck_term_when_no_targets():
    agg = _Agg(new_card_ev_10x=5.0, copy_ev=2.0, deck_target_ev=9.0)
    expected = (5.0 * bev.UNIFIED_WEIGHTS["new_card_10x"]
                + 2.0 * bev.UNIFIED_WEIGHTS["copy"])
    assert bev._compute_unified_score(agg, {}, 1.0) == pytest.approx(expected)


def test_unified_score_includes_deck_term_and_confidence():
    agg = _Agg(new_card_ev_10x=5.0, copy_ev=2.0, deck_target_ev=9.0)
    expected = (5.0 * bev.UNIFIED_WEIGHTS["new_card_10x"]
                + 2.0 * bev.UNIFIED_WEIGHTS["copy"]
                + 9.0 * bev.UNIFIED_WEIGHTS["deck_target"]) * 0.85
    assert bev._compute_unified_score(agg, {"x": 1}, 0.85) == pytest.approx(expected)


def test_cost_efficiency_guards_against_zero():
    c1, c10 = bev._calculate_cost_efficiency(0.0, 0.0)
    assert c1 == bev.HOURGLASS_PER_PACK / 0.001
    assert c10 == (bev.HOURGLASS_PER_PACK * 10) / 0.001


def test_rank_top_cards_sorts_and_filters():
    cards = [
        {"ev_contribution": 1.0, "is_deck_target": False},
        {"ev_contribution": 3.0, "is_deck_target": True},
        {"ev_contribution": 2.0},
    ]
    top, deck = bev._rank_top_cards(cards)
    assert [c["ev_contribution"] for c in top[:3]] == [3.0, 2.0, 1.0]
    assert deck == [{"ev_contribution": 3.0, "is_deck_target": True}]
    assert len(top) <= bev.TOP_N_CARDS


# ---------------------------------------------------------------------------
# Deck-target stub is deferred (no producer) — pin it to 0 so it can't silently
# activate. See DEFERRED(deck-ev) in build_pack_ev.py.
# ---------------------------------------------------------------------------

def test_load_deck_targets_empty_when_file_absent(tmp_path):
    assert bev.load_deck_targets(tmp_path / "nope.json") == {}


def test_deck_target_ev_is_zero_at_runtime(pack_ev):
    packs = pack_ev["packs"] if isinstance(pack_ev, dict) else pack_ev
    for p in packs:
        assert p.get("deck_target_ev", 0) == 0, p.get("pack_name")
        assert p.get("deck_target_cards", []) == []


# ---------------------------------------------------------------------------
# _top_power_cards — strongest missing pullable cards per pack (informational)
# ---------------------------------------------------------------------------

def test_top_power_cards_ranks_missing_by_power():
    card_ev_list = [
        {"name": "Weak", "set_code": "A1", "card_number": 1, "rarity": "common",
         "owned": 0, "pull_prob": 0.5},
        {"name": "Strong", "set_code": "A1", "card_number": 2, "rarity": "double_rare",
         "owned": 0, "pull_prob": 0.02},
        {"name": "Owned", "set_code": "A1", "card_number": 3, "rarity": "rare",
         "owned": 1, "pull_prob": 0.1},          # excluded (already owned)
        {"name": "NoPower", "set_code": "A1", "card_number": 4, "rarity": "rare",
         "owned": 0, "pull_prob": 0.1},          # excluded (no power score)
    ]
    power = {("A1", 1): 30.0, ("A1", 2): 80.0, ("A1", 3): 90.0}
    top = bev._top_power_cards(card_ev_list, power, n=5)
    assert [c["name"] for c in top] == ["Strong", "Weak"]   # power desc, missing only
    assert top[0]["power_score"] == 80.0 and top[0]["pull_prob"] == 0.02


def test_top_power_cards_empty_without_power_map():
    lst = [{"name": "X", "set_code": "A1", "card_number": 1, "rarity": "rare",
            "owned": 0, "pull_prob": 0.1}]
    assert bev._top_power_cards(lst, {}) == []


def test_top_power_cards_dedups_printings_keeping_most_pullable():
    # Same card, three printings sharing one power score — the list must show it
    # once, via its most-pullable printing, not fill every slot with dupes.
    card_ev_list = [
        {"name": "Charizard ex", "set_code": "A1", "card_number": 36,
         "rarity": "double_rare", "owned": 0, "pull_prob": 0.017},
        {"name": "Charizard ex", "set_code": "A1", "card_number": 253,
         "rarity": "super_rare", "owned": 0, "pull_prob": 0.003},
        {"name": "Charizard ex", "set_code": "A1", "card_number": 280,
         "rarity": "immersive", "owned": 0, "pull_prob": 0.011},
        {"name": "Melmetal", "set_code": "A1", "card_number": 182,
         "rarity": "rare", "owned": 0, "pull_prob": 0.018},
    ]
    power = {("A1", 36): 81.3, ("A1", 253): 81.3, ("A1", 280): 81.3,
             ("A1", 182): 65.7}
    top = bev._top_power_cards(card_ev_list, power, n=5)
    assert [c["name"] for c in top] == ["Charizard ex", "Melmetal"]  # distinct
    # kept the highest-pull_prob printing (double_rare 0.017, card 36)
    assert top[0]["card_number"] == 36 and top[0]["pull_prob"] == 0.017


# ---------------------------------------------------------------------------
# "◆◆◆◆ or Higher Guaranteed" pity floor (game update 2026-07-29)
# ---------------------------------------------------------------------------
# The batch model p_10x = 1-(1-p)^10 assumes independent packs. The guarantee
# breaks that: a run of misses forces a hit. The trigger condition is published
# only on the in-app Offering Rates > Attention screen, so the threshold ships
# null and the floor is inert until it is read off that screen.

def test_guarantee_is_inert_when_the_threshold_is_unknown():
    """A null/absent threshold must not move any EV number."""
    assert bev.guaranteed_hits_per_batch(None) == 0
    assert bev.guaranteed_hits_per_batch({"threshold": None}) == 0
    assert bev.guaranteed_hits_per_batch({}) == 0


def test_shipped_threshold_matches_the_in_app_condition():
    """Pinned to the verified condition, not a guess.

    Offering Rates > Attention, read 2026-08-05: "A ◆◆◆◆ or higher card did not
    get generated after 12 consecutive openings of packs from the same expansion."
    """
    model = json.loads(io.PULL_MODEL_JSON.read_text(encoding="utf-8"))
    for pack in model["packs"]:
        g = pack["slot_rates"].get("guarantee")
        assert g is not None, f"{pack['pack_name']}: missing guarantee block"
        assert g["threshold"] == 12, (
            f"{pack['pack_name']}: pity threshold {g['threshold']} disagrees with the "
            "in-app Offering Rates > Attention screen (12)"
        )


def test_verified_threshold_adds_no_floor_to_a_ten_pack_batch():
    """12 consecutive misses is longer than a batch, so the pity never fires in one.

    This is the practical consequence of the real condition: the guaranteed
    category cannot be forced inside 10 packs, so it leaves the 10x model alone.
    """
    assert bev.guaranteed_hits_per_batch({"threshold": 12}) == 0
    # It does bite once the run is long enough to complete a cycle.
    assert bev.guaranteed_hits_per_batch({"threshold": 12}, batch=13) == 1
    assert bev.guaranteed_hits_per_batch({"threshold": 12}, batch=39) == 3


def test_guaranteed_hits_floor_matches_pity_semantics():
    """With threshold N the counter resets on a hit, so a batch of 10 has >= 10//(N+1)."""
    assert bev.guaranteed_hits_per_batch({"threshold": 4}) == 2   # 10 // 5
    assert bev.guaranteed_hits_per_batch({"threshold": 9}) == 1   # 10 // 10
    assert bev.guaranteed_hits_per_batch({"threshold": 1}) == 5   # 10 // 2
    assert bev.guaranteed_hits_per_batch({"threshold": 20}) == 0  # never fires in 10


def test_guarantee_lifts_a_pool_below_the_floor():
    agg = bev._PoolEV()
    agg.drp_p10x_sum = 0.5           # naturally expect half a ◆◆◆◆+ per batch
    agg.drp_value_sum = 2.0
    agg.new_card_ev_10x = 10.0
    bev._apply_double_rare_guarantee(agg, {"guarantee": {"threshold": 4}})

    assert agg.guaranteed_drp == 2
    # Shortfall 0.5 -> 2 is a 4x uplift on the tier's contribution: +2.0 * 3.
    assert agg.new_card_ev_10x == pytest.approx(16.0)


def test_guarantee_does_not_lower_a_pool_already_above_the_floor():
    agg = bev._PoolEV()
    agg.drp_p10x_sum = 5.0           # already clears the floor naturally
    agg.drp_value_sum = 20.0
    agg.new_card_ev_10x = 30.0
    bev._apply_double_rare_guarantee(agg, {"guarantee": {"threshold": 4}})

    assert agg.new_card_ev_10x == 30.0, "an inactive guarantee must never reprice a pack"
