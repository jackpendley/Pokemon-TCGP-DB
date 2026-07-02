"""
Output-contract tests: lock the shape of the JSON artifacts the web front end
(web/) consumes, so a backend refactor or publish step can't silently change the
contract the Next.js Zod schemas mirror.

Scope here is the *frontend-facing contract*: the set of keys each consumer reads
plus cross-artifact / structural invariants. The EV *math* (rarity ordering, 10x
formula, confidence weighting) is covered by test_ev.py; the recommendation
output is covered by test_results.py. This module fills the gap:
collection_summary.json had no coverage, and no test pinned the per-pack field set.

"Required keys" use subset semantics (all listed keys must be present): a consumer
breaks when a field is removed or renamed, not when a new field is added.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "data" / "current"

PACK_EV_JSON = CUR / "pack_ev.json"
RECOMMENDATIONS_JSON = CUR / "inferred_pack_recommendations.json"
COLLECTION_SUMMARY_JSON = CUR / "collection_summary.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    assert path.exists(), f"{path.name} not found — run scripts/run_recommendations.py --skip-sync"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack_ev():
    return _load(PACK_EV_JSON)


@pytest.fixture(scope="module")
def recommendations():
    return _load(RECOMMENDATIONS_JSON)


@pytest.fixture(scope="module")
def collection_summary():
    return _load(COLLECTION_SUMMARY_JSON)


# ---------------------------------------------------------------------------
# Required key sets (the contract the web/ Zod schemas mirror)
# ---------------------------------------------------------------------------

PACK_EV_TOP_LEVEL = {
    "generated_at", "generated_by", "meta", "scoring_weights", "confidence_weights",
    "deck_targets", "overall_summary", "packs", "blocked_packs", "next_steps",
}

# Fields each pack record exposes — consumed by the Packs list, Pack detail,
# and recommendations pages. Kept in sync with build_pack_ev.py output.
PACK_RECORD_FIELDS = {
    "pack_name", "expansion", "set_code", "source_status", "slot_rates_confidence",
    "confidence_weight", "blocked", "blocked_reason", "purchasable",
    "cards_in_pool", "owned_in_pool", "missing_in_pool",
    "base_cards_in_pool", "base_owned_in_pool",
    "new_card_ev", "new_card_ev_10x", "copy_ev", "deck_target_ev",
    "missing_rare_plus", "rare_plus_ev_10x", "pack_total_ev", "confidence_adjusted_ev",
    "unified_score", "ev_diminishing_returns_ratio",
    "cost_per_unique_card_1x", "cost_per_unique_card_10x",
    "pz_coverage", "deck_target_cards", "notes",
}

TOP_EV_CARD_FIELDS = {
    "name", "rarity", "owned", "pull_prob", "value",
    "ev_contribution", "is_deck_target", "rate_source",
}

RECOMMENDATIONS_TOP_LEVEL = {
    "generated_at", "generated_by", "model_confidence", "collection_total",
    "collection_mutated", "inputs_hash", "disclaimer",
    "top_packs_unified", "cost_efficiency_ranking", "chase_deck_packs",
}

COLLECTION_SUMMARY_TOP_LEVEL = {
    "meta", "total_quantity", "meta_total_cards", "count_matches_meta",
    "unique_entries", "by_card_type", "by_pokemon_type", "by_stage",
    "ex_entries", "ex_quantity", "trainer_subtypes", "top_cards_by_count",
    "variant_names", "evolution_groups",
}

EVOLUTION_GROUP_FIELDS = {"line", "owned", "missing", "complete"}


def _assert_keys(required: set, actual_keys, label: str):
    missing = required - set(actual_keys)
    assert not missing, f"{label} missing required keys: {sorted(missing)}"


# ---------------------------------------------------------------------------
# pack_ev.json contract
# ---------------------------------------------------------------------------

def test_pack_ev_top_level_keys(pack_ev):
    _assert_keys(PACK_EV_TOP_LEVEL, pack_ev.keys(), "pack_ev.json")


def test_pack_ev_packs_nonempty(pack_ev):
    assert isinstance(pack_ev["packs"], list) and len(pack_ev["packs"]) >= 1


def test_pack_ev_every_pack_has_contract_fields(pack_ev):
    for p in pack_ev["packs"]:
        _assert_keys(PACK_RECORD_FIELDS, p.keys(), f"pack '{p.get('pack_name')}'")


def test_pack_ev_top_ev_cards_contract_fields(pack_ev):
    for p in pack_ev["packs"]:
        for card in p.get("top_ev_cards", []):
            _assert_keys(TOP_EV_CARD_FIELDS, card.keys(),
                         f"top_ev_cards in '{p.get('pack_name')}'")


def test_pack_ev_meta_has_collection_total(pack_ev):
    assert "collection_total" in pack_ev["meta"]
    assert isinstance(pack_ev["meta"]["collection_total"], int)


def test_pack_ev_pool_counts_consistent(pack_ev):
    """owned + missing must equal the pool size for every pack."""
    for p in pack_ev["packs"]:
        assert p["owned_in_pool"] + p["missing_in_pool"] == p["cards_in_pool"], (
            f"{p['pack_name']}: owned+missing != cards_in_pool"
        )


def test_pack_ev_scores_nonnegative(pack_ev):
    for p in pack_ev["packs"]:
        assert p["new_card_ev_10x"] >= 0.0, f"{p['pack_name']} negative new_card_ev_10x"
        assert p["unified_score"] >= 0.0, f"{p['pack_name']} negative unified_score"


# ---------------------------------------------------------------------------
# inferred_pack_recommendations.json contract
# ---------------------------------------------------------------------------

def test_recommendations_top_level_keys(recommendations):
    _assert_keys(RECOMMENDATIONS_TOP_LEVEL, recommendations.keys(),
                 "inferred_pack_recommendations.json")


def test_recommendations_packs_have_contract_fields(recommendations):
    for p in recommendations["top_packs_unified"]:
        _assert_keys(PACK_RECORD_FIELDS - {"top_ev_cards"}, p.keys(),
                     f"recommendation pack '{p.get('pack_name')}'")


# ---------------------------------------------------------------------------
# collection_summary.json contract (dashboard / sets pages)
# ---------------------------------------------------------------------------

def test_collection_summary_top_level_keys(collection_summary):
    _assert_keys(COLLECTION_SUMMARY_TOP_LEVEL, collection_summary.keys(),
                 "collection_summary.json")


def test_collection_summary_totals_consistent(collection_summary):
    assert collection_summary["count_matches_meta"] is True
    assert collection_summary["total_quantity"] == collection_summary["meta_total_cards"]


def test_collection_summary_breakdowns_are_int_maps(collection_summary):
    for field in ("by_card_type", "by_pokemon_type", "by_stage", "trainer_subtypes"):
        m = collection_summary[field]
        assert isinstance(m, dict) and m, f"{field} should be a non-empty map"
        assert all(isinstance(v, int) for v in m.values()), f"{field} values must be ints"


def test_collection_summary_top_cards_shape(collection_summary):
    """top_cards_by_count is a list of [name, count] pairs."""
    for entry in collection_summary["top_cards_by_count"]:
        assert isinstance(entry, list) and len(entry) == 2
        assert isinstance(entry[0], str) and isinstance(entry[1], int)


def test_collection_summary_evolution_groups_shape(collection_summary):
    for g in collection_summary["evolution_groups"]:
        _assert_keys(EVOLUTION_GROUP_FIELDS, g.keys(), "evolution_group")
        assert isinstance(g["complete"], bool)


# ---------------------------------------------------------------------------
# Cross-artifact consistency
# ---------------------------------------------------------------------------

def test_collection_total_agrees_across_artifacts(pack_ev, recommendations, collection_summary):
    total = collection_summary["total_quantity"]
    assert pack_ev["meta"]["collection_total"] == total
    assert recommendations["collection_total"] == total


def test_recommendation_top_pack_exists_in_pack_ev(pack_ev, recommendations):
    pack_ev_names = {p["pack_name"] for p in pack_ev["packs"]}
    top = recommendations["top_packs_unified"][0]["pack_name"]
    assert top in pack_ev_names, f"recommendation top pack '{top}' absent from pack_ev packs"
