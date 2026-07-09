"""
Branch lock for determine_source_status in build_pull_probability_model.

Before this lock, an all-third_party_verified model was mislabeled
'third_party_verified_with_in_app_anchor' (the mid-tier check fired before the
dedicated third_party_verified return, leaving that branch dead), so the
model's meta falsely claimed an in-app anchor that did not exist.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_pull_probability_model import determine_source_status


def _packs(*confs):
    return [{"confidence": c} for c in confs]


def test_all_verified():
    assert determine_source_status(_packs("verified", "verified")) == "verified"


def test_all_third_party_verified_has_no_anchor():
    assert determine_source_status(
        _packs("third_party_verified", "third_party_verified")
    ) == "third_party_verified"


def test_in_app_anchor_label_requires_top_tier():
    assert determine_source_status(
        _packs("user_in_app_verified", "third_party_verified")
    ) == "third_party_verified_with_in_app_anchor"
    assert determine_source_status(
        _packs("bulbapedia_branch_verified", "third_party_verified")
    ) == "third_party_verified_with_in_app_anchor"


def test_top_only_without_in_app_is_bulbapedia_branch():
    assert determine_source_status(
        _packs("bulbapedia_branch_verified", "verified")
    ) == "bulbapedia_branch_verified"


def test_mid_mixed_with_low_is_not_fully_verified():
    assert determine_source_status(
        _packs("third_party_verified", "inferred")
    ) == "inferred"
    assert determine_source_status(
        _packs("third_party_verified", "pending_verification")
    ) == "inferred"


def test_inferred_and_scaffold():
    assert determine_source_status(_packs("inferred")) == "inferred"
    assert determine_source_status(_packs("unknown")) == "scaffold_only"
