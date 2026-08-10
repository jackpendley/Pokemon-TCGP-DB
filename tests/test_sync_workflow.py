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

# The owner's timezone. Phoenix does not observe DST, so a fixed UTC hour is the
# same local time all year and the cron needs no seasonal adjustment — do not
# "fix" this to a DST-aware zone without also splitting the cron.
OWNER_TZ = "America/Phoenix"

# The cron is aimed slightly BEFORE 2am on purpose. GitHub runs scheduled
# workflows on a best-effort queue, and the first nightly run was queued at 09:00
# UTC and started at 10:05 — 66 minutes late, because :00 is the most contended
# slot. Firing at :40 avoids the rush and leaves headroom so a typical delay
# still lands near 2am. The window below is what "overnight" means here; the
# off-the-hour check is what stops someone tidying it back to :00.
TARGET_WINDOW_LOCAL = range(1, 4)          # 01:00-03:59 local


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


def test_cron_runs_overnight_and_never_drifts_with_the_seasons(workflow):
    cron = _triggers(workflow)["schedule"][0]["cron"]
    minute, hour, dom, month, dow = cron.split()
    assert (dom, month, dow) == ("*", "*", "*"), f"not a daily cron: {cron}"

    summer = (datetime(2026, 6, 1, int(hour), int(minute), tzinfo=timezone.utc)
              .astimezone(ZoneInfo(OWNER_TZ)))
    winter = (datetime(2026, 12, 1, int(hour), int(minute), tzinfo=timezone.utc)
              .astimezone(ZoneInfo(OWNER_TZ)))

    assert summer.hour in TARGET_WINDOW_LOCAL, (
        f"cron {cron} fires at {summer.strftime('%H:%M')} local — outside the "
        f"overnight window {TARGET_WINDOW_LOCAL.start}:00-{TARGET_WINDOW_LOCAL.stop - 1}:59")
    assert (summer.hour, summer.minute) == (winter.hour, winter.minute), (
        f"cron {cron} drifts between seasons ({summer:%H:%M} vs {winter:%H:%M}) — "
        f"{OWNER_TZ} does not observe DST, so something else changed")


def test_cron_avoids_the_contended_top_of_the_hour(workflow):
    """The offset is the point, not an accident.

    The first nightly run was scheduled for 09:00 UTC and started at 10:05 — 66
    minutes late, because the top of the hour is where every scheduled workflow
    on GitHub piles up. Rounding this back to :00 would quietly undo the fix.
    """
    minute = int(_triggers(workflow)["schedule"][0]["cron"].split()[0])
    assert minute != 0, (
        "the nightly cron is deliberately off the hour to dodge GitHub's "
        "scheduled-workflow queue — see this module's TARGET_WINDOW_LOCAL note")


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
