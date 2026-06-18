"""
Tests for the Pokémon energy-type cross-check in validate_collection_coords.validate_entry.

A wrong `type` has a single authoritative answer in the cross-validated reference, so a
disagreement is a SERIOUS error (it skews every type-aware count). Cards with no
authoritative type are reported as 'uncovered' (a blind spot) but never fail — we can't
prove wrong what no source can confirm.

    python3 -m pytest tests/test_collection_type_validation.py
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "validate_collection_coords", ROOT / "scripts" / "validate_collection_coords.py")
vcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcc)


def _entry(**kw):
    base = {"name": "Pikachu", "set_code": "ZZ", "card_number": 1,
            "card_type": "Pokemon", "type": "Lightning"}
    base.update(kw)
    return base


def _validate(entry, card_ref=None, ext_ref=None, pack_sources=None):
    """Run validate_entry offline with no TCGdex/Limitless sources."""
    return vcc.validate_entry(
        entry, pack_sources or {}, ext_ref or {}, {}, set(), False,
        {"count": 0}, frozenset(), None, card_ref=card_ref or {})


def test_correct_type_passes():
    card_ref = {("ZZ", 1): {"name": "Pikachu", "pokemon_type": "Lightning",
                            "confidence": "confirmed"}}
    r = _validate(_entry(type="Lightning"), card_ref=card_ref)
    assert r["type_check"] == "ok"
    assert r["status"] == "ok" and not r.get("serious")


def test_wrong_type_is_serious():
    card_ref = {("ZZ", 1): {"name": "Pikachu", "pokemon_type": "Lightning",
                            "confidence": "confirmed"}}
    r = _validate(_entry(type="Water"), card_ref=card_ref)
    assert r["type_check"] == "mismatch"
    assert r["status"] == "mismatch" and r["serious"] is True
    assert any("type mismatch" in i for i in r["issues"])


def test_uncovered_type_is_not_fatal():
    # No source has a type for this coord → uncovered, but must not fail validation.
    r = _validate(_entry(type="Lightning"), card_ref={})
    assert r["type_check"] == "uncovered"
    assert not r.get("serious")


def test_ext_ref_fallback_when_reference_unconfirmed():
    # card_reference type only at <confirmed confidence → ext_ref (limitless) wins.
    card_ref = {("ZZ", 1): {"name": "Pikachu", "pokemon_type": "Metal",
                            "confidence": "single"}}
    ext_ref = {("ZZ", 1): {"pokemon_type": "Lightning"}}
    r = _validate(_entry(type="Lightning"), card_ref=card_ref, ext_ref=ext_ref)
    assert r["type_check"] == "ok"


def test_trainer_is_not_type_checked():
    r = _validate(_entry(card_type="Trainer", type=None, name="Potion"), card_ref={})
    assert r["type_check"] == "n/a"
