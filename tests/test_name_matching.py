#!/usr/bin/env python3
"""
Guards for the card-name normalizer the sync matcher uses.

History, because this problem has been patched around more than once:

  * `norm_card_name` is the cross-source card-name matcher. It was hardened in
    da3966d specifically so Nidoran♀/♂ survive normalization (♀→f, ♂→m *before*
    stripping) and so accents fold (Flabébé ≡ Flabebe).
  * `field_slug` is a key-slug helper. It maps every non-alphanumeric to "_",
    which both KEEPS internal spacing and COLLAPSES ♀/♂. Its own docstring says
    it "MUST NOT be used to build a lookup that must distinguish the two
    variants".
  * sync_collection nonetheless imported `field_slug as _normalize` and used it
    as the card-name matcher. Two consequences, both live:
      - Pokémon Zone used to emit run-together names ("CastformSunny Form") and
        later corrected them. Stored entries kept the old spelling, so the two
        never matched: every sync re-added 12 "new" cards and flagged the 12
        originals missing, incrementing consecutive_missing toward
        _STALE_THRESHOLD = 3, i.e. deleting 31 real copies.
      - Nidoran♀ and Nidoran♂ shared one key, which
        test_new_card_phase4 works around by comparing raw names instead.

The fix was to use the function that already existed for this, not to write a
third normalizer. These tests pin that choice.

    python3 -m pytest tests/test_name_matching.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io  # noqa: E402
import sync_collection as sc  # noqa: E402

CARD_REF = ROOT / "data" / "reference" / "card_reference.json"


def _reference_names() -> set[str]:
    records = json.loads(CARD_REF.read_text(encoding="utf-8"))["records"]
    return {r["name"] for r in records}


# ---------------------------------------------------------------------------
# The matcher must use the card-name normalizer, not the key-slug helper
# ---------------------------------------------------------------------------

def test_sync_matcher_uses_norm_card_name():
    """The structural guard: _normalize IS norm_card_name.

    Everything below describes *why* that matters; this asserts the wiring, so a
    future edit cannot quietly point the matcher back at field_slug.
    """
    assert sc._normalize is io.norm_card_name, (
        "sync_collection._normalize must be norm_card_name. field_slug keeps "
        "internal spacing and collapses Nidoran♀/♂ — see this module's docstring."
    )


def test_field_slug_still_has_the_properties_that_disqualify_it():
    """Documents the two defects, so the reasoning survives if field_slug changes."""
    # Keeps internal spacing → PZ's corrected name never matched the stored one.
    assert io.field_slug("CastformSunny Form") != io.field_slug("Castform Sunny Form")
    # Collapses the gender glyphs → two distinct cards share one key.
    assert io.field_slug("Nidoran♀") == io.field_slug("Nidoran♂") == "nidoran"


# ---------------------------------------------------------------------------
# The normalizer's required behaviour
# ---------------------------------------------------------------------------

def test_normalizer_is_injective_over_the_whole_catalog():
    """No two distinct card names may share a key.

    This is the invariant that makes aggressive normalization safe. It is also
    the one that rules out the tempting "just strip everything non-alphanumeric"
    shortcut, which merges Nidoran♀ and Nidoran♂.
    """
    names = _reference_names()
    by_key = defaultdict(set)
    for n in names:
        by_key[io.norm_card_name(n)].add(n)
    collisions = {k: sorted(v) for k, v in by_key.items() if len(v) > 1}
    assert not collisions, f"normalizer merges distinct cards: {collisions}"


def test_gender_forms_stay_distinct():
    assert io.norm_card_name("Nidoran♀") != io.norm_card_name("Nidoran♂")


def test_spacing_drift_normalizes_equal():
    """The exact pairs that churned, from data/sync/sync_review_queue.json."""
    for stored, from_pz in [
        ("CastformSunny Form", "Castform Sunny Form"),
        ("CastformRainy Form", "Castform Rainy Form"),
        ("CastformSnowy Form", "Castform Snowy Form"),
        ("Rapid StrikeUrshifu", "Rapid Strike Urshifu"),
        ("Single StrikeUrshifu", "Single Strike Urshifu"),
        ("HisuianZorua", "Hisuian Zorua"),
        ("HisuianLilligant", "Hisuian Lilligant"),
        ("HisuianSliggoo", "Hisuian Sliggoo"),
        ("HisuianGoodra", "Hisuian Goodra"),
        ("HisuianZoroark ex", "Hisuian Zoroark ex"),
    ]:
        assert io.norm_card_name(stored) == io.norm_card_name(from_pz), (
            f"{stored!r} must match PZ's {from_pz!r}")


def test_base_and_ex_are_never_merged():
    """' ex' is a different card, not a spelling variant."""
    assert io.norm_card_name("Zygarde") != io.norm_card_name("Zygarde ex")
    assert io.norm_card_name("Marowak") != io.norm_card_name("Marowak ex")


def test_accents_fold_but_do_not_merge_distinct_cards():
    assert io.norm_card_name("Flabébé") == io.norm_card_name("Flabebe")


# ---------------------------------------------------------------------------
# Healing stored names from card_reference
# ---------------------------------------------------------------------------

def test_reconcile_name_fixes_spelling_drift():
    import assign_collection_coords as acc

    entry = {"name": "CastformSunny Form"}
    assert acc.reconcile_name(entry, "Castform Sunny Form") == "corrected"
    assert entry["name"] == "Castform Sunny Form"


def test_reconcile_name_never_swaps_one_card_for_another():
    """Only spelling is rewritten — a genuinely different name is left alone.

    Without this, a wrong coord would silently relabel the entry instead of
    surfacing as the coord mismatch it is.
    """
    import assign_collection_coords as acc

    entry = {"name": "Nidoran♀"}
    assert acc.reconcile_name(entry, "Nidoran♂") is None
    assert entry["name"] == "Nidoran♀"

    entry = {"name": "Zygarde"}
    assert acc.reconcile_name(entry, "Zygarde ex") is None
    assert entry["name"] == "Zygarde"


def test_reconcile_name_is_a_noop_without_a_reference_name():
    import assign_collection_coords as acc

    entry = {"name": "Castform"}
    assert acc.reconcile_name(entry, None) is None
    assert entry["name"] == "Castform"


def test_collection_carries_no_run_together_names():
    """End state: nothing in the tracked collection still has the old spelling."""
    import re

    data = json.loads(io.strip_comments(
        (ROOT / "collection.json").read_text(encoding="utf-8")))
    bad = [e["name"] for e in data["collection"]
           if re.search(r"[a-z][A-Z]", e.get("name", ""))]
    assert not bad, f"entries still carry run-together names: {bad}"
