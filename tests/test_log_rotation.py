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
