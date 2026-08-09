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

import json
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

    assert json.loads(target.read_text())["catalog_misses"]["copies"] == 5


# ---------------------------------------------------------------------------
# nextSyncPlayerAt is advisory, NOT a rate limit
# ---------------------------------------------------------------------------
# PZ sets this field to trigger+12h on every accepted request, which made it look
# like a cooldown. It is not enforced. Syncs demonstrably succeed inside it:
# 2026-07-10/11 (2.7h apart), 2026-07-23 (2.3h) and 2026-07-23/24 (7.4h) all
# completed, and a deliberate test on 2026-08-09 *inside* the window returned
# successCount=1008 in nine seconds.
#
# Treating it as a hard block was a wrong diagnosis that stopped legitimate
# refreshes. The August hangs were Pokémon Zone's ingestion being down; the window
# they fell inside was a coincidence. These tests pin that the field never gates a
# sync.

from datetime import datetime, timedelta, timezone  # noqa: E402


def test_parses_the_advisory_timestamp():
    got = pz._parse_next_sync_at("2026-08-07T08:59:49.647480+00:00")
    assert got == datetime(2026, 8, 7, 8, 59, 49, 647480, tzinfo=timezone.utc)


def test_naive_and_zulu_timestamps_are_read_as_utc():
    assert pz._parse_next_sync_at("2026-08-07T08:59:49Z").tzinfo is not None
    assert pz._parse_next_sync_at("2026-08-07T08:59:49").tzinfo == timezone.utc


def test_missing_or_junk_advisory_is_ignored():
    for value in (None, "", "not a date", 12345):
        assert pz._parse_next_sync_at(value) is None


def _identity(next_sync):
    return {"data": {"players": [{"friendId": "1"}], "nextSyncPlayerAt": next_sync}}


class _R:
    status_code = 200

    def __init__(self, body):
        self._b = body

    def json(self):
        return self._b


def test_still_triggers_inside_the_advisory_window(monkeypatch):
    """The regression that matters: an advisory hint must never block a refresh."""
    future = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _R(_identity(future)))
    posted = []
    monkeypatch.setattr(pz, "_post",
                        lambda *a, **k: (posted.append(1), _R({"data": {}}))[1])

    pz.trigger_player_sync({}, {})
    assert posted == [1], (
        "nextSyncPlayerAt is advisory — PZ answers syncs inside it "
        "(verified 2026-08-09: successCount=1008 in 9s)"
    )
    assert pz._SYNC_ADVISORY_NEXT[0], "the hint should still be recorded for context"


def test_expired_advisory_is_not_recorded(monkeypatch):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _R(_identity(past)))
    monkeypatch.setattr(pz, "_post", lambda *a, **k: _R({"data": {}}))
    pz.trigger_player_sync({}, {})
    assert pz._SYNC_ADVISORY_NEXT[0] is None


def test_absent_advisory_does_not_block(monkeypatch):
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _R(_identity(None)))
    posted = []
    monkeypatch.setattr(pz, "_post",
                        lambda *a, **k: (posted.append(1), _R({"data": {}}))[1])
    pz.trigger_player_sync({}, {})
    assert posted == [1]


# ---------------------------------------------------------------------------
# "Refresh completed" is not proof the snapshot advanced
# ---------------------------------------------------------------------------
# 2026-08-04: the sync task reported ready=true with no successCount, Pokémon
# Zone's player.lastUpdatedAt stayed on 2026-07-28, and the run republished a
# six-day-old snapshot as a clean success. Six more days of "successful" syncs
# followed before anyone looked at the timestamp. The task's own verdict is not
# trustworthy; PZ's ingest timestamp is.

def _player_body(last_updated):
    return {"data": {"player": {"lastUpdatedAt": last_updated}, "cards": []}}


def test_reads_pz_ingest_timestamp():
    assert pz._player_last_updated_at(
        _player_body("2026-08-09T16:49:33Z")) == "2026-08-09T16:49:33Z"


def test_missing_ingest_timestamp_is_none():
    for body in ({}, {"data": {}}, {"data": {"player": {}}}, None, []):
        assert pz._player_last_updated_at(body) is None


def test_previous_timestamp_round_trips_through_player_stats(monkeypatch, tmp_path):
    target = tmp_path / "player_stats.json"
    monkeypatch.setattr(pz, "PLAYER_STATS_CACHE", target)
    assert pz._previous_last_updated_at() is None      # nothing recorded yet

    pz._save_player_stats({}, None, player_synced=True,
                          source_last_updated_at="2026-07-28T05:28:43Z")
    assert pz._previous_last_updated_at() == "2026-07-28T05:28:43Z"


def test_unchanged_snapshot_is_reported_stale_despite_a_completed_task(monkeypatch, tmp_path):
    """The exact 2026-08-04 signature: task says done, nothing was ingested."""
    stats = tmp_path / "player_stats.json"
    monkeypatch.setattr(pz, "PLAYER_STATS_CACHE", stats)
    monkeypatch.setattr(pz, "DISCOVERY_CACHE", tmp_path / "d.json")
    monkeypatch.setattr(pz, "RAW_CACHE", tmp_path / "r.json")
    monkeypatch.setattr(pz, "AUTH_CACHE", tmp_path / "a.json")
    (tmp_path / "a.json").write_text(json.dumps(
        {"api_url": "http://x", "cookies": {}, "auth_headers": {}}), encoding="utf-8")

    # Previous run recorded the same timestamp PZ is about to serve again.
    pz._save_player_stats({}, None, player_synced=True,
                          source_last_updated_at="2026-07-28T05:28:43Z")

    body = {"data": {"player": {"lastUpdatedAt": "2026-07-28T05:28:43Z"},
                     "cards": [{"cardId": "c1", "amount": 1, "expansionIds": ["A1"]}]}}
    monkeypatch.setattr(pz, "trigger_player_sync", lambda *a, **k: True)
    monkeypatch.setattr(pz, "_fetch_catalog", lambda *a, **k: {
        "c1": {"name": "Bulbasaur", "set_code": "A1", "card_number": 1}})
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _Resp(body))

    pz.fetch_with_stored_auth()
    saved = json.loads(stats.read_text(encoding="utf-8"))
    assert saved["player_synced"] is False, (
        "an unchanged ingest timestamp must read as stale even when the task completed"
    )


def test_advanced_snapshot_reads_as_a_real_refresh(monkeypatch, tmp_path):
    stats = tmp_path / "player_stats.json"
    monkeypatch.setattr(pz, "PLAYER_STATS_CACHE", stats)
    monkeypatch.setattr(pz, "DISCOVERY_CACHE", tmp_path / "d.json")
    monkeypatch.setattr(pz, "RAW_CACHE", tmp_path / "r.json")
    monkeypatch.setattr(pz, "AUTH_CACHE", tmp_path / "a.json")
    (tmp_path / "a.json").write_text(json.dumps(
        {"api_url": "http://x", "cookies": {}, "auth_headers": {}}), encoding="utf-8")

    pz._save_player_stats({}, None, player_synced=True,
                          source_last_updated_at="2026-07-28T05:28:43Z")

    body = {"data": {"player": {"lastUpdatedAt": "2026-08-09T16:49:33Z"},
                     "cards": [{"cardId": "c1", "amount": 1, "expansionIds": ["A1"]}]}}
    monkeypatch.setattr(pz, "trigger_player_sync", lambda *a, **k: True)
    monkeypatch.setattr(pz, "_fetch_catalog", lambda *a, **k: {
        "c1": {"name": "Bulbasaur", "set_code": "A1", "card_number": 1}})
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _Resp(body))

    pz.fetch_with_stored_auth()
    saved = json.loads(stats.read_text(encoding="utf-8"))
    assert saved["player_synced"] is True
    assert saved["source_last_updated_at"] == "2026-08-09T16:49:33Z"


def test_first_ever_run_is_not_flagged_stale(monkeypatch, tmp_path):
    """With no previous timestamp there is nothing to compare — don't cry wolf."""
    stats = tmp_path / "player_stats.json"
    monkeypatch.setattr(pz, "PLAYER_STATS_CACHE", stats)
    monkeypatch.setattr(pz, "DISCOVERY_CACHE", tmp_path / "d.json")
    monkeypatch.setattr(pz, "RAW_CACHE", tmp_path / "r.json")
    monkeypatch.setattr(pz, "AUTH_CACHE", tmp_path / "a.json")
    (tmp_path / "a.json").write_text(json.dumps(
        {"api_url": "http://x", "cookies": {}, "auth_headers": {}}), encoding="utf-8")

    body = {"data": {"player": {"lastUpdatedAt": "2026-08-09T16:49:33Z"},
                     "cards": [{"cardId": "c1", "amount": 1, "expansionIds": ["A1"]}]}}
    monkeypatch.setattr(pz, "trigger_player_sync", lambda *a, **k: True)
    monkeypatch.setattr(pz, "_fetch_catalog", lambda *a, **k: {
        "c1": {"name": "Bulbasaur", "set_code": "A1", "card_number": 1}})
    monkeypatch.setattr(pz, "_get", lambda *a, **k: _Resp(body))

    pz.fetch_with_stored_auth()
    assert json.loads(stats.read_text(encoding="utf-8"))["player_synced"] is True
