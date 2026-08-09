#!/usr/bin/env python3
"""
Guards for the nightly sync schedule.

This exists because the gap, not the upstream, was the larger half of the Ruler
of the Skies incident: the set released 2026-07-29 and nobody ran a sync for six
days, so both the missing cards and Pokémon Zone's own outage stayed invisible
until they were spotted by hand. A nightly run is what turns "the data is wrong
and nobody knows" into "the data is stale and the dashboard says so".

A schedule that silently stops firing, or fires into the wrong runner, is worse
than no schedule at all — it removes the prompt to check manually while providing
nothing. Hence these.

    python3 -m pytest tests/test_sync_workflow.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "sync.yml"

# The owner's timezone. Phoenix does not observe DST, so one UTC hour is 2am all
# year and the cron needs no seasonal adjustment — do not "fix" this to a
# DST-aware zone without also splitting the cron.
OWNER_TZ = "America/Phoenix"
TARGET_LOCAL_HOUR = 2


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers(workflow):
    # PyYAML reads a bare `on:` key as the boolean True.
    return workflow.get(True) or workflow.get("on")


def test_sync_runs_nightly(workflow):
    schedule = _triggers(workflow).get("schedule")
    assert schedule, "the nightly sync schedule is missing"
    assert len(schedule) == 1, f"expected exactly one cron, got {schedule}"


def test_cron_is_2am_in_the_owners_timezone(workflow):
    cron = _triggers(workflow)["schedule"][0]["cron"]
    minute, hour, dom, month, dow = cron.split()
    assert (minute, dom, month, dow) == ("0", "*", "*", "*"), f"not a daily cron: {cron}"

    local = (datetime(2026, 6, 1, int(hour), tzinfo=timezone.utc)
             .astimezone(ZoneInfo(OWNER_TZ)))
    winter = (datetime(2026, 12, 1, int(hour), tzinfo=timezone.utc)
              .astimezone(ZoneInfo(OWNER_TZ)))
    assert local.hour == TARGET_LOCAL_HOUR, (
        f"cron {cron} is {local.hour}:00 in {OWNER_TZ}, not {TARGET_LOCAL_HOUR}:00")
    assert winter.hour == TARGET_LOCAL_HOUR, (
        f"cron {cron} drifts to {winter.hour}:00 in winter — {OWNER_TZ} should not")


def test_scheduled_run_is_a_live_sync_on_the_self_hosted_runner(workflow):
    """A schedule must take the same path as a manual dispatch.

    'skip' mode republishes the committed collection without contacting Pokémon
    Zone, and the cloud runner cannot reach it at all (Cloudflare blocks
    datacenter IPs), so a schedule routed either way would run nightly and never
    fetch anything — the failure this schedule exists to prevent.
    """
    job = workflow["jobs"]["publish"]
    runs_on, mode = job["runs-on"], job["env"]["MODE"]

    # Both expressions branch on push / inputs.mode only; a schedule matches
    # neither and therefore falls through to self-hosted + live.
    for expr, name in ((runs_on, "runs-on"), (mode, "MODE")):
        assert "schedule" not in expr, (
            f"{name} special-cases the schedule event: {expr}")
    assert "'self-hosted'" in runs_on and "ubuntu-latest" in runs_on
    assert "'live'" in mode


def test_manual_and_dispatch_triggers_are_retained(workflow):
    triggers = _triggers(workflow)
    assert "repository_dispatch" in triggers, "the dashboard Sync button needs this"
    assert "workflow_dispatch" in triggers, "manual runs must stay possible"
