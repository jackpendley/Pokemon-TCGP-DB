"""
Producer-side lock for collection.json's meta block.

collection_summary.json passes meta through to the webapp, whose Zod schema
(web/types/collection-summary.ts) requires meta.total_cards (number),
meta.last_updated (string), and meta.format (string). Before this lock a
hand-edited collection.json missing one of them normalized successfully and
took the Dashboard down at readArtifact time; now the producer fails loudly.
The single definition lives in _collection_io and is consumed by both
normalize_current_collection (hard gate) and validate_current_collection.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _collection_io import meta_errors

VALID = {"total_cards": 1743, "last_updated": "2026-07-05", "format": "Pokemon TCG Pocket"}


def test_valid_meta_passes():
    assert meta_errors(VALID) == []


def test_missing_or_null_total_cards():
    assert meta_errors({**VALID, "total_cards": None})
    m = dict(VALID)
    del m["total_cards"]
    assert m and meta_errors(m)


def test_wrong_types_rejected():
    assert meta_errors({**VALID, "total_cards": "1743"})
    assert meta_errors({**VALID, "last_updated": None})
    assert meta_errors({**VALID, "format": 42})


def test_bool_total_cards_rejected():
    # isinstance(True, int) is True in Python; the web contract needs a number.
    assert meta_errors({**VALID, "total_cards": True})


def test_extra_keys_allowed():
    assert meta_errors({**VALID, "note": "anything"}) == []
