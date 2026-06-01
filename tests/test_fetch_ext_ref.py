"""
Tests for fetch_ext_ref.py guards — specifically the mass-misclassification
flip-abort decision, which protects ext_ref from a parser/site-layout regression
silently overwriting it on a --force re-fetch.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_ext_ref as fer


# ---------------------------------------------------------------------------
# Flip-abort decision (_should_abort_flips)
# ---------------------------------------------------------------------------

def test_no_refetch_never_aborts():
    """A pure first-fetch (0 re-fetched records) can't trip the flip guard."""
    assert fer._should_abort_flips(category_flips=0, refetched=0, allow_override=False) is False


def test_small_flip_ratio_does_not_abort():
    """A single-card genuine fix (1/100 = 1%) stays well under the threshold."""
    assert fer._should_abort_flips(1, 100, allow_override=False) is False


def test_at_threshold_does_not_abort():
    """Exactly at the threshold (15/100 = 15%) does NOT abort — must exceed it."""
    assert fer._should_abort_flips(15, 100, allow_override=False) is False


def test_above_threshold_aborts():
    """A mass flip (16/100 = 16% > 15%) across multiple transition types aborts."""
    assert fer._should_abort_flips(16, 100, allow_override=False) is True
    # Explicit multi-direction collapse also aborts.
    assert fer._should_abort_flips(16, 100, allow_override=False, distinct_transitions=4) is True


def test_override_suppresses_abort():
    """--allow-category-flips (override) lets even a 100% flip through."""
    assert fer._should_abort_flips(100, 100, allow_override=True) is False


def test_small_set_high_ratio_aborts():
    """Ratio, not absolute count, drives the decision (2/3 = 67% aborts)."""
    assert fer._should_abort_flips(2, 3, allow_override=False) is True


def test_single_coherent_transition_does_not_abort():
    """A high flip rate in ONE coherent direction (e.g. Pokemon→Item Fossil fix)
    is a likely bulk fix, not a regression — it proceeds without --allow-category-flips."""
    assert fer._should_abort_flips(30, 60, allow_override=False, distinct_transitions=1) is False


def test_multi_transition_collapse_aborts():
    """Many categories draining into one (multiple transition types) is a regression."""
    assert fer._should_abort_flips(40, 100, allow_override=False, distinct_transitions=3) is True


def test_threshold_constant_is_sane():
    """The abort ratio is a fraction in (0, 1)."""
    assert 0.0 < fer.FLIP_ABORT_RATIO < 1.0
    # First-fetch single-category warn threshold is full-set-scale (not tiny).
    assert fer.SINGLE_CATEGORY_WARN_MIN >= 20
