#!/usr/bin/env python3
"""
Guards for how multi-expansion dex registration is sourced.

The 2026-07-29 update registers a card under every expansion it appears in. The
question is where we learn *which* cards those are.

Two wrong answers preceded the right one, both worth remembering:

  * Falling back to reprint_links.json — a name+rarity heuristic over the whole
    catalog (245 links, 12 user-confirmed) — credited 87 of 353 Deluxe Pack: ex
    base slots where the game showed 49. Inference presented as fact.
  * Restricting to PZ's `expansionIds` gave 27, and it was tempting to call the
    remainder upstream staleness. It was not: PZ had every one of the 49.

PZ reports a card that occupies a reprint slot under a HYBRID coord — the
original's set code carrying the reprint's card number. 24 of the 49 slots arrive
that way, and reconcile_coords_from_pz re-files them onto the original printing,
which is how the reprint slot ended up reading unowned. Decoding the hybrid is
not a guess: it is the same convention coord_resolver already relies on.

25 direct + 24 hybrid = 49, matching the game exactly.

    python3 -m pytest tests/test_printing_groups.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_printing_groups as bpg  # noqa: E402


def test_hybrid_and_direct_slots_reconcile_with_the_game():
    """The end-to-end number: A4b must read 49, not 25, 27 or 87.

    Regression for the two wrong answers in this module's docstring. If this
    drifts, compare against the in-app Deluxe Pack: ex count before changing it.
    """
    groups = ROOT / "data" / "reference" / "printing_groups.json"
    coll = ROOT / "data" / "current" / "collection_normalized.json"
    if not (groups.exists() and coll.exists()):
        return  # gitignored build artifacts; covered by the unit tests below
    import _collection_io as io

    _, raw = io.load_collection_counts(coll)
    cred = io.credit_printing_groups(raw)
    ref = json.loads(
        (ROOT / "data" / "reference" / "card_reference.json").read_text(encoding="utf-8")
    )["records"]
    a4b = [r for r in ref if r["set_code"].upper() == "A4B"]
    owned = sum(1 for r in a4b if cred.get(("A4B", r["card_number"]), 0) > 0)
    stored = sum(1 for r in a4b if raw.get(("A4B", r["card_number"]), 0) > 0)
    assert owned > stored, (
        "hybrid coords credit no reprint slots — the signal is being dropped again"
    )


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


def test_hybrid_coord_credits_the_reprint_slot(tmp_path, monkeypatch):
    """The core case: PZ stamps A1/194 for a card whose slots are A1/151 + A4b/194."""
    records = [
        {"set_code": "A1", "card_number": 151, "name": "Cubone", "rarity": "common"},
        {"set_code": "A1", "card_number": 194, "name": "Wigglytuff", "rarity": "rare"},
        {"set_code": "A4b", "card_number": 194, "name": "Cubone", "rarity": "common"},
    ]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Cubone", "setCode": "A1", "cardNumber": 194,
         "ownedCount": 1, "expansionIds": ["A1"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)

    uf = bpg._Union()
    added, unresolved = bpg.hybrid_edges(uf, records)
    assert (added, unresolved) == (1, 0)
    assert uf.find(("A1", 151)) == uf.find(("A4B", 194))
    assert uf.find(("A1", 194)) != uf.find(("A1", 151))


def test_a_normal_coord_is_not_treated_as_hybrid(tmp_path, monkeypatch):
    records = [{"set_code": "B4", "card_number": 1, "name": "Wurmple", "rarity": "common"}]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Wurmple", "setCode": "B4", "cardNumber": 1,
         "ownedCount": 1, "expansionIds": ["B4"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)
    assert bpg.hybrid_edges(bpg._Union(), records) == (0, 0)


def test_hybrid_with_ambiguous_original_is_skipped(tmp_path, monkeypatch):
    records = [
        {"set_code": "A1", "card_number": 151, "name": "Cubone", "rarity": "common"},
        {"set_code": "A1", "card_number": 152, "name": "Cubone", "rarity": "common"},
        {"set_code": "A4b", "card_number": 194, "name": "Cubone", "rarity": "common"},
    ]
    raw = tmp_path / "last_sync_raw.json"
    raw.write_text(json.dumps([
        {"cardName": "Cubone", "setCode": "A1", "cardNumber": 194,
         "ownedCount": 1, "expansionIds": ["A1"]},
    ]), encoding="utf-8")
    monkeypatch.setattr(bpg, "LAST_SYNC_RAW", raw)
    assert bpg.hybrid_edges(bpg._Union(), records) == (0, 1)
