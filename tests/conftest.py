"""Shared pytest fixtures.

`test_ev.py` and `test_results.py` validate the pipeline's generated outputs
(data/current/pack_ev.json, inferred_pack_recommendations.json, final_hourglass_
spending_plan.json). Those are gitignored build artifacts (regenerated from
collection.json + data/reference/*), so they are absent in a fresh checkout / CI.

This session-scoped autouse fixture generates them once if missing, making the suite
hermetic anywhere. Locally the files already exist, so it is a no-op.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_PACK_EV = ROOT / "data" / "current" / "pack_ev.json"


@pytest.fixture(scope="session", autouse=True)
def _ensure_pipeline_outputs():
    if not _PACK_EV.exists():
        # --skip-sync regenerates the full output set offline from the tracked
        # collection.json + reference data (no network, no PZ auth needed).
        subprocess.run(
            [sys.executable, "scripts/run_recommendations.py", "--skip-sync"],
            cwd=ROOT, capture_output=True,
        )
    yield
