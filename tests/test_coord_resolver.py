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
        rarity="common",
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
        "rarity": "common",
        "confidence": confidence,
        "confirmations": ["tcgdex"],
        "conflict_notes": [],
    }


def _ps_rec(set_code, card_number, card_name, rarity="common"):
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


# ── Path 1a: name-agreeing PZ coord is trusted despite multi-set collision ──

def test_collision_trusts_name_agreeing_pz_coord():
    """A name+number collision across sets resolves to PZ's coord when the reference
    name agrees there. For dual-location A4b reprints PZ's set_code is the ORIGINAL
    set — the app's dex attribution (user-verified in-app 2026-06-12) — so the
    original-set slot is the right answer either way."""
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
    assert rc.card_number == 1


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


# ── Path 1a: name MISMATCH at PZ coord still falls to 1b (hybrid coords) ─────────

def test_exact_coord_name_mismatch_resolves_by_name_number():
    """A hybrid PZ coord (original set code + A4b number) where a DIFFERENT card sits
    at that coord must resolve by name+number, not conflict — e.g. Greninja exported
    as A1/114 where A1/114 is really Clefable but (Greninja, 114) lives at A4b/114."""
    resolver = _PatchedResolver(
        ref_records=[
            _ref_rec("A1",  114, "Clefable"),
            _ref_rec("A4b", 114, "Greninja"),
        ],
        ps_records=[],
    )
    rc = resolver.resolve("Greninja", "A1", 114)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A4b"
    assert rc.card_number == 114


def test_name_number_single_set_uses_1b_path():
    """When (name, number) uniquely maps to one set, path 1b corrects PZ's set_code.

    Note: this test exercises path 1b (name+number lookup), not path 1a (exact coord).
    Path 1a requires PZ's set_code to match the reference's set_code.
    """
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("Pikachu", 35, "Pikachu")],
        ps_records=[],
    )
    # PZ says A1 but the reference only has this card in set "Pikachu" — 1b corrects it
    rc = resolver.resolve("Pikachu", "A1", 35)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "Pikachu"  # set_code from the ref record (corrected from A1)


def test_exact_coord_single_set_fast_path():
    """When PZ's set_code matches the reference AND the card is in exactly one set,
    path 1a (exact coord + single ref_cands) confirms without any network call."""
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("A1", 35, "Pikachu")],
        ps_records=[],
    )
    # PZ says A1, reference has this card only in A1 → path 1a fast-path fires
    rc = resolver.resolve("Pikachu", "A1", 35)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A1"


# ── Path 1a: exact coord but name disagrees → conflict (not silent fallthrough) ──

def test_exact_coord_name_mismatch_returns_conflict():
    """Reference says Charizard at A1/1 but PZ sends Pikachu — must conflict, not trust PZ.

    Here the PZ name (Pikachu) exists nowhere at number 1, so there is no hybrid coord to
    recover — a genuine conflict.
    """
    resolver = _PatchedResolver(
        ref_records=[_ref_rec("A1", 1, "Charizard")],
        ps_records=[_ps_rec("A1", 1, "Charizard")],
    )
    rc = resolver.resolve("Pikachu", "A1", 1)
    assert rc.confidence == "conflict"
    assert "Charizard" in rc.detail


# ── PZ hybrid coord: different card at PZ coord, but (name, number) recovers it ──

def test_pz_hybrid_coord_resolves_to_a4b():
    """PZ emits A4b reprints as <original set_code>/<A4b number>, a hybrid that points at a
    different real card. The Greninja case: PZ sends A1/114, but A1/114 is Clefable while
    (Greninja, 114) uniquely lives at A4b/114. The resolver must recover A4b/114 at full
    confidence rather than declaring a conflict and routing it to the review queue."""
    resolver = _PatchedResolver(
        ref_records=[
            _ref_rec("A1", 114, "Clefable"),
            _ref_rec("A4b", 114, "Greninja"),
        ],
        ps_records=[],
    )
    rc = resolver.resolve("Greninja", "A1", 114)
    assert rc.confidence == "confirmed"
    assert rc.set_code == "A4b"
    assert rc.card_number == 114


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
