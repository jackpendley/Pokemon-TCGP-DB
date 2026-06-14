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
    _make_pz("A1",    1,  "Bulbasaur"),   # common, hp=70 regular
    _make_pz("A1",  227,  "Bulbasaur"),   # illustration_rare,    hp=70 alt art
    _make_pz("B1a",   1,  "Bulbasaur"),   # common, hp=60 Tackle art
    # Grovyle — same HP (80), different rarities; alt-art or Pass 3
    _make_pz("B3",    6,  "Grovyle"),     # uncommon
    _make_pz("B3",  157,  "Grovyle"),     # illustration_rare
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


def test_unresolvable_ambiguous_force_matches_with_warning(capsys, pack_sources, ext_ref, collection):
    """An unresolvable ambiguous card is force-matched with a WARN, never raised.

    A single Riolu PZ record with bogus coords can't be disambiguated against the
    multiple Riolu collection entries. The matcher's design is to always ingest every
    PZ card: it force-matches to an unclaimed variant and emits a WARN to stderr
    (so the user can add HP/rarity data to resolve it properly) rather than crashing.
    """
    pz_cards = [_make_pz("FAKE", 999, "Riolu")]
    results = sc.match_pz_cards(pz_cards, collection, pack_sources, ext_ref)
    captured = capsys.readouterr()
    # Never raises, and no AMBIGUOUS result is left unresolved — the card is ingested.
    assert all(r.status != "AMBIGUOUS" for r in results)
    assert len(results) == 1 and results[0].status == "MATCHED"
    # A WARN is surfaced so the root cause (missing disambiguation data) is visible.
    assert "WARN" in captured.err and "Riolu" in captured.err

    # Force-match must land on an actual Riolu collection entry — not some unrelated
    # card. Guards against a regression where force-match picks the wrong index.
    r = results[0]
    assert r.entry is not None and r.entry_index is not None
    assert r.entry is collection[r.entry_index]          # index points at the chosen entry
    assert r.entry.get("name") == "Riolu"                # and it's genuinely a Riolu variant
    assert r.canonical_name == "Riolu"


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
    parsed = json.loads(sc.strip_comments(result))
    names = [e["name"] for e in parsed["collection"]]
    assert "Pikachu" in names
    assert "Bulbasaur" in names


# ---------------------------------------------------------------------------
# 1.4: Fuzzy name matching was intentionally removed from sync_collection.py —
# it picked wrong cards at ≥85% similarity (e.g. "Mega Ampharos ex", "Heracross"),
# which is why the _PROMO_A/_PROMO_B_OVERRIDES exist instead. The former
# test_fuzzy_borderline_logs_debug covered that removed feature and was deleted
# along with the _build_name_list helper that fed it.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 1.6: is_ex type strictness — non-bool is_ex is now a FAILURE not a warning
# ---------------------------------------------------------------------------

def _validate_collection_data(data):
    meta_total = data.get("meta", {}).get("total_cards", 0)
    failures, warnings, _, _ = vc.validate(data, meta_total)
    return failures, warnings


# Note: is_ex is no longer a tracked field on collection entries (it is stripped
# by assign_collection_coords.py before validation, and EX status is derived from
# rarity / the " ex" name suffix). The former test_is_ex_* validation tests were
# removed when the field was dropped from the schema.


# ---------------------------------------------------------------------------
# Dual-location pairing: aggregated multi-set counts must survive pairing
# ---------------------------------------------------------------------------

_PAIR_LINKS = {("A4B", 10): ("A1", 5)}  # A4b 10 reprints A1 5


def _pair_entries(orig_count=2, a4b_count=2):
    return [
        {"name": "Shroomish", "set_code": "A1",  "card_number": 5,  "count": orig_count},   # 0: original slot
        {"name": "Shroomish", "set_code": "A4B", "card_number": 10, "count": a4b_count},     # 1: A4b slot
    ]


def test_pairing_leaves_counts_alone_when_pair_sums():
    """One PZ record on the pair's own coord, counts already split correctly."""
    entries = _pair_entries()
    totals = {0: 4}
    coords = {0: {("A1", 5)}}
    paired = sc.pair_dual_location_entries(entries, totals, coords, {0}, _PAIR_LINKS)
    assert paired == {1}
    assert totals[0] == 2  # reset to entry's own count; sibling holds the rest


def test_pairing_fires_on_pz_hybrid_stamp():
    """Regression (the 1261 bug): Pokémon Zone stamps a dual-location card with the
    ORIGINAL set code + the A4b card number — Shroomish here arrives as A1/10, not
    A1/5 or A4B/10. The matcher lands the full count (3) on the original entry; the
    A4b sibling (count 2) gets no PZ record. Pairing MUST still fire (1 + 2 == 3),
    or sync keeps the full 3 on the original AND preserves the A4b 2 → over-counts.
    """
    entries = _pair_entries(orig_count=1, a4b_count=2)
    totals = {0: 3}                       # full PZ hybrid count landed on the original
    coords = {0: {("A1", 10)}}            # hybrid stamp: original set A1 + A4b number 10
    paired = sc.pair_dual_location_entries(entries, totals, coords, {0}, _PAIR_LINKS)
    assert paired == {1}                  # A4b sibling paired, not flagged missing
    assert totals[0] == 1                 # original keeps 1; 1 + sibling 2 == PZ 3


def test_pairing_fires_on_hybrid_stamp_from_a4b_side():
    """The matcher may land the PZ record on the A4b entry instead of the original.
    The hybrid coord (original set + A4b number) must be accepted from that side too."""
    entries = _pair_entries(orig_count=1, a4b_count=2)
    totals = {1: 3}                       # full count landed on the A4b entry (idx 1)
    coords = {1: {("A1", 10)}}            # same hybrid stamp
    paired = sc.pair_dual_location_entries(entries, totals, coords, {1}, _PAIR_LINKS)
    assert paired == {0}                  # original paired
    assert totals[1] == 2                 # A4b keeps 2; 2 + original 1 == PZ 3


def test_pairing_skipped_when_copy_from_other_set_aggregated():
    """A copy aggregated from a genuinely foreign set (e.g. B3) must not be
    discarded by the pairing reset just because the pair's counts happen to
    sum to the aggregate."""
    entries = _pair_entries()
    # PZ: A1 ×2 + B3 ×1 + A4B ×1 → aggregate 4 on entry 0; pair counts 2+2 == 4
    totals = {0: 4}
    coords = {0: {("A1", 5), ("B3", 77), ("A4B", 10)}}
    paired = sc.pair_dual_location_entries(entries, totals, coords, {0}, _PAIR_LINKS)
    assert paired == set()      # no pairing — B3 copy is real
    assert totals[0] == 4       # aggregate preserved, not reset to 2


def _real_dual_location_link():
    """Pick a real dual-location link whose A4b number differs from its original
    number, so the hybrid stamp (original_set + A4b number) is a DISTINCT coord
    from the original — the only shape that exercises the 1261 over-count. Returns
    (name, a4b_coord, original_coord) or None."""
    from pathlib import Path as _Path
    lp = _Path(__file__).resolve().parent.parent / "data" / "reference" / "reprint_links.json"
    if not lp.exists():
        return None
    for l in json.loads(lp.read_text(encoding="utf-8")).get("links", []):
        a4b = (str(l["a4b"][0]).upper(), int(l["a4b"][1]))
        orig = (str(l["original"][0]).upper(), int(l["original"][1]))
        if a4b[1] != orig[1]:                 # hybrid (orig_set, a4b_num) != original coord
            return l.get("name"), a4b, orig
    return None


def test_pz_hybrid_stamp_end_to_end_count_integrity():
    """End-to-end guard against the 1261 regression, self-contained (no fixtures).

    Builds a tiny collection where a real dual-location card is already split
    (original slot + A4b slot), then replays a Pokémon Zone snapshot that stamps
    the card with the ORIGINAL set code + A4b number (the real-world hybrid). The
    post-sync collection total MUST equal the PZ total — the broken guard left the
    full count on the original AND preserved the A4b half, inflating the total.
    """
    link = _real_dual_location_link()
    if link is None:
        import pytest
        pytest.skip("no reprint_links.json with links")
    name, (a4b_set, a4b_num), (orig_set, orig_num) = link

    collection = [
        {"name": name, "set_code": orig_set, "card_number": orig_num, "count": 1, "card_type": "Pokemon"},
        {"name": name, "set_code": a4b_set,  "card_number": a4b_num,  "count": 2, "card_type": "Pokemon"},
    ]
    # PZ stamps the dual card once, as (original_set, a4b_number), count 3.
    pz_raw = [{"cardName": name, "setCode": orig_set, "cardNumber": a4b_num, "ownedCount": 3}]

    pack_sources = sc.load_pack_sources()
    ext_ref = sc.load_ext_ref()
    pz_cards = [p for p in (sc.normalize_pz_record(r) for r in pz_raw) if p]
    pz_total = sum(p.count for p in pz_cards)

    results = sc.match_pz_cards(pz_cards, collection, pack_sources, ext_ref)
    matched = [r for r in results if r.status == "MATCHED"]
    new = [r for r in results if r.status == "NEW_CARD"]
    matched_indices = {r.entry_index for r in matched if r.entry_index is not None}

    entry_pz_total, entry_pz_coords = {}, {}
    for r in matched:
        i = r.entry_index
        entry_pz_total[i] = entry_pz_total.get(i, 0) + r.pz_card.count
        entry_pz_coords.setdefault(i, set()).add(
            (str(r.pz_card.set_code or "").upper(), r.pz_card.card_number))

    link_orig = {(a4b_set, a4b_num): (orig_set, orig_num)}
    paired = sc.pair_dual_location_entries(
        collection, entry_pz_total, entry_pz_coords, matched_indices, link_orig)

    missing = [i for i in range(len(collection))
               if i not in matched_indices and i not in paired]
    post_sync_total = (
        sum(entry_pz_total.values())
        + sum(collection[j].get("count", 0) for j in paired)
        + sum(collection[i].get("count", 0) for i in missing)
        + sum(r.pz_card.count for r in new)
    )
    assert post_sync_total == pz_total, (
        f"sync total {post_sync_total} != PZ total {pz_total} "
        f"(delta {post_sync_total - pz_total}) — dual-location hybrid pairing regressed")


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
