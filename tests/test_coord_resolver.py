"""
Tests for coord_resolver.py — covers the paths that were tricky to get right.

Uses no network (fetch=False) and a minimal card_reference / pack_sources
dict injected via monkeypatching so tests run offline and fast.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from coord_resolver import CoordResolver, ResolvedCoord, _name_agrees


# ---------------------------------------------------------------------------
# _name_agrees unit tests
# ---------------------------------------------------------------------------

def test_name_agrees_exact():
    assert _name_agrees("Pikachu", "Pikachu")

def test_name_agrees_accent_fold():
    # NFKD normalization via norm_card_name in _collection_io
    assert _name_agrees("Flabébé", "Flabebe")

def test_name_agrees_forme_stripped():
    assert _name_agrees("Zygarde 10% Forme", "Zygarde")
    assert _name_agrees("Zygarde", "Zygarde 50% Forme")

def test_name_disagrees():
    assert not _name_agrees("Charizard", "Pikachu")

def test_name_agrees_ex_not_stripped():
    # ' ex' suffix must NOT be stripped — base vs EX are distinct cards
    assert not _name_agrees("Charizard", "Charizard ex")
    assert not _name_agrees("Charizard ex", "Charizard")


# ---------------------------------------------------------------------------
# ResolvedCoord construction — every keyword argument must be valid
# ---------------------------------------------------------------------------

def test_resolved_coord_all_fields():
    rc = ResolvedCoord(
        name="Bulbasaur",
        set_code="A1",
        card_number=1,
        rarity="one_diamond",
        confidence="confirmed",
        sources_agreed=["card_reference", "tcgdex"],
        detail="test",
    )
    assert rc.sources_agreed == ["card_reference", "tcgdex"]
    assert rc.detail == "test"


def test_resolved_coord_defaults():
    rc = ResolvedCoord("Bulbasaur", "A1", 1, None, "unconfirmed")
    assert rc.sources_agreed == []
    assert rc.detail == ""


# ---------------------------------------------------------------------------
# CoordResolver with injected card_reference — collision / conflict paths
# ---------------------------------------------------------------------------

class _PatchedResolver(CoordResolver):
    """CoordResolver that replaces the reference indexes with test data."""

    def __init__(self, ref_records, ps_records, fetch=False):
        # Bypass __init__ file reads by calling object.__init__ then wiring
        # only what resolve() / _coord_from_ref need.
        object.__init__(self)
        self.fetch = fetch
        self._dirty_td = False
        self._dirty_ll = False
        self.tcgdex_cache = {}
        self.limitless_cache = {}
        self._fetched_sets: dict = {}
        self.tcgdex_sets: set = set()

        from _collection_io import norm_card_name as _norm
        # Build pack_sources indexes
        self.ps_by_coord = {}
        self.ps_name_num = {}
        for r in ps_records:
            s = str(r.get("set_code") or "").upper().strip()
            try:
                n = int(r.get("card_number"))
            except (TypeError, ValueError):
                continue
            self.ps_by_coord[(s, n)] = r
            self.ps_name_num.setdefault((_norm(r.get("card_name", "")), n), []).append(s)

        # Build card_reference indexes
        self.ref_by_coord = {}
        self.ref_name_num = {}
        for r in ref_records:
            sc = str(r.get("set_code") or "").upper().strip()
            try:
                cn = int(r.get("card_number"))
            except (TypeError, ValueError):
                continue
            self.ref_by_coord[(sc, cn)] = r
            self.ref_name_num.setdefault((_norm(r.get("name", "")), cn), []).append((sc, cn))


def _ref_rec(set_code, card_number, name, confidence="confirmed"):
    return {
        "set_code": set_code,
        "card_number": card_number,
        "name": name,
        "rarity": "one_diamond",
        "confidence": confidence,
        "confirmations": ["tcgdex"],
        "conflict_notes": [],
    }


def _ps_rec(set_code, card_number, card_name, rarity="one_diamond"):
    return {
        "set_code": set_code,
        "card_number": card_number,
        "card_name": card_name,
        "rarity": rarity,
        "pack_name": None,
    }


# ── Path 1a: exact-coord hit ──────────────────────────────────────────────

def test_exact_coord_confirmed():
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("A1", 1, "Bulbasaur")],
        ps_records=[_ps_rec("A1", 1, "Bulbasaur")],
    )
    rc = resolver.resolve("Bulbasaur", "A1", 1)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A1"
    assert rc.card_number == 1


# ── Path 1b single: name+number unambiguous in reference ─────────────────

def test_name_number_corrects_pz_mislabel():
    # PZ says A1, but card is really in A4b — reference has A4b only.
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("A4b", 1, "Bulbasaur")],
        ps_records=[_ps_rec("A4b", 1, "Bulbasaur")],
    )
    rc = resolver.resolve("Bulbasaur", "A1", 1)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A4b"  # corrected from PZ's "A1"


# ── Path 1b multiple: collision → PZ tiebreaker ───────────────────────────

def test_collision_pz_set_tiebreaker():
    # Bulbasaur #1 appears in A1 and A4b; PZ says A1 → A1 should win.
    resolver = _PatchedResolver(
        ref_records=[
            _ref_rec("A1", 1, "Bulbasaur"),
            _ref_rec("A4b", 1, "Bulbasaur"),
        ],
        ps_records=[],
    )
    rc = resolver.resolve("Bulbasaur", "A1", 1)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A1"


def test_collision_no_pz_tiebreaker_returns_conflict_not_crash():
    """The crash case: name+number in 2+ sets, PZ set_code not in reference at that number.

    Before fix #1 this raised TypeError: ResolvedCoord() got unexpected keyword 'sources'.
    After fix it must return a conflict ResolvedCoord without raising.
    """
    resolver = _PatchedResolver(
        ref_records=[
            _ref_rec("A1", 1, "Bulbasaur"),
            _ref_rec("A4b", 1, "Bulbasaur"),
        ],
        ps_records=[],
    )
    # PZ says "B3A" which has no Bulbasaur/1 in reference → tiebreaker fails
    rc = resolver.resolve("Bulbasaur", "B3A", 1)
    assert rc.confidence == "conflict"
    assert rc.set_code is None
    assert "card_reference" in rc.sources_agreed


# ── Path 1a: exact coord but name disagrees → conflict (not silent fallthrough) ──

def test_exact_coord_name_mismatch_returns_conflict():
    """Reference says Charizard at A1/1 but PZ sends Pikachu — must conflict, not trust PZ."""
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("A1", 1, "Charizard")],
        ps_records=[_ps_rec("A1", 1, "Charizard")],
    )
    rc = resolver.resolve("Pikachu", "A1", 1)
    assert rc.confidence == "conflict"
    assert "Charizard" in rc.detail


# ── No card_number: unconfirmed ───────────────────────────────────────────

def test_no_card_number():
    resolver = _PatchedResolver(ref_records=[], ps_records=[])
    rc = resolver.resolve("Pikachu", "A1", None)
    assert rc.confidence == "unconfirmed"


# ── Fallback path: card not in reference, in pack_sources ─────────────────

def test_fallback_single_pack_source():
    resolver = _PatchedResolver(
        ref_records=[],   # card absent from reference
        ps_records=[_ps_rec("A1", 25, "Pikachu")],
    )
    rc = resolver.resolve("Pikachu", "A1", 25)
    # Should use fallback, land on single-source (no independent confirmation)
    assert rc.confidence in ("single-source", "confirmed", "unconfirmed")
    assert rc.set_code == "A1"
