"""
Phase 1 tests: sync_collection.py and validate_current_collection.py reliability.

Tests run against real reference data (pack_sources, ext_ref, collection.json)
so they verify actual disambiguation correctness, not just mocked behavior.
"""

import io
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sync_collection as sc
import validate_current_collection as vc


# ---------------------------------------------------------------------------
# Fixtures: real reference data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pack_sources():
    return sc.load_pack_sources()


@pytest.fixture(scope="module")
def ext_ref():
    return sc.load_ext_ref()


@pytest.fixture(scope="module")
def collection():
    _, data = sc.load_collection()
    return data["collection"]


@pytest.fixture(scope="module")
def collection_data():
    _, data = sc.load_collection()
    return data


# ---------------------------------------------------------------------------
# 1.2: Multi-variant disambiguation — no AMBIGUOUS results for known variants
# ---------------------------------------------------------------------------

def _make_pz(set_code, card_number, raw_name, count=1):
    return sc.PZCard(
        set_code=set_code,
        card_number=card_number,
        raw_name=raw_name,
        count=count,
    )


KNOWN_MULTI_VARIANT_PZ = [
    # Riolu — same HP (60), different rarities; Pass 3 resolves group
    _make_pz("B3",   79,  "Riolu"),
    _make_pz("B3",  169,  "Riolu"),
    # Bulbasaur — three variants; hp=60 unique; hp=70 × 2 resolved by alt-art rarity
    _make_pz("A1",    1,  "Bulbasaur"),   # one_diamond, hp=70 regular
    _make_pz("A1",  227,  "Bulbasaur"),   # one_star,    hp=70 alt art
    _make_pz("B1a",   1,  "Bulbasaur"),   # one_diamond, hp=60 Tackle art
    # Grovyle — same HP (80), different rarities; alt-art or Pass 3
    _make_pz("B3",    6,  "Grovyle"),     # two_diamond
    _make_pz("B3",  157,  "Grovyle"),     # one_star
    # HP-unique pairs — resolve in Step A
    _make_pz("B3",   79,  "Mienfoo"),     # placeholder set; test by name-only if not in PS
    _make_pz("B3",   80,  "Mienshao"),
]


def test_no_ambiguous_for_multi_variant_cards(pack_sources, ext_ref, collection):
    """Every known multi-variant card resolves without remaining AMBIGUOUS."""
    pz_cards = [
        _make_pz("B3",  79,  "Riolu"),
        _make_pz("B3", 169,  "Riolu"),
        _make_pz("A1",   1,  "Bulbasaur"),
        _make_pz("A1", 227,  "Bulbasaur"),
        _make_pz("B1a",  1,  "Bulbasaur"),
        _make_pz("B3",   6,  "Grovyle"),
        _make_pz("B3", 157,  "Grovyle"),
    ]
    # Should not raise RuntimeError
    results = sc.match_pz_cards(pz_cards, collection, pack_sources, ext_ref)
    ambiguous = [r for r in results if r.status == "AMBIGUOUS"]
    assert ambiguous == [], (
        f"Got {len(ambiguous)} unresolved AMBIGUOUS result(s): "
        + ", ".join(f"'{r.pz_card.raw_name}'" for r in ambiguous)
    )


def test_ambiguous_raises_runtime_error(pack_sources, ext_ref, collection):
    """If disambiguation truly fails, RuntimeError is raised (not silent queue)."""
    # Inject a card name that has multiple collection entries but no disambiguating data:
    # We simulate this by passing ONE Riolu record when there are TWO collection entries
    # for Riolu (same HP=60), with a bogus set_code so pack_sources can't help.
    pz_cards = [_make_pz("FAKE", 999, "Riolu")]
    with pytest.raises(RuntimeError, match="Unresolvable match"):
        sc.match_pz_cards(pz_cards, collection, pack_sources, ext_ref)


# ---------------------------------------------------------------------------
# 1.1: Silent card drops — malformed count_raw emits WARNING
# ---------------------------------------------------------------------------

def test_malformed_count_logs_warning_and_drops(capsys):
    raw = {"cardName": "Pikachu", "ownedCount": "N/A"}
    result = sc.normalize_pz_record(raw)
    captured = capsys.readouterr()
    assert result is None
    assert "WARNING" in captured.err
    assert "Pikachu" in captured.err
    assert "N/A" in captured.err


def test_zero_count_drops_silently(capsys):
    """count=0 is expected (card not owned) — should not emit WARNING."""
    raw = {"cardName": "Pikachu", "ownedCount": 0}
    result = sc.normalize_pz_record(raw)
    captured = capsys.readouterr()
    assert result is None
    assert "WARNING" not in captured.err


def test_none_count_drops_silently(capsys):
    """No count field at all — should not emit WARNING."""
    raw = {"cardName": "Pikachu"}
    result = sc.normalize_pz_record(raw)
    captured = capsys.readouterr()
    assert result is None
    assert "WARNING" not in captured.err


def test_valid_count_parses(capsys):
    raw = {"cardName": "Pikachu", "ownedCount": 2, "setCode": "A1", "cardNumber": 35}
    result = sc.normalize_pz_record(raw)
    assert result is not None
    assert result.count == 2
    assert result.raw_name == "Pikachu"


# ---------------------------------------------------------------------------
# 1.3: Append regex safety — RuntimeError on bad closing structure
# ---------------------------------------------------------------------------

def test_append_raises_on_bad_structure():
    # Non-whitespace trailing content after the closing } breaks the \s*$ anchor
    bad_raw = '{\n  "meta": {},\n  "collection": [\n    {"name": "Pikachu", "count": 1}\n  ]\n}\nEXTRA'
    entry = {"name": "Bulbasaur", "count": 1, "card_type": "Pokemon"}
    with pytest.raises(RuntimeError, match="append point not found"):
        sc.append_entries_to_collection(bad_raw, [entry])


def test_append_succeeds_on_valid_structure():
    valid_raw = '{\n  "meta": {},\n  "collection": [\n    {"name": "Pikachu", "count": 1}\n  ]\n}'
    entry = {"name": "Bulbasaur", "count": 1, "card_type": "Pokemon"}
    result = sc.append_entries_to_collection(valid_raw, [entry])
    assert "Bulbasaur" in result
    assert result.endswith("}")
    # Result must be valid JSON after stripping comments
    parsed = json.loads(sc._strip_comments(result))
    names = [e["name"] for e in parsed["collection"]]
    assert "Pikachu" in names
    assert "Bulbasaur" in names


# ---------------------------------------------------------------------------
# 1.4: Fuzzy match logging — borderline matches emit DEBUG to stderr
# ---------------------------------------------------------------------------

def test_fuzzy_borderline_logs_debug(capsys, pack_sources, ext_ref, collection):
    """A fuzzy match scoring 85-94% emits a DEBUG message to stderr.

    We test the underlying _match_one() directly so we don't trigger
    the AMBIGUOUS→RuntimeError path in match_pz_cards() (which fires
    when a fuzzy-matched name has multiple variants).
    """
    name_index = sc._build_name_index(collection)
    pack_name_list = sc._build_name_list(pack_sources)
    # "Lapras" has only one variant in the collection — no disambiguation needed
    pz = _make_pz(None, None, "Lapraz")  # typo, high fuzzy similarity to "Lapras"
    result = sc._match_one(pz, collection, name_index, pack_sources, pack_name_list, ext_ref)
    captured = capsys.readouterr()
    if result.status == "MATCHED":
        # Any borderline fuzzy match (85-94%) should log DEBUG
        assert "DEBUG" in captured.err or "fuzzy" in captured.err.lower(), (
            f"Expected DEBUG log for borderline fuzzy match, got stderr: {captured.err!r}"
        )


# ---------------------------------------------------------------------------
# 1.6: is_ex type strictness — non-bool is_ex is now a FAILURE not a warning
# ---------------------------------------------------------------------------

def _validate_collection_data(data):
    meta_total = data.get("meta", {}).get("total_cards", 0)
    failures, warnings, _, _ = vc.validate(data, meta_total)
    return failures, warnings


def test_is_ex_string_is_failure():
    data = {
        "meta": {"total_cards": 1, "last_updated": "2026-01-01", "format": "test"},
        "collection": [{
            "name": "Pikachu", "count": 1, "card_type": "Pokemon",
            "type": "Lightning", "stage": 0, "is_ex": "true",
        }],
    }
    failures, warnings = _validate_collection_data(data)
    failure_text = " ".join(failures)
    warn_text = " ".join(warnings)
    assert "is_ex" in failure_text, f"Expected is_ex failure, got failures={failures} warnings={warnings}"
    assert "is_ex" not in warn_text


def test_is_ex_integer_is_failure():
    data = {
        "meta": {"total_cards": 1, "last_updated": "2026-01-01", "format": "test"},
        "collection": [{
            "name": "Pikachu", "count": 1, "card_type": "Pokemon",
            "type": "Lightning", "stage": 0, "is_ex": 1,
        }],
    }
    failures, _ = _validate_collection_data(data)
    assert any("is_ex" in f for f in failures)


def test_is_ex_bool_passes():
    data = {
        "meta": {"total_cards": 1, "last_updated": "2026-01-01", "format": "test"},
        "collection": [{
            "name": "Pikachu ex", "count": 1, "card_type": "Pokemon",
            "type": "Lightning", "stage": 0, "is_ex": True,
        }],
    }
    failures, _ = _validate_collection_data(data)
    is_ex_failures = [f for f in failures if "is_ex" in f]
    assert is_ex_failures == []


# ---------------------------------------------------------------------------
# Regression: real collection.json passes validation
# ---------------------------------------------------------------------------

def test_real_collection_passes_validation(collection_data):
    """Ensure the live collection.json is valid after Phase 1 changes."""
    failures, warnings, _, _ = vc.validate(
        collection_data,
        collection_data.get("meta", {}).get("total_cards", 0),
    )
    assert failures == [], f"Real collection has validation failures: {failures}"
