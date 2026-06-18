#!/usr/bin/env python3
"""
Unit tests for pipeline.log rotation (_append_log / _trim_log).

The pipeline log is append-only; _trim_log caps retained history to the most
recent LOG_MAX_BLOCKS stage blocks so it can't grow without bound.

Usage:
    python3 -m pytest tests/test_log_rotation.py
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location(
    "run_recommendations",
    ROOT / "scripts" / "run_recommendations.py",
)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def test_append_log_caps_to_recent_blocks(tmp_path, monkeypatch):
    log = tmp_path / "pipeline.log"
    monkeypatch.setattr(rr, "LOG_FILE", log)
    monkeypatch.setattr(rr, "LOG_MAX_BLOCKS", 5)

    # Write well past the cap; each block body names its index so we can check ordering.
    for i in range(20):
        rr._append_log(f"Stage {i}", f"body-{i}")

    text = log.read_text(encoding="utf-8")
    sep = "=" * 60
    # Exactly LOG_MAX_BLOCKS blocks retained (2 separators per block).
    assert text.count(sep) == rr.LOG_MAX_BLOCKS * 2, text.count(sep)
    # The most recent block is intact (header + body) and the oldest are gone.
    assert "Stage 19" in text and "body-19" in text
    assert "body-0\n" not in text
    assert "Stage 15" in text and "Stage 14" not in text


def test_append_log_below_cap_keeps_everything(tmp_path, monkeypatch):
    log = tmp_path / "pipeline.log"
    monkeypatch.setattr(rr, "LOG_FILE", log)
    monkeypatch.setattr(rr, "LOG_MAX_BLOCKS", 50)

    for i in range(3):
        rr._append_log(f"Stage {i}", f"body-{i}")

    text = log.read_text(encoding="utf-8")
    for i in range(3):
        assert f"body-{i}" in text


# A canonical --skip-sync run's stage blocks.
_RUN = [("Normalize entries", "assigned 0\n"),
        ("Validate coords", "OK\n"),
        ("Spending plan", "  Inputs unchanged (hash=abc…) — skipping recompute.\n")]


def _emit_run(blocks, ts="2026-06-18T01:21:41Z"):
    """Mimic one pipeline invocation: write the per-run 'Pipeline run:' banner (as main()
    does, with a fresh timestamp each time), append the stage blocks, then collapse."""
    sep = "=" * 60
    with rr.LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{sep}\nPipeline run: {ts}\n{sep}\n")
    for label, body in blocks:
        rr._append_log(label, body)
    rr._collapse_repeated_run()


def test_collapse_identical_reruns(tmp_path, monkeypatch):
    log = tmp_path / "pipeline.log"
    monkeypatch.setattr(rr, "LOG_FILE", log)
    monkeypatch.setattr(rr, "LOG_MAX_BLOCKS", 200)

    _emit_run(_RUN, ts="2026-06-18T01:00:00Z")  # run 1 — nothing to collapse against
    text = log.read_text()
    assert text.count("] Normalize entries\n") == 1
    assert rr._REPEAT_LABEL not in text

    # run 2 — identical except its Spending timestamp → still collapses into a ×2 marker
    _emit_run(_RUN, ts="2026-06-18T02:00:00Z")
    text = log.read_text()
    assert text.count("] Normalize entries\n") == 1, "second run's blocks were not collapsed"
    assert f"({rr._REPEAT_LABEL} ×2)" in text

    _emit_run(_RUN, ts="2026-06-18T03:00:00Z")  # run 3 — identical → bumps the marker to ×3
    text = log.read_text()
    assert f"({rr._REPEAT_LABEL} ×3)" in text
    assert "×2)" not in text
    assert text.count(rr._REPEAT_LABEL) == 1, "marker must not duplicate"


def test_collapse_preserves_changed_run(tmp_path, monkeypatch):
    log = tmp_path / "pipeline.log"
    monkeypatch.setattr(rr, "LOG_FILE", log)
    monkeypatch.setattr(rr, "LOG_MAX_BLOCKS", 200)

    _emit_run(_RUN)
    _emit_run(_RUN)                                   # collapses to ×2
    changed = [_RUN[0], ("Validate coords", "1 owned card <confirmed\n"), _RUN[2]]
    _emit_run(changed)                                # different body → kept in full

    text = log.read_text()
    assert "1 owned card <confirmed" in text, "a changed run must not be collapsed"
    assert f"({rr._REPEAT_LABEL} ×2)" in text         # earlier collapse marker survives
