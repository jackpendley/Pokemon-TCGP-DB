"""
Regression tests for compute_sync_delta.build_delta — the before/after collection
diff that produces last_sync_delta.json.

The bug it fixes: an Illustration Rare pull (high card number) gets aggregated
onto its already-owned base printing (low number) during matching, then split
into its own entry by reconcile. A delta written mid-sync mislabeled the new IR
card as a copy of the base. A pure before/after collection diff must instead
report the IR coords as new and leave the unchanged base coords out entirely.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import compute_sync_delta as csd


def _coords(entries):
    return csd._counts_by_coord(entries)


def test_new_alt_art_is_new_not_a_base_copy():
    """The exact bug: base Oricorio(22)/Sandshrew(77) owned; IR (161/170) pulled."""
    prev = _coords([
        {"name": "Oricorio", "set_code": "B2", "card_number": 22, "count": 1},
        {"name": "Sandshrew", "set_code": "B2", "card_number": 77, "count": 2},
    ])
    curr = _coords([
        {"name": "Oricorio", "set_code": "B2", "card_number": 22, "count": 1},
        {"name": "Oricorio", "set_code": "B2", "card_number": 161, "count": 1},
        {"name": "Sandshrew", "set_code": "B2", "card_number": 77, "count": 2},
        {"name": "Sandshrew", "set_code": "B2", "card_number": 170, "count": 1},
    ])
    delta = csd.build_delta(prev, curr)

    by_coord = {(e["set_code"], e["card_number"]): e for e in delta["added"]}
    # Unchanged base coords must NOT appear.
    assert ("B2", 22) not in by_coord
    assert ("B2", 77) not in by_coord
    # The IR coords appear as brand-new.
    assert by_coord[("B2", 161)]["is_new"] is True
    assert by_coord[("B2", 161)]["previous_count"] == 0
    assert by_coord[("B2", 170)]["is_new"] is True
    assert delta["added_count"] == 2


def test_real_copy_increase_is_not_new():
    prev = _coords([{"name": "Pikachu", "set_code": "A1", "card_number": 94, "count": 1}])
    curr = _coords([{"name": "Pikachu", "set_code": "A1", "card_number": 94, "count": 2}])
    delta = csd.build_delta(prev, curr)
    assert delta["added_count"] == 1
    row = delta["added"][0]
    assert row["is_new"] is False
    assert row["previous_count"] == 1 and row["new_count"] == 2 and row["added"] == 1


def test_decreases_and_unchanged_are_ignored():
    prev = _coords([
        {"name": "Eevee", "set_code": "A1", "card_number": 1, "count": 4},
        {"name": "Mew", "set_code": "A1", "card_number": 2, "count": 1},
    ])
    curr = _coords([
        {"name": "Eevee", "set_code": "A1", "card_number": 1, "count": 2},  # decrease
        {"name": "Mew", "set_code": "A1", "card_number": 2, "count": 1},    # unchanged
    ])
    assert csd.build_delta(prev, curr)["added_count"] == 0


def test_new_cards_sort_first():
    prev = _coords([{"name": "A", "set_code": "A1", "card_number": 5, "count": 1}])
    curr = _coords([
        {"name": "A", "set_code": "A1", "card_number": 5, "count": 2},   # copy
        {"name": "B", "set_code": "A1", "card_number": 9, "count": 1},   # new
    ])
    added = csd.build_delta(prev, curr)["added"]
    assert added[0]["is_new"] is True and added[1]["is_new"] is False
