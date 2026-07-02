"""
Phase 3 tests: generate_pack_recommendation_report.py.

Tests verify the unified-ranking output structure (no legacy 6-bucket keys)
and key field presence.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

RECOMMENDATIONS_JSON = ROOT / "data" / "current" / "inferred_pack_recommendations.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def recommendations():
    assert RECOMMENDATIONS_JSON.exists(), (
        "inferred_pack_recommendations.json not found — run generate_pack_recommendation_report.py first"
    )
    return json.loads(RECOMMENDATIONS_JSON.read_text(encoding="utf-8"))


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
