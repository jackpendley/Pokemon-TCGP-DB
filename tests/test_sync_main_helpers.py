"""
Tests for the phase helpers extracted from sync_collection.main().

main() requires PZ auth and so was never unit-tested; these cover the pure
phase functions split out of it (arg parsing, the import-mode dispatch, and PZ
record normalisation) so the decomposition has real coverage.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sync_collection as sc


# ── _build_arg_parser ────────────────────────────────────────────────────────

def test_arg_parser_defaults():
    args = sc._build_arg_parser().parse_args([])
    assert args.json_import is None and args.har_import is None
    assert args.dry_run is False and args.force is False and args.no_fetch is False


def test_arg_parser_flags():
    args = sc._build_arg_parser().parse_args(["--dry-run", "--force", "--no-fetch"])
    assert args.dry_run and args.force and args.no_fetch


def test_arg_parser_json_import_value():
    args = sc._build_arg_parser().parse_args(["--json-import", "cards.json"])
    assert args.json_import == "cards.json"


# ── _normalize_pz_records ────────────────────────────────────────────────────

def test_normalize_drops_unparseable(monkeypatch):
    # Stub normalize_pz_record so we test the filter (skip None) in isolation.
    seq = {"good": "PZC", "bad": None}
    monkeypatch.setattr(sc, "normalize_pz_record", lambda rec: seq[rec["k"]])
    out = sc._normalize_pz_records([{"k": "good"}, {"k": "bad"}, {"k": "good"}])
    assert out == ["PZC", "PZC"]


# ── _acquire_raw_cards (--json-import branch; no PZ network needed) ───────────

def _fake_pz(tmp_path):
    # _acquire reads pz.AUTH_CACHE; the json-import branch never touches the network.
    return SimpleNamespace(AUTH_CACHE=tmp_path / "auth.json")


def _args(**over):
    base = dict(json_import=None, har_import=None, curl_file=None, curl_import=False,
                login=False, discover=False, dry_run=False, force=False, no_fetch=False)
    base.update(over)
    return SimpleNamespace(**base)


def test_acquire_json_import_success(tmp_path):
    p = tmp_path / "cards.json"
    p.write_text(json.dumps([{"name": "Pikachu", "count": 2}]))
    cards, early = sc._acquire_raw_cards(_args(json_import=str(p)), _fake_pz(tmp_path))
    assert early is None
    assert cards == [{"name": "Pikachu", "count": 2}]


def test_acquire_json_import_missing_file(tmp_path):
    cards, early = sc._acquire_raw_cards(
        _args(json_import=str(tmp_path / "nope.json")), _fake_pz(tmp_path))
    assert cards is None and early == 1


def test_acquire_json_import_not_a_list(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"not": "a list"}))
    cards, early = sc._acquire_raw_cards(_args(json_import=str(p)), _fake_pz(tmp_path))
    assert cards is None and early == 1
