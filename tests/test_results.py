"""
Phase 3 tests: generate_pack_recommendation_report.py and generate_hourglass_spending_plan.py.

Tests verify the unified-ranking output structure (no legacy 6-bucket keys),
spending plan format (single plan, not scenarios array), and key field presence.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

RECOMMENDATIONS_JSON = ROOT / "data" / "current" / "inferred_pack_recommendations.json"
SPENDING_PLAN_JSON   = ROOT / "data" / "current" / "final_hourglass_spending_plan.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def recommendations():
    assert RECOMMENDATIONS_JSON.exists(), (
        "inferred_pack_recommendations.json not found — run generate_pack_recommendation_report.py first"
    )
    return json.loads(RECOMMENDATIONS_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def spending_plan_doc():
    assert SPENDING_PLAN_JSON.exists(), (
        "final_hourglass_spending_plan.json not found — run generate_hourglass_spending_plan.py first"
    )
    return json.loads(SPENDING_PLAN_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def spending_plan(spending_plan_doc):
    return spending_plan_doc["spending_plan"]


# ---------------------------------------------------------------------------
# 3.1: Recommendations output keys — no legacy bucket keys
# ---------------------------------------------------------------------------

REMOVED_KEYS = [
    "top_5_by_new_card_ev",
    "top_5_by_deck_target_ev",
    "top_5_by_ex_ev",
    "deprioritize_5",
    "planning_scenarios",
    "blockers",
    "next_actions",
]

REQUIRED_KEYS = [
    "top_packs_unified",
    "cost_efficiency_ranking",
    "chase_deck_packs",
]


def test_recommendations_no_legacy_keys(recommendations):
    """Legacy 6-bucket keys must not be present."""
    for key in REMOVED_KEYS:
        assert key not in recommendations, (
            f"Legacy key '{key}' still present in recommendations output"
        )


def test_recommendations_required_keys_present(recommendations):
    """New unified-ranking keys must be present."""
    for key in REQUIRED_KEYS:
        assert key in recommendations, (
            f"Required key '{key}' missing from recommendations output"
        )


def test_top_packs_unified_nonempty(recommendations):
    top = recommendations["top_packs_unified"]
    assert isinstance(top, list) and len(top) >= 1


def test_top_packs_unified_has_unified_score(recommendations):
    for p in recommendations["top_packs_unified"]:
        assert "unified_score" in p, f"{p.get('pack_name')} missing unified_score"
        assert p["unified_score"] >= 0.0


def test_top_packs_ordered_by_unified_score(recommendations):
    scores = [p["unified_score"] for p in recommendations["top_packs_unified"]]
    assert scores == sorted(scores, reverse=True), "top_packs_unified not sorted descending"


def test_cost_efficiency_ranking_nonempty(recommendations):
    cost = recommendations["cost_efficiency_ranking"]
    assert isinstance(cost, list) and len(cost) >= 1


def test_cost_efficiency_ordered_ascending(recommendations):
    costs = [p.get("cost_per_unique_card_10x", float("inf"))
             for p in recommendations["cost_efficiency_ranking"]]
    assert costs == sorted(costs), "cost_efficiency_ranking not sorted ascending"


# ---------------------------------------------------------------------------
# 3.2: Spending plan — single plan, not scenarios array
# ---------------------------------------------------------------------------

def test_spending_plan_key_present(spending_plan_doc):
    assert "spending_plan" in spending_plan_doc, "Missing 'spending_plan' key"


def test_no_scenarios_key(spending_plan_doc):
    assert "scenarios" not in spending_plan_doc, (
        "Stale 'scenarios' key found — should be replaced by 'spending_plan'"
    )


def test_batches_nonempty(spending_plan):
    batches = spending_plan.get("batches", [])
    assert len(batches) >= 1, "spending_plan.batches is empty"


def test_batches_have_required_fields(spending_plan):
    required = [
        "batch_number", "pack_name", "hourglass_cost",
        "unified_score", "new_card_ev_10x", "rerun_after", "notes",
    ]
    for b in spending_plan["batches"]:
        for field in required:
            assert field in b, f"Batch {b.get('batch_number')} missing field '{field}'"


def test_batch_hourglass_cost_correct(spending_plan):
    """Each batch costs BATCH_SIZE × HOURGLASS_PER_PACK hourglasses."""
    for b in spending_plan["batches"]:
        expected = b["packs_to_open"] * 12
        assert b["hourglass_cost"] == expected, (
            f"Batch {b['batch_number']}: expected {expected}⧗, got {b['hourglass_cost']}⧗"
        )


def test_total_hourglasses_matches_sum(spending_plan):
    total = sum(b["hourglass_cost"] for b in spending_plan["batches"])
    assert spending_plan["total_hourglasses"] == total


def test_rerun_after_batch_n_nonempty(spending_plan):
    rerun = spending_plan.get("rerun_after_batch_n", [])
    assert len(rerun) >= 1, "At least one rerun trigger required"


def test_stopping_condition_present(spending_plan):
    sc = spending_plan.get("stopping_condition", "")
    assert len(sc) > 10, "stopping_condition missing or too short"


def test_batch3_rotates(spending_plan):
    """Batch 3 must open a pack different from both batch 1 and batch 2."""
    batches = spending_plan.get("batches", [])
    if len(batches) >= 3:
        b1_name = batches[0]["pack_name"]
        b2_name = batches[1]["pack_name"]
        b3_name = batches[2]["pack_name"]
        assert b2_name != b3_name, (
            f"Batch 2 and batch 3 both open '{b2_name}' — no rotation"
        )
        # When batch 1 and 2 differ (near-complete switch happened), batch 3 must differ from both.
        if b1_name != b2_name:
            assert b3_name not in (b1_name, b2_name), (
                f"Batch 3 ({b3_name}) repeats a prior pack — expected rotation to a third pack"
            )


def test_collection_mutated_false(spending_plan_doc):
    assert spending_plan_doc.get("collection_mutated") is False


# ---------------------------------------------------------------------------
# Cross-check: spending plan top pack == recommendation top pack
# ---------------------------------------------------------------------------

def test_spending_plan_top_pack_matches_recommendations(recommendations, spending_plan):
    rec_top = recommendations["top_packs_unified"][0]["pack_name"]
    plan_top = spending_plan["batches"][0]["pack_name"]
    assert rec_top == plan_top, (
        f"Spending plan batch 1 ({plan_top}) doesn't match recommendations top ({rec_top})"
    )
