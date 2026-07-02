"""
Integration tests: full pipeline smoke tests.

Runs the full pipeline end-to-end and verifies outputs exist and are valid JSON.
Tests the collection hash skip optimization on consecutive runs.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_OUTPUTS = [
    ROOT / "data" / "current" / "pack_ev.json",
    ROOT / "data" / "current" / "inferred_pack_recommendations.json",
    ROOT / "review" / "inferred_pack_recommendations.md",
]


def _run(script, *args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, f"scripts/{script}", *args],
        capture_output=True, text=True, cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Full pipeline smoke test (--skip-sync avoids network calls in CI)
# ---------------------------------------------------------------------------

def test_run_recommendations_skip_sync_exits_0():
    """run_recommendations.py --skip-sync must exit 0 and print 'Top pack:' line."""
    r = _run("run_recommendations.py", "--skip-sync")
    assert r.returncode == 0, f"run_recommendations.py --skip-sync failed:\n{r.stdout}\n{r.stderr}"
    assert "Top pack:" in r.stdout, (
        f"Expected 'Top pack:' in output, got:\n{r.stdout}"
    )


def test_run_recommendations_top_pack_uses_unified_score():
    """The 'Top pack:' line printed by run_recommendations.py must reference unified= not adj_ev=."""
    r = _run("run_recommendations.py", "--skip-sync")
    assert r.returncode == 0
    top_pack_lines = [l for l in r.stdout.splitlines() if "Top pack:" in l]
    assert top_pack_lines, "No 'Top pack:' line in output"
    assert "unified=" in top_pack_lines[0], (
        f"Expected 'unified=' in top-pack line, got: {top_pack_lines[0]!r}"
    )


def test_build_pack_ev_exits_0():
    r = _run("build_pack_ev.py")
    assert r.returncode == 0, f"build_pack_ev.py failed:\n{r.stderr}"


def test_recommendation_report_exits_0():
    r = _run("generate_pack_recommendation_report.py")
    assert r.returncode == 0, f"generate_pack_recommendation_report.py failed:\n{r.stderr}"


def test_all_output_files_exist():
    for path in EXPECTED_OUTPUTS:
        assert path.exists(), f"Expected output missing: {path.relative_to(ROOT)}"


def test_all_json_outputs_valid():
    for path in EXPECTED_OUTPUTS:
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                pytest.fail(f"{path.relative_to(ROOT)} is not valid JSON: {e}")


# ---------------------------------------------------------------------------
# Validate modes
# ---------------------------------------------------------------------------

def test_recommendation_report_validate_passes():
    r = _run("generate_pack_recommendation_report.py", "--validate")
    assert r.returncode == 0, f"--validate failed:\n{r.stdout}\n{r.stderr}"
    assert "PASS" in r.stdout


# ---------------------------------------------------------------------------
# Collection hash skip
# ---------------------------------------------------------------------------

def test_second_ev_run_skips_recompute():
    """After one full run, a second consecutive run should detect unchanged collection."""
    # First run to ensure hash is current
    r1 = _run("build_pack_ev.py")
    assert r1.returncode == 0, f"First run failed: {r1.stderr}"

    # Second run should skip
    r2 = _run("build_pack_ev.py")
    assert r2.returncode == 0, f"Second run failed: {r2.stderr}"
    assert "unchanged" in r2.stdout.lower() or "skipping" in r2.stdout.lower(), (
        f"Expected skip message on second run, got stdout: {r2.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Output structure sanity checks
# ---------------------------------------------------------------------------

def test_pack_ev_has_unified_score():
    ev = json.loads((ROOT / "data" / "current" / "pack_ev.json").read_text(encoding="utf-8"))
    for p in ev["packs"][:5]:
        assert "unified_score" in p, f"{p['pack_name']} missing unified_score"


def test_recommendations_no_legacy_keys():
    rec = json.loads(
        (ROOT / "data" / "current" / "inferred_pack_recommendations.json").read_text(encoding="utf-8")
    )
    for bad_key in ("top_5_by_new_card_ev", "deprioritize_5", "planning_scenarios", "scenarios"):
        assert bad_key not in rec, f"Legacy key '{bad_key}' still present"
    assert "top_packs_unified" in rec
    assert "cost_efficiency_ranking" in rec
