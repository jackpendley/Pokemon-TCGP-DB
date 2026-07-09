"""
Cross-boundary lock for run_recommendations.py's exit-code contract.

web/lib/sync/runner.ts (mapExitCode, pinned by web/lib/sync/runner.test.ts)
matches on these literal values: 0/2 → done, 3 → needs_reauth, else error.
This is the Python-side half of that lock — a renumber here without a matching
runner.ts change silently regresses the needs_reauth flow.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_recommendations as rr


def test_exit_codes_match_web_runner_contract():
    assert rr.EXIT_OK == 0
    assert rr.EXIT_FATAL == 1
    assert rr.EXIT_REVIEW_ITEMS == 2
    assert rr.EXIT_AUTH_EXPIRED == 3


def test_docstring_documents_the_contract():
    # The module docstring is the human-readable source; keep it in step.
    for line in ("0  Full pipeline completed", "3  Pipeline completed but PZ auth expired"):
        assert line in rr.__doc__
