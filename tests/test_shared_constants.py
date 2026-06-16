"""
Regression guards for constants centralised in _collection_io.

These exist to prevent the "silently divergent per-script knob" drift that the
HTTP request timeouts had before centralisation: each consumer must keep using
the shared object, not re-declare its own local copy.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io


def test_request_constants_values():
    # Lightweight API / single-card fetches vs. heavier full-set HTML scrapes.
    assert (io.REQUEST_TIMEOUT, io.REQUEST_DELAY) == (12, 0.35)
    assert (io.SNAPSHOT_REQUEST_TIMEOUT, io.SNAPSHOT_REQUEST_DELAY) == (15, 0.4)


def test_lightweight_consumers_use_shared_constants():
    import coord_resolver
    import validate_collection_coords as vcc

    # Identity, not just equality: catches a re-introduced local shadow.
    assert coord_resolver.REQUEST_TIMEOUT is io.REQUEST_TIMEOUT
    assert coord_resolver.REQUEST_DELAY is io.REQUEST_DELAY
    assert vcc.REQUEST_TIMEOUT is io.REQUEST_TIMEOUT
    assert vcc.REQUEST_DELAY is io.REQUEST_DELAY


def test_snapshot_consumer_uses_shared_constants():
    import fetch_source_snapshots as fss

    # Imported under the historical local names but bound to the snapshot pair.
    assert fss.REQUEST_TIMEOUT is io.SNAPSHOT_REQUEST_TIMEOUT
    assert fss.REQUEST_DELAY is io.SNAPSHOT_REQUEST_DELAY


def test_a4b_and_promo_constants_values():
    assert io.A4B_SET_CODE == "A4B"
    # Ordered by debut so it can drive tie-breaks, not just membership.
    assert io.A4B_ORIGINAL_SETS == ("A1", "A2", "A3", "A4")
    assert io.PROMO_SET_CODES == frozenset({"PROMO-A", "PROMO-B"})


def test_a4b_consumers_derive_from_shared_constants():
    import coord_resolver
    import build_reprint_links as brl
    import build_pull_probability_model as bppm

    assert coord_resolver._PZ_MISLABEL_SOURCE_SETS == frozenset({io.A4B_SET_CODE})
    assert coord_resolver._PZ_MISLABEL_TARGET_SETS == frozenset(io.A4B_ORIGINAL_SETS)
    assert brl.REPRINT_SET == io.A4B_SET_CODE
    assert brl.ORIGINAL_SETS == list(io.A4B_ORIGINAL_SETS)
    assert bppm._NON_HOURGLASS_PURCHASABLE == {io.A4B_SET_CODE}
    assert bppm._PROMO_SET_CODES is io.PROMO_SET_CODES
