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


# ---------------------------------------------------------------------------
# append_sync_history — running log the web Sync page reads
# ---------------------------------------------------------------------------

import json

import pytest


@pytest.fixture
def history_path(tmp_path, monkeypatch):
    p = tmp_path / "sync_history.json"
    monkeypatch.setattr(sc, "SYNC_DIR", tmp_path)
    monkeypatch.setattr(sc, "SYNC_HISTORY", p)
    return p


def _delta(added_count, names=("Pikachu",)):
    return {
        "generated_at": "2026-06-21",
        "added_count": added_count,
        "added": [{"name": n, "is_new": True, "added": 1} for n in names],
    }


def test_empty_delta_is_not_recorded(history_path):
    sc.append_sync_history(_delta(0, names=()))
    assert not history_path.exists()


def test_append_records_newest_last_with_timestamp(history_path):
    sc.append_sync_history(_delta(1, ("Pikachu",)))
    sc.append_sync_history(_delta(2, ("Mew", "Eevee")))
    entries = json.loads(history_path.read_text())["entries"]
    assert [e["added_count"] for e in entries] == [1, 2]  # newest last
    assert all("synced_at" in e for e in entries)
    assert entries[1]["added"][0]["name"] == "Mew"


def test_history_is_capped(history_path):
    for _ in range(sc.MAX_SYNC_HISTORY + 5):
        sc.append_sync_history(_delta(1))
    entries = json.loads(history_path.read_text())["entries"]
    assert len(entries) == sc.MAX_SYNC_HISTORY


def test_corrupt_history_is_replaced_not_fatal(history_path):
    history_path.write_text("{ not json")
    sc.append_sync_history(_delta(1))
    entries = json.loads(history_path.read_text())["entries"]
    assert len(entries) == 1
