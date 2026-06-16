"""
Tests for _collection_io.validate_pack_sources_schema — the load-time schema
guard that makes malformed pack_sources fail loudly (instead of feeding missing
coords/fields silently into the EV model).
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io

pytest.importorskip("jsonschema")


def _rec(**over):
    base = {
        "set_code": "A1", "card_number": 1, "card_name": "Pikachu",
        "pack_name": None, "expansion": "Genetic Apex",
    }
    base.update(over)
    return base


def test_valid_envelope_passes():
    assert io.validate_pack_sources_schema({"records": [_rec()]}) is True


def test_valid_flat_array_is_wrapped_and_passes():
    assert io.validate_pack_sources_schema([_rec()]) is True


def test_real_pack_sources_passes():
    raw = json.loads(io.PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    assert io.validate_pack_sources_schema(raw) is True


def test_missing_required_field_raises_with_source():
    bad = {"records": [{k: v for k, v in _rec().items() if k != "card_number"}]}
    with pytest.raises(ValueError) as exc:
        io.validate_pack_sources_schema(bad, source="bad.json")
    msg = str(exc.value)
    assert "bad.json" in msg and "card_number" in msg


def test_invalid_rarity_enum_raises():
    with pytest.raises(ValueError):
        io.validate_pack_sources_schema({"records": [_rec(rarity="mythic")]})


def test_wrong_type_card_number_raises():
    with pytest.raises(ValueError):
        io.validate_pack_sources_schema({"records": [_rec(card_number="3")]})


def test_nullable_rarity_and_pack_name_allowed():
    assert io.validate_pack_sources_schema(
        {"records": [_rec(rarity=None, pack_name=None)]}
    ) is True
