"""
Tests for build_card_reference.reconcile_card — focused on the Limitless (ext_ref) stage
fallback for sets TCGdex doesn't cover (A4b/B2b/B3/B3A/promos).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_card_reference as bcr


def _reconcile(tcgdex_stage, ext_stage, set_code="B3A", num=3, name="Psyduck"):
    snapshots = {"serebii": {}, "bulbapedia": {}, "tcgdex": {}}
    if tcgdex_stage is not None:
        snapshots["tcgdex"] = {str(num): {"name": name, "stage": tcgdex_stage}}
    ps_record = {"card_name": name, "expansion": "Test"}
    return bcr.reconcile_card(set_code, num, ps_record, snapshots, ext_stage)


def test_tcgdex_stage_wins_over_ext():
    # When TCGdex (the structured authority) has a stage, ext_ref is ignored.
    assert _reconcile("Stage2", "Basic")["stage"] == "Stage2"


def test_ext_stage_fallback_when_tcgdex_absent():
    # TCGdex doesn't cover B3A → fall back to Limitless stage, mapped to spaceless format.
    assert _reconcile(None, "Basic")["stage"] == "Basic"
    assert _reconcile(None, "Stage 1")["stage"] == "Stage1"
    assert _reconcile(None, "Stage 2")["stage"] == "Stage2"


def test_no_stage_anywhere_is_none():
    assert _reconcile(None, None)["stage"] is None
    # Unknown/garbage ext stage maps to None rather than leaking through.
    assert _reconcile(None, "Stage X")["stage"] is None


def test_snapshot_only_card_reconciles_with_type():
    """Cards absent from pack_sources (e.g. newer promos) are emitted from the snapshots
    via a synthetic pack_sources record whose name comes from the snapshot. With two
    independent sources agreeing on the name, the record is 'confirmed' and Bulbapedia's
    type flows through — the mechanism that closes the promo type-validation gap."""
    snapshots = {
        "bulbapedia": {"58": {"name": "Tepig", "pokemon_type": "Fire", "rarity": "promo"}},
        "serebii":    {"58": {"name": "Tepig"}},  # has the name, no type (mirrors real data)
        "tcgdex":     {},
    }
    synth = {"card_number": 58, "card_name": "Tepig",
             "rarity": None, "pack_name": None, "expansion": None}
    rec = bcr.reconcile_card("PROMO-B", 58, synth, snapshots, ext_stage=None)
    assert rec["name"] == "Tepig"
    assert rec["pokemon_type"] == "Fire"
    assert rec["confidence"] == "confirmed"  # bulbapedia + serebii agree on the name


def test_snapshot_only_single_source_is_single():
    """One independent source only → 'single' confidence, but the name/type still flow
    through (no empty-name record)."""
    snapshots = {
        "bulbapedia": {"99": {"name": "Solo", "pokemon_type": "Water"}},
        "serebii":    {},
        "tcgdex":     {},
    }
    synth = {"card_number": 99, "card_name": "Solo",
             "rarity": None, "pack_name": None, "expansion": None}
    rec = bcr.reconcile_card("PROMO-B", 99, synth, snapshots, ext_stage=None)
    assert rec["name"] == "Solo"
    assert rec["pokemon_type"] == "Water"
    assert rec["confidence"] == "single"
