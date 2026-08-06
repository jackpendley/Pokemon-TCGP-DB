#!/usr/bin/env python3
"""
Guards for how multi-expansion dex registration is sourced.

The 2026-07-29 update registers a card under every expansion it appears in. The
question is where we learn *which* cards those are.

The first implementation fell back to reprint_links.json, which pairs A4b
printings to their originals by a name+rarity heuristic (245 links, 12 of them
user-confirmed). Measured against the game: it credited 87 of 353 Deluxe Pack: ex
base slots where the app showed 49 and Pokémon Zone's own data showed 27 — about
3x the sourced signal, presented as fact. Ownership is now sourced from PZ's
expansionIds only; being behind a stale upstream is recoverable, being confidently
wrong is not.

    python3 -m pytest tests/test_printing_groups.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_printing_groups as bpg  # noqa: E402


def test_groups_are_not_inferred_from_reprint_links():
    """The structural guard: reprint_links must not be an edge source."""
    assert not hasattr(bpg, "reprint_edges"), (
        "printing groups must be sourced from PZ expansionIds only — see this "
        "module's docstring for what the reprint_links heuristic measured."
    )
    src = (ROOT / "scripts" / "build_printing_groups.py").read_text(encoding="utf-8")
    code = "\n".join(
        l for l in src.splitlines()
        if not l.lstrip().startswith("#") and "reprint" not in l.lower()
        or "reprint" not in l.lower()
    )
    assert "REPRINT_LINKS_JSON" not in code, (
        "build_printing_groups must not read reprint_links.json"
    )


def test_hybrid_pz_coord_resolves_to_both_real_printings(tmp_path, monkeypatch):
    """PZ sends the original's set code with the reprint's number.

    Cubone arrives as A1/194, but A1/194 is Wigglytuff — the real printings are
    A1/151 and A4b/194. Trusting setCode resolves nothing, so the number is
    treated as reliable and the anchor is whichever listed expansion actually
    holds that number under this name.
    """
    records = [
        {"set_code": "A1", "card_number": 151, "name": "Cubone", "rarity": "common"},
        {"set_code": "A1", "card_number": 194, "name": "Wigglytuff", "rarity": "rare"},
        {"set_code": "A4b", "card_number": 194, "name": "Cubone", "rarity": "common"},
    ]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Cubone", "setCode": "A1", "cardNumber": 194,
         "ownedCount": 3, "expansionIds": ["A1", "A4b"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)

    uf = bpg._Union()
    added, unresolved = bpg.pz_edges(uf, records)

    assert (added, unresolved) == (1, 0)
    assert uf.find(("A1", 151)) == uf.find(("A4B", 194))
    # The decoy at the hybrid coord must not be dragged in.
    assert uf.find(("A1", 194)) != uf.find(("A1", 151))


def test_single_expansion_cards_make_no_edges(tmp_path, monkeypatch):
    records = [{"set_code": "B4", "card_number": 1, "name": "Wurmple", "rarity": "common"}]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Wurmple", "setCode": "B4", "cardNumber": 1,
         "ownedCount": 2, "expansionIds": ["B4"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)

    assert bpg.pz_edges(bpg._Union(), records) == (0, 0)


def test_ambiguous_partner_is_skipped_not_guessed(tmp_path, monkeypatch):
    """Two same-rarity candidates in the target expansion: credit neither.

    Guessing here would mark an unowned dex slot owned, which is the exact
    failure mode that made the heuristic unusable.
    """
    records = [
        {"set_code": "A1", "card_number": 151, "name": "Cubone", "rarity": "common"},
        {"set_code": "A4b", "card_number": 194, "name": "Cubone", "rarity": "common"},
        {"set_code": "A4b", "card_number": 195, "name": "Cubone", "rarity": "common"},
    ]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Cubone", "setCode": "A4b", "cardNumber": 151,
         "ownedCount": 1, "expansionIds": ["A4b", "A1"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)

    uf = bpg._Union()
    added, unresolved = bpg.pz_edges(uf, records)
    assert added == 0 and unresolved == 1


def test_non_base_rarities_are_independent_slots(tmp_path, monkeypatch):
    """A full-art printing is its own dex slot on both sides."""
    records = [
        {"set_code": "A1", "card_number": 239, "name": "Cubone",
         "rarity": "illustration_rare"},
        {"set_code": "A4b", "card_number": 400, "name": "Cubone",
         "rarity": "illustration_rare"},
    ]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Cubone", "setCode": "A1", "cardNumber": 239,
         "ownedCount": 1, "expansionIds": ["A1", "A4b"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)

    assert bpg.pz_edges(bpg._Union(), records)[0] == 0


def test_shipped_groups_are_all_pz_sourced():
    """Every shipped group must trace to a multi-expansion PZ record."""
    path = ROOT / "data" / "reference" / "printing_groups.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "reprint_links" not in data["_meta"]["sources"], (
        "printing_groups.json still records a reprint_links edge count"
    )
    for g in data["groups"]:
        assert len(g["coords"]) >= 2, f"{g['id']} is not a real group"
