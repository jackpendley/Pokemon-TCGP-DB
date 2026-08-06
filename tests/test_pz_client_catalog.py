"""
Guards for PZ catalog decoding in pokemon_zone_client.

Both behaviours here were found while investigating why the 2026-08-03 sync
picked up none of the newly-released B4 cards:

  * owned cards the catalog cannot name used to be dropped with no warning and
    no counter, so a whole set missing from PZ looked identical to a clean sync;
  * PZ reports expansionIds as a list, and everything past [0] was discarded —
    but since the 2026-07-29 update a card registers in the dex under every
    expansion in that list.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pokemon_zone_client as pz


class _Resp:
    status_code = 200

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def _body(cards):
    return {"data": {"cards": cards}}


def _run(monkeypatch, cards, catalog):
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _Resp(_body(cards)))
    return pz._fetch_and_normalize_cards("http://x", {}, {}, catalog)


CATALOG = {"c1": {"name": "Bulbasaur", "set_code": "A1", "card_number": 1}}


def test_uncatalogued_card_is_reported_not_dropped(monkeypatch):
    cards = [
        {"cardId": "c1", "amount": 1, "expansionIds": ["A1"]},
        {"cardId": "unknown-b4", "amount": 3, "expansionIds": ["B4"]},
    ]
    arr, _body_out, status, misses = _run(monkeypatch, cards, CATALOG)

    assert status == 200
    # The known card still comes through untouched.
    assert [c["cardName"] for c in arr] == ["Bulbasaur"]
    # The unknown one is accounted for rather than vanishing.
    assert misses["count"] == 1
    assert misses["copies"] == 3
    assert misses["card_ids"] == ["unknown-b4"]


def test_no_misses_reports_empty(monkeypatch):
    cards = [{"cardId": "c1", "amount": 2, "expansionIds": ["A1"]}]
    arr, _body_out, _status, misses = _run(monkeypatch, cards, CATALOG)

    assert len(arr) == 1
    assert misses == {}


def test_all_expansion_ids_are_carried_through(monkeypatch):
    """A card registered in several expansions keeps the full list.

    setCode stays the first (debut) entry so existing coord matching is
    unaffected; build_printing_groups consumes the rest.
    """
    cards = [{"cardId": "c1", "amount": 1, "expansionIds": ["A1", "A4b"]}]
    arr, _body_out, _status, _misses = _run(monkeypatch, cards, CATALOG)

    assert arr[0]["setCode"] == "A1"
    assert arr[0]["expansionIds"] == ["A1", "A4b"]


def test_missing_expansion_ids_falls_back_to_catalog_set(monkeypatch):
    cards = [{"cardId": "c1", "amount": 1}]
    arr, _body_out, _status, _misses = _run(monkeypatch, cards, CATALOG)

    assert arr[0]["setCode"] == "A1"
    assert arr[0]["expansionIds"] == []


def test_empty_catalog_still_passes_raw_records(monkeypatch):
    """With no catalog at all, records pass through for normalize_pz_record.

    This path must not be counted as a miss — nothing was resolvable.
    """
    cards = [{"cardId": "c1", "amount": 1, "expansionIds": ["A1"]}]
    arr, _body_out, _status, misses = _run(monkeypatch, cards, {})

    assert arr == cards
    assert misses == {}


def test_catalog_misses_reach_player_stats(monkeypatch, tmp_path):
    """sync_status.stats is player_stats.json verbatim, so misses must land there."""
    target = tmp_path / "player_stats.json"
    monkeypatch.setattr(pz, "PLAYER_STATS_CACHE", target)

    pz._save_player_stats({}, {"count": 2, "copies": 5, "card_ids": ["a", "b"]})

    import json

    assert json.loads(target.read_text())["catalog_misses"]["copies"] == 5
