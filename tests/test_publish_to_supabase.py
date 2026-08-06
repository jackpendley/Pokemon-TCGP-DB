"""
Publisher-contract tests: verify scripts/publish_to_supabase.py builds upsert
payloads whose shapes match the artifact contract the web Zod schemas mirror.

Uses the committed web/types/__fixtures__ artifacts as the contract (per the
hosting roadmap §4.2) plus minimal inline stubs for artifacts without a
fixture. Only the pure builders and publish() are exercised, with a fake
client — no network, and no `supabase` package import, so this runs in CI's
minimal pip environment.
"""

import sys
from pathlib import Path

import json

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from publish_to_supabase import (  # noqa: E402
    OWNER_USER_ID,
    TABLE_CONFLICT_KEYS,
    build_all_rows,
    build_last_run,
    build_card_rows,
    build_collection_rows,
    build_pack_card_rows,
    build_recommendation_snapshot_rows,
    is_mega,
    publish,
    publish_recommendation_snapshot,
    should_snapshot,
)

FIXTURES = ROOT / "web" / "types" / "__fixtures__"

CARD_COLUMNS = {
    "set_code", "card_number", "name", "rarity", "pokemon_type", "card_category",
    "trainer_subtype", "stage", "expansion", "is_ex", "is_mega", "evolves_from",
    "hp", "pack_name", "power_score", "power_score_kind", "boosts",
    "printing_group",
}


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def artifacts():
    """Fixture artifacts + minimal stubs shaped like the real files."""
    card_reference = {
        "records": [
            {
                "set_code": "A1", "card_number": 1, "name": "Bulbasaur",
                "rarity": "common", "pokemon_type": "Grass",
                "card_category": "Pokemon", "trainer_subtype": None,
                "stage": "Basic", "expansion": "Genetic Apex", "is_ex": False,
                "evolves_from": None, "hp": 70,
                "pack_name": "Mewtwo pack, Pikachu pack",
            },
            {
                "set_code": "A3", "card_number": 200, "name": "Mega Gyarados ex",
                "rarity": "double rare", "pokemon_type": "Water",
                "card_category": "Pokemon", "trainer_subtype": None,
                "stage": "Stage 1", "expansion": None, "is_ex": True,
                "evolves_from": "Magikarp", "hp": 210, "pack_name": "Lunala pack",
            },
        ]
    }
    return {
        "card_reference": card_reference,
        "card_power_scores": {
            "generated_at": "2026-01-01",
            "scores": {"A1:1": {"power_score": 42.5, "score_kind": "pokemon",
                                "hp": 70, "effective_damage": 30,
                                "has_ability": False, "estimated": False}},
        },
        "pull_probability_model": {"generated_at": "2026-01-01", "packs": {}},
        "collection_normalized": {
            "collection": [
                {"set_code": "A1", "card_number": 1, "count": 2, "entry_id": "x1"},
                {"set_code": "A1", "card_number": 1, "count": 1, "entry_id": "x2"},
            ]
        },
        "collection_summary": _fixture("collection_summary.json"),
        "pack_ev": _fixture("pack_ev.json"),
        "recommendations": _fixture("inferred_pack_recommendations.json"),
        "player_stats": None,
        "sync_review_queue": None,
        "last_sync_delta": None,
        "sync_history": {
            "entries": [{"synced_at": "2026-01-02T03:04:05", "added_count": 1,
                         "added": []}]
        },
    }


@pytest.fixture(scope="module")
def rows(artifacts):
    return build_all_rows(artifacts)


class FakeQuery:
    def __init__(self, log, table):
        self.log = log
        self.table_name = table
        self._op = None

    def upsert(self, rows, on_conflict=None):
        self._op = ("upsert", self.table_name, rows, on_conflict)
        return self

    def insert(self, rows):
        self._op = ("insert", self.table_name, rows, None)
        return self

    def delete(self):
        self._op = ("delete", self.table_name, None, None)
        return self

    def eq(self, column, value):
        op, table, rows, conflict = self._op
        self._op = (op, table, {column: value}, conflict)
        return self

    def execute(self):
        self.log.append(self._op)
        return self


class FakeClient:
    """Records (op, table, rows, on_conflict) for every executed call."""

    def __init__(self):
        self.log = []

    def table(self, name):
        return FakeQuery(self.log, name)


# ---------------------------------------------------------------------------
# Builders: payload shapes match the artifact contract
# ---------------------------------------------------------------------------

def test_card_rows_carry_printing_group():
    """Coords in a printing group publish their group; singles publish null.

    The group is what lets the catalog read credit one owned copy to every dex
    slot the card now registers in (game update 2026-07-29).
    """
    card_reference = {"records": [
        {"set_code": "A1", "card_number": 151, "name": "Cubone"},
        {"set_code": "A4b", "card_number": 194, "name": "Cubone"},
        {"set_code": "B4", "card_number": 1, "name": "Wurmple"},
    ]}
    groups = {"groups": [{"id": "g0042", "coords": [["A1", 151], ["A4b", 194]]}]}

    by_coord = {(r["set_code"], r["card_number"]): r
                for r in build_card_rows(card_reference, None, groups)}

    assert by_coord[("A1", 151)]["printing_group"] == "g0042"
    assert by_coord[("A4b", 194)]["printing_group"] == "g0042"
    assert by_coord[("B4", 1)]["printing_group"] is None


def test_card_rows_publish_without_printing_groups():
    """A checkout predating printing_groups.json still publishes."""
    card_reference = {"records": [
        {"set_code": "B4", "card_number": 1, "name": "Wurmple"},
    ]}
    rows = build_card_rows(card_reference, None, None)
    assert rows[0]["printing_group"] is None


def test_card_rows_carry_every_column(rows):
    assert len(rows["cards"]) == 2
    for row in rows["cards"]:
        assert set(row) == CARD_COLUMNS
    by_coord = {(r["set_code"], r["card_number"]): r for r in rows["cards"]}
    assert by_coord[("A1", 1)]["power_score"] == 42.5
    assert by_coord[("A3", 200)]["power_score"] is None
    # The kind travels with the score so consumers can't mix the two models.
    assert by_coord[("A1", 1)]["power_score_kind"] == "pokemon"
    assert by_coord[("A3", 200)]["power_score_kind"] is None
    # Boosts travel with the score too; a card with no score has no boosts.
    assert by_coord[("A3", 200)]["boosts"] is None
    # expansion falls back to set_code like loadCatalog does.
    assert by_coord[("A3", 200)]["expansion"] == "A3"


def test_is_mega_matches_web_domain_rule():
    assert is_mega({"is_ex": True, "name": "Mega Gyarados ex"})
    assert not is_mega({"is_ex": False, "name": "Mega Punch Fan"})
    assert not is_mega({"is_ex": True, "name": "Gyarados ex"})
    assert not is_mega({"is_ex": None, "name": "Mega Gyarados ex"})


def test_card_rows_without_power_scores(artifacts):
    rows = build_card_rows(artifacts["card_reference"], None)
    assert all(r["power_score"] is None for r in rows)


def test_pack_rows_one_per_fixture_pack(rows, artifacts):
    fixture_packs = artifacts["pack_ev"]["packs"]
    assert len(rows["packs"]) == len(fixture_packs)
    assert all(set(r) == {"pack_name", "expansion", "set_code"}
               for r in rows["packs"])


def test_pack_top_card_rows_carry_both_lists(rows, artifacts):
    fixture_packs = {p["pack_name"]: p for p in artifacts["pack_ev"]["packs"]}
    assert len(rows["pack_top_cards"]) == len(fixture_packs)
    for row in rows["pack_top_cards"]:
        fixture = fixture_packs[row["pack_name"]]
        assert row["top_ev_cards"] == fixture["top_ev_cards"]
        assert row["top_power_cards"] == fixture.get("top_power_cards", [])


def test_pack_card_rows_split_multi_pack_names(artifacts):
    rows = build_pack_card_rows(artifacts["card_reference"])
    a1 = {r["pack_name"] for r in rows if r["set_code"] == "A1"}
    assert a1 == {"Mewtwo pack", "Pikachu pack"}


def test_collection_rows_sum_duplicate_coords(artifacts):
    rows = build_collection_rows(artifacts["collection_normalized"], OWNER_USER_ID)
    assert rows == [
        {"user_id": OWNER_USER_ID, "set_code": "A1", "card_number": 1, "count": 3}
    ]


def test_document_rows_round_trip_fixtures_verbatim(rows, artifacts):
    # JSONB documents must be byte-identical to the artifact contract.
    assert rows["collection_summaries"][0]["payload"] == artifacts["collection_summary"]
    assert rows["pack_ev"][0]["payload"] == artifacts["pack_ev"]
    assert rows["recommendations"][0]["payload"] == artifacts["recommendations"]
    for table in ("collection_summaries", "pack_ev", "recommendations"):
        assert rows[table][0]["user_id"] == OWNER_USER_ID


def test_build_all_rows_stamps_a_custom_user_id(artifacts):
    # Phase 6: main() passes the real auth owner UUID via OWNER_USER_ID env.
    custom = build_all_rows(artifacts, user_id="custom-uuid")
    for table in ("collections", "collection_summaries", "pack_ev",
                  "recommendations", "sync_status", "sync_history"):
        assert all(row["user_id"] == "custom-uuid" for row in custom[table])


def test_sync_rows_absent_files_publish_nulls(rows):
    (status,) = rows["sync_status"]
    assert status["user_id"] == OWNER_USER_ID
    assert status["stats"] is None
    assert status["review_queue"] is None
    assert status["delta"] is None
    assert status["last_run"] is None
    # Explicit so it advances on every publish (the web remote runner's
    # completion baseline).
    assert status["published_at"]
    (entry,) = rows["sync_history"]
    assert entry["synced_at"] == "2026-01-02T03:04:05"


def test_sync_status_carries_the_ci_last_run_marker(artifacts):
    marker = {"finished_at": "2026-07-10T00:00:00+00:00",
              "outcome": "ok", "mode": "live"}
    rows = build_all_rows(artifacts, last_run=marker)
    assert rows["sync_status"][0]["last_run"] == marker


def test_build_last_run_reads_ci_env(monkeypatch):
    monkeypatch.delenv("SYNC_OUTCOME", raising=False)
    assert build_last_run() is None
    monkeypatch.setenv("SYNC_OUTCOME", "auth_expired")
    monkeypatch.setenv("SYNC_MODE", "live")
    marker = build_last_run()
    assert marker["outcome"] == "auth_expired"
    assert marker["mode"] == "live"
    assert marker["finished_at"]


def test_all_tables_have_a_conflict_strategy(rows):
    assert set(rows) == set(TABLE_CONFLICT_KEYS)


# ---------------------------------------------------------------------------
# publish(): idempotent upserts on natural PKs via the client
# ---------------------------------------------------------------------------

def test_publish_upserts_on_natural_pks(rows):
    client = FakeClient()
    publish(client, rows)

    upserts = {t: (r, c) for op, t, r, c in client.log if op == "upsert"}
    assert upserts["cards"][1] == "set_code,card_number"
    assert upserts["packs"][1] == "pack_name"
    assert upserts["collection_summaries"][1] == "user_id"
    assert upserts["sync_history"][1] == "user_id,synced_at"

    # collections is full-replace: delete for the owner, then insert.
    ops = [(op, t) for op, t, _, _ in client.log if t == "collections"]
    assert ops == [("delete", "collections"), ("insert", "collections")]
    delete = next(r for op, t, r, _ in client.log
                  if t == "collections" and op == "delete")
    assert delete == {"user_id": OWNER_USER_ID}


def test_publish_chunks_large_tables(rows):
    big_rows = {"cards": [dict(r) for r in rows["cards"] * 600]}
    client = FakeClient()
    publish(client, big_rows)
    chunks = [r for op, t, r, _ in client.log if op == "upsert"]
    assert len(chunks) == 3  # 1200 rows / 500 per chunk
    assert sum(len(c) for c in chunks) == 1200


def test_supabase_package_not_imported():
    # The builders/publish path must stay importable in CI's minimal env.
    assert "supabase" not in sys.modules


# ---------------------------------------------------------------------------
# recommendation_snapshots: append-only history (Phase 7)
# ---------------------------------------------------------------------------

def test_snapshot_row_bundles_recommendations_and_pack_ev(artifacts):
    rows = build_recommendation_snapshot_rows(
        artifacts["recommendations"], artifacts["pack_ev"], "custom-uuid"
    )
    assert len(rows) == 1
    (row,) = rows
    assert row["user_id"] == "custom-uuid"
    # Byte-identical to the artifacts; captured_at is stamped by Postgres.
    assert row["payload"] == {
        "recommendations": artifacts["recommendations"],
        "pack_ev": artifacts["pack_ev"],
    }
    assert "captured_at" not in row


def test_snapshot_is_not_an_idempotent_table():
    # Append-only: deliberately excluded from the upsert/replace strategy map.
    assert "recommendation_snapshots" not in TABLE_CONFLICT_KEYS


def test_publish_snapshot_inserts_without_delete_or_upsert(artifacts):
    client = FakeClient()
    rows = build_recommendation_snapshot_rows(
        artifacts["recommendations"], artifacts["pack_ev"], OWNER_USER_ID
    )
    publish_recommendation_snapshot(client, rows)
    ops = [(op, t) for op, t, _, _ in client.log]
    assert ops == [("insert", "recommendation_snapshots")]


def test_should_snapshot_skips_republishes(monkeypatch):
    monkeypatch.delenv("SYNC_MODE", raising=False)
    assert should_snapshot() is True  # local manual publish
    monkeypatch.setenv("SYNC_MODE", "live")
    assert should_snapshot() is True  # live CI sync
    monkeypatch.setenv("SYNC_MODE", "skip")
    assert should_snapshot() is False  # push-to-main republish


# ---------------------------------------------------------------------------
# Every published column must exist in the schema
# ---------------------------------------------------------------------------
# Adding a field to a row builder without the matching migration fails only at
# publish time, against the live database, after the run has already rewritten
# collection.json — which is how sync_status.pending_sets shipped and broke the
# first publish of the B4 release with PGRST204.

import re as _re

MIGRATIONS_DIR = ROOT / "supabase" / "migrations"


def _declared_columns() -> dict[str, set[str]]:
    """{table: columns} from CREATE TABLE bodies and ALTER TABLE ADD COLUMN."""
    sql = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS_DIR.glob("*.sql"))
    )
    sql = _re.sub(r"--[^\n]*", "", sql)          # strip comments
    cols: dict[str, set[str]] = {}

    for m in _re.finditer(
        r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?(\w+)\s*\((.*?)\n\s*\);",
        sql, _re.S | _re.I,
    ):
        table, body = m.group(1), m.group(2)
        found = set()
        for line in body.split("\n"):
            line = line.strip().lstrip("(").strip()
            if not line or line.startswith(")"):
                continue
            word = _re.match(r"(\w+)", line)
            if not word:
                continue
            name = word.group(1).lower()
            if name in {"primary", "foreign", "unique", "check", "constraint"}:
                continue
            found.add(name)
        cols.setdefault(table, set()).update(found)

    for m in _re.finditer(
        r"alter\s+table\s+(?:public\.)?(\w+)\s+add\s+column\s+"
        r"(?:if\s+not\s+exists\s+)?(\w+)",
        sql, _re.S | _re.I,
    ):
        cols.setdefault(m.group(1), set()).add(m.group(2).lower())
    return cols


def test_every_published_column_has_a_migration(rows):
    declared = _declared_columns()
    missing: list[str] = []
    for table, table_rows in rows.items():
        if not table_rows:
            continue
        known = declared.get(table)
        assert known, f"no migration creates table {table!r}"
        for column in table_rows[0]:
            if column.lower() not in known:
                missing.append(f"{table}.{column}")
    assert not missing, (
        "publisher writes columns with no migration: "
        f"{sorted(set(missing))} — add one under supabase/migrations/"
    )


def test_column_parser_sees_a_known_late_added_column():
    """Guards the parser itself: last_run arrives via ALTER in 0003, and
    pending_sets via 0009, so both forms must be picked up."""
    declared = _declared_columns()
    assert "last_run" in declared["sync_status"]
    assert "pending_sets" in declared["sync_status"]
    assert "printing_group" in declared["cards"]
    assert "set_code" in declared["cards"]
