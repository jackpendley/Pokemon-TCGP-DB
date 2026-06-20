"""
Tests for build_sync_delta — the per-sync "what was added" record the web Sync
page displays, including the brand-new ("new") flag.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sync_collection as sc


def _change(name, set_code, num, old, new):
    entry = {"name": name, "set_code": set_code, "card_number": num, "count": new}
    return sc.CountChange(entry=entry, entry_index=0, old_count=old, new_count=new)


def test_count_increase_is_added_not_new():
    delta = sc.build_sync_delta([_change("Pikachu", "A1", 94, 1, 3)], [])
    assert delta["added_count"] == 1
    row = delta["added"][0]
    assert row["added"] == 2
    assert row["is_new"] is False
    assert row["previous_count"] == 1 and row["new_count"] == 3


def test_zero_to_owned_is_new():
    delta = sc.build_sync_delta([_change("Mew", "A1a", 10, 0, 1)], [])
    assert delta["added"][0]["is_new"] is True


def test_decrease_is_ignored():
    delta = sc.build_sync_delta([_change("Eevee", "A3b", 5, 4, 2)], [])
    assert delta["added_count"] == 0


def test_auto_added_cards_are_new():
    auto_added = [{"name": "Gengar ex", "set_code": "B3", "card_number": 45, "count": 1}]
    delta = sc.build_sync_delta([], auto_added)
    assert delta["added_count"] == 1
    row = delta["added"][0]
    assert row["is_new"] is True
    assert row["previous_count"] == 0 and row["added"] == 1


def test_combines_changes_and_auto_added():
    delta = sc.build_sync_delta(
        [_change("Pikachu", "A1", 94, 1, 2)],
        [{"name": "Gengar ex", "set_code": "B3", "card_number": 45, "count": 1}],
    )
    assert delta["added_count"] == 2
    assert {r["name"] for r in delta["added"]} == {"Pikachu", "Gengar ex"}
    assert "generated_at" in delta
