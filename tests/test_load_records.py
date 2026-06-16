"""
Tests for _collection_io.load_records — the shared JSON-records loader that
replaced the per-script ``raw.get("records", raw) if isinstance(...)`` idiom and
added a corrupt-JSON guard.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _collection_io import load_records


def test_envelope_form(tmp_path):
    p = tmp_path / "env.json"
    p.write_text(json.dumps({"records": [{"x": 1}, {"x": 2}]}))
    assert load_records(p) == [{"x": 1}, {"x": 2}]


def test_flat_array_form(tmp_path):
    p = tmp_path / "flat.json"
    p.write_text(json.dumps([{"y": 1}]))
    assert load_records(p) == [{"y": 1}]


def test_dict_without_records_key_passes_through(tmp_path):
    # Preserves the historical get("records", raw) fallback so behaviour is
    # identical to the idiom this helper replaced.
    p = tmp_path / "weird.json"
    p.write_text(json.dumps({"foo": 1}))
    assert load_records(p) == {"foo": 1}


def test_empty_envelope(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"records": []}))
    assert load_records(p) == []


def test_corrupt_json_raises_value_error_naming_path(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid json")
    with pytest.raises(ValueError) as exc:
        load_records(p)
    assert "broken.json" in str(exc.value)


def test_accepts_str_path(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps([{"z": 9}]))
    assert load_records(str(p)) == [{"z": 9}]
