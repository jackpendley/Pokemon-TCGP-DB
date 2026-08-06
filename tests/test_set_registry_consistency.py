#!/usr/bin/env python3
"""
Guardrail tests: every set-keyed table across the pipeline must stay consistent
with the single source of truth, SET_REGISTRY (in _collection_io.py).

Adding a new set touches several hand-maintained tables in different modules.
Only one of them (SET_ALIASES) was previously enforced at import time, so a set
could be "half-registered" — registered in SET_REGISTRY and syncing fine, but a
table elsewhere carrying a stale or typo'd set code with no error.

These tests assert the invariants that are actually true today:
  * SET_ALIASES keys EXACTLY equal the registry (mirrors the import-time check).
  * Pull-model tables are SUBSETS — they legitimately omit promos and any set
    whose pull rates are still pending (e.g. B3a), but must never carry a set
    code that isn't in the registry (that would be a typo or a removed set).
  * The A4b reprint/mislabel set lists agree across the modules that define them
    and resolve to real set codes.

They do NOT assert full pull-model coverage, because pull rates are added per
set on a deliberate schedule (a set can be live before its pull model exists).

    python3 -m pytest tests/test_set_registry_consistency.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _collection_io import VALID_SET_CODES, canonical_set_code
import fetch_source_snapshots as fss
import build_pull_probability_model as bppm
import build_reprint_links as brl
import coord_resolver as cr
import sync_collection as sc


def test_set_aliases_match_registry_exactly():
    """External-source aliases must cover exactly the registered sets — no more, no less."""
    assert set(fss.SET_ALIASES) == set(VALID_SET_CODES), (
        f"SET_ALIASES drift: "
        f"missing={set(VALID_SET_CODES) - set(fss.SET_ALIASES)}, "
        f"extra={set(fss.SET_ALIASES) - set(VALID_SET_CODES)}"
    )


def test_combat_stat_sources_partition_the_registry():
    """Every set must draw HP/stage/effects from exactly one source.

    These two tables were hand-maintained with no guard, and forgetting a new
    set there silently leaves it without HP or stage rather than failing —
    the B3b release hit exactly that (docs/adding-a-set.md gap #9).
    """
    import fetch_combat_stats as fcs
    import fetch_trainer_effects as fte

    for name, mod in (("fetch_combat_stats", fcs), ("fetch_trainer_effects", fte)):
        covered = mod.TCGDEX_COVERED | mod.LIMITLESS_COVERED
        assert covered == set(VALID_SET_CODES), (
            f"{name} coverage drift: "
            f"missing={set(VALID_SET_CODES) - covered}, "
            f"extra={covered - set(VALID_SET_CODES)}"
        )
        overlap = mod.TCGDEX_COVERED & mod.LIMITLESS_COVERED
        assert not overlap, f"{name}: set(s) claimed by both sources: {sorted(overlap)}"

    # The trainer-effects module documents itself as "kept in sync" with combat
    # stats; make that a fact rather than a comment.
    assert fcs.TCGDEX_COVERED == fte.TCGDEX_COVERED
    assert fcs.LIMITLESS_COVERED == fte.LIMITLESS_COVERED


def test_pull_model_tables_have_no_unknown_set_codes():
    """Pull-model tables may omit sets (pending/promo) but must not carry unknown codes."""
    for name, table in (("BULBAPEDIA_URLS", bppm.BULBAPEDIA_URLS),
                        ("SET_CODE_BRANCH_CONFIG", bppm.SET_CODE_BRANCH_CONFIG)):
        unknown = set(table) - set(VALID_SET_CODES)
        assert not unknown, f"{name} contains unregistered set codes: {unknown}"


def test_reprint_link_sets_are_registered():
    """build_reprint_links' original + reprint sets must resolve to real set codes."""
    for sc_code in brl.ORIGINAL_SETS:
        assert sc_code in VALID_SET_CODES, f"ORIGINAL_SETS has unregistered code: {sc_code}"
    assert canonical_set_code(brl.REPRINT_SET) in VALID_SET_CODES, (
        f"REPRINT_SET {brl.REPRINT_SET!r} does not resolve to a registered set code"
    )


def test_a4b_target_lists_agree_across_modules():
    """The A4b-reprint target sets are duplicated in coord_resolver and sync_collection;
    they must stay identical, or the two modules will disagree on A4b coord recovery."""
    assert cr._PZ_MISLABEL_TARGET_SETS == sc._A4B_HYBRID_TARGET_SETS, (
        f"A4b target-set drift: coord_resolver={set(cr._PZ_MISLABEL_TARGET_SETS)} "
        f"vs sync_collection={set(sc._A4B_HYBRID_TARGET_SETS)}"
    )


def test_a4b_mislabel_sets_are_registered():
    """Every set code in the A4b mislabel/target frozensets must be a real set code."""
    codes = (cr._PZ_MISLABEL_TARGET_SETS | cr._PZ_MISLABEL_SOURCE_SETS
             | sc._A4B_HYBRID_TARGET_SETS)
    for raw in codes:
        assert canonical_set_code(raw) in VALID_SET_CODES, (
            f"A4b set list has unregistered code: {raw!r}"
        )


def test_promo_overrides_match_pack_sources():
    """The hardcoded PROMO name overrides (used because PZ returns wrong/blank names)
    must agree with pack_sources for the same coord. If the catalog shifts and
    pack_sources is rebuilt but a dict isn't (or vice-versa), this catches the drift."""
    ps = sc.load_pack_sources()
    for set_code, overrides in (("PROMO-A", sc._PROMO_A_OVERRIDES),
                                ("PROMO-B", sc._PROMO_B_OVERRIDES)):
        for num, name in overrides.items():
            rec = ps.get((set_code, num))
            assert rec is not None, (
                f"{set_code}/{num} override {name!r} has no pack_sources record"
            )
            assert sc._normalize(rec["card_name"]) == sc._normalize(name), (
                f"{set_code}/{num} override {name!r} != pack_sources {rec['card_name']!r}"
            )
