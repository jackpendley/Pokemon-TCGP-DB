"""
Tests for the consolidated by-coord indexers in _collection_io.

The three public loaders (pack_sources/card_reference/ext_ref) now share one
_index_by_coord core; these pin the semantics that differ between them so the
consolidation can't silently drift.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io


def test_index_uppercases_and_ints():
    recs = [{"set_code": "a1", "card_number": "7"}]
    assert io._index_by_coord(recs, "card_number") == {("A1", 7): recs[0]}


def test_index_skips_blank_set_code_by_default():
    recs = [{"set_code": "", "card_number": 5}, {"set_code": "A1", "card_number": 6}]
    assert io._index_by_coord(recs, "card_number") == {("A1", 6): recs[1]}


def test_index_keeps_blank_set_code_when_not_required():
    recs = [{"set_code": "", "card_number": 5}, {"set_code": "A1", "card_number": 6}]
    out = io._index_by_coord(recs, "card_number", require_set_code=False)
    assert out == {("", 5): recs[0], ("A1", 6): recs[1]}


def test_index_skips_missing_and_unparseable_numbers():
    recs = [
        {"set_code": "A1"},                       # no number key
        {"set_code": "A1", "card_number": None},  # explicit None
        {"set_code": "A1", "card_number": "x"},   # non-int
        {"set_code": "A1", "card_number": 3},     # good
    ]
    assert io._index_by_coord(recs, "card_number") == {("A1", 3): recs[3]}


def test_ext_ref_uses_number_key():
    recs = [{"set_code": "A1", "number": 9}]
    assert io._index_by_coord(recs, "number") == {("A1", 9): recs[0]}


def test_card_reference_missing_file_returns_empty(tmp_path):
    assert io.card_reference_by_coord(tmp_path / "absent.json") == {}


def test_card_reference_keeps_blank_set_code(tmp_path):
    p = tmp_path / "cr.json"
    p.write_text(json.dumps({"records": [{"set_code": "", "card_number": 1}]}))
    assert io.card_reference_by_coord(p) == {("", 1): {"set_code": "", "card_number": 1}}


def test_pack_sources_envelope_and_flat(tmp_path):
    env = tmp_path / "env.json"
    env.write_text(json.dumps({"records": [{"set_code": "A1", "card_number": 1}]}))
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps([{"set_code": "A1", "card_number": 1}]))
    assert io.pack_sources_by_coord(env) == io.pack_sources_by_coord(flat)
