#!/usr/bin/env python3
"""
Full recommendation pipeline: sync → validate → normalize → EV → reports.

Usage:
    python3 scripts/run_recommendations.py                         # headless sync (stored auth)
    python3 scripts/run_recommendations.py --json-import           # auto-detect newest ~/Downloads/pz_collection*.json
    python3 scripts/run_recommendations.py --json-import FILE      # explicit bookmarklet JSON path
    python3 scripts/run_recommendations.py --skip-sync             # skip sync, use current collection
    python3 scripts/run_recommendations.py --login                 # re-auth browser before sync
    python3 scripts/run_recommendations.py --dry-run-sync          # show sync diff only, stop
    python3 scripts/run_recommendations.py --promo                 # also run promo EV (Shop Tickets currency)
    python3 scripts/run_recommendations.py --full-rankings         # print all 24 packs ranked + write review/full_pack_ranking.md
    python3 scripts/run_recommendations.py --include-limited       # include limited-time packs (e.g. Deluxe Pack: ex)

Exit codes:
    0  Full pipeline completed
    1  Fatal error in any step
    2  Sync had review items; pipeline ran with existing collection.json
    3  Pipeline completed but PZ auth expired — collection NOT refreshed.
       Consumed by the web sync runner (web/lib/sync/runner.ts) as needs_reauth.
"""

import argparse
import itertools
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (strip_comments, card_reference_freshness,
                            ROOT, CARD_REF_JSON, SOURCES_DIR)

# Exit-code contract (see module docstring). The web sync runner
# (web/lib/sync/runner.ts mapExitCode) matches on these values; a renumber
# silently breaks its needs_reauth handling, so tests pin them.
EXIT_OK = 0
EXIT_FATAL = 1
EXIT_REVIEW_ITEMS = 2
EXIT_AUTH_EXPIRED = 3

LOG_FILE = ROOT / "data" / "pipeline.log"
LOG_MAX_BLOCKS = 200  # retain only the most recent N stage blocks (the log is append-only)

PIPELINE_STEPS = [
    ("Build pack EV",        "scripts/build_pack_ev.py"),
    ("Recommendations",      "scripts/generate_pack_recommendation_report.py"),
]

_STATUS_PATTERNS: dict[str, list[tuple]] = {
    "Build pack EV": [
        (r"Packs scored:\s*(\d+)", lambda m: f"{m.group(1)} packs"),
        (r"skipping (?:EV )?recompute", lambda m: "cached (inputs unchanged)"),
    ],
    "Build promo EV": [
        (r"Promo packs in PZ data:\s*(\d+)", lambda m: f"{m.group(1)} promo packs"),
        (r"skipping (?:EV )?recompute", lambda m: "cached (inputs unchanged)"),
    ],
}


_REPEAT_LABEL = "repeated, no changes"


def _append_log(label: str, output: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 60}\n[{ts}] {label}\n{'=' * 60}\n")
        f.write(output)
        if not output.endswith("\n"):
            f.write("\n")
    _trim_log()


def _trim_log() -> None:
    """Keep only the most recent LOG_MAX_BLOCKS stage blocks so the log can't grow forever.

    Blocks are delimited by the ``'=' * 60`` separator line written above; keeping a
    multiple of that delimiter preserves whole blocks (header + body) intact.
    """
    sep = "=" * 60
    text = LOG_FILE.read_text(encoding="utf-8")
    # Each block is "<sep>\n[ts] label\n<sep>\n<body>", i.e. two separators per block.
    if text.count(sep) <= LOG_MAX_BLOCKS * 2:
        return
    # Split on the leading "\n<sep>\n[" that begins every block and keep the last N.
    blocks = text.split(f"\n{sep}\n[")
    kept = blocks[-LOG_MAX_BLOCKS:]
    LOG_FILE.write_text(f"\n{sep}\n[".join(["", *kept]).lstrip("\n"), encoding="utf-8")


_ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_RUN_DELIM = f"\n{'=' * 60}\nPipeline run: "  # main() writes this at the start of every run


def _run_marker(count: int) -> str:
    """A collapsed-repeat 'run' chunk (sits where the duplicate run would have been)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{ts}  ({_REPEAT_LABEL} ×{count})\n{'=' * 60}\n"
            f"The previous run repeated identically; collapsed to keep the log readable.\n")


def _collapse_repeated_run() -> None:
    """Collapse the just-finished run when it's identical (modulo timestamps) to the
    previous one. Splits the log on the ``Pipeline run:`` banner main() writes per run.

    Targets the repeated ``--skip-sync`` reruns that bloat the log; a real sync never
    matches (its body carries a per-run taskId) so it stays logged in full. The tail is
    kept as ``[…][reference run][<repeat-marker ×N>]`` so each further identical rerun
    just bumps the marker instead of appending another copy.
    """
    if not LOG_FILE.exists():
        return
    chunks = LOG_FILE.read_text(encoding="utf-8").split(_RUN_DELIM)
    if len(chunks) < 3:  # preamble + at least two runs
        return
    preamble, runs = chunks[0], chunks[1:]
    cur = runs[-1]

    def same(a: str, b: str) -> bool:
        return _ISO_TS_RE.sub("<ts>", a) == _ISO_TS_RE.sub("<ts>", b)

    if f"{_REPEAT_LABEL} ×" in runs[-2].split("\n", 1)[0]:
        # Previous chunk is a marker from an earlier collapse; the reference is before it.
        if len(runs) < 3 or not same(cur, runs[-3]):
            return
        count = int(re.search(r"×(\d+)", runs[-2].split("\n", 1)[0]).group(1)) + 1
        new_runs = runs[:-2] + [_run_marker(count)]
    else:
        if not same(cur, runs[-2]):
            return
        new_runs = runs[:-1] + [_run_marker(2)]

    LOG_FILE.write_text(preamble + _RUN_DELIM + _RUN_DELIM.join(new_runs), encoding="utf-8")


def _extract_status(label: str, stdout: str) -> str:
    entries = _STATUS_PATTERNS.get(label)
    if not entries:
        return "OK"
    for pattern, fmt in entries:
        m = re.search(pattern, stdout)
        if m:
            return fmt(m)
    # A pattern is registered but nothing matched: the stage's output format
    # drifted. Don't pretend it parsed — surface it so the regex gets updated.
    return "OK (summary not parsed — see data/pipeline.log)"


def _run(label: str, script: str, extra_args: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, script] + (extra_args or [])
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    combined = result.stdout
    if result.stderr.strip():
        combined += "\n--- stderr ---\n" + result.stderr
    _append_log(label, combined)
    return result.returncode, result.stdout


def _run_with_spinner(label: str, script: str, extra_args: list[str] | None = None) -> tuple[int, str]:
    """Run a subprocess while printing a spinner; capture output for the log."""
    cmd = [sys.executable, script] + (extra_args or [])
    buf_out: list[str] = []
    buf_err: list[str] = []
    done = threading.Event()

    def _spin() -> None:
        for frame in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if done.is_set():
                break
            print(f"\r  {frame}  {label:<22}  syncing...", end="", flush=True)
            time.sleep(0.1)
        print(f"\r{' ' * 50}\r", end="", flush=True)  # clear spinner line

    with subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        spin_thread = threading.Thread(target=_spin, daemon=True)
        spin_thread.start()
        stdout, stderr = proc.communicate()
        done.set()
        spin_thread.join()
        rc = proc.returncode

    combined = stdout + (("\n--- stderr ---\n" + stderr) if stderr.strip() else "")
    _append_log(label, combined)
    return rc, stdout


def _print_step(label: str, rc: int, status: str) -> None:
    icon = "✓" if rc == 0 else "✗"
    print(f"  {icon}  {label:<22}  {status}")


def _find_latest_pz_json() -> Path:
    downloads = Path.home() / "Downloads"
    candidates = sorted(downloads.glob("pz_collection*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(
            "No pz_collection*.json in ~/Downloads.\n"
            "Click the 'PZ Sync' bookmarklet on pokemon-zone.com/collection-tracker/ first."
        )
    return candidates[-1]


def _auth_age_days() -> float | None:
    """Age of the stored PZ auth in days, or None if absent/unreadable. Used to warn
    before a ~3–4 week session lapses mid-run."""
    p = ROOT / "data" / "sync" / ".auth.json"
    if not p.exists():
        return None
    try:
        imported = json.loads(p.read_text(encoding="utf-8")).get("imported_at")
        dt = datetime.fromisoformat(imported.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    except (json.JSONDecodeError, OSError, ValueError, AttributeError):
        return None


def _load_collection_json() -> dict:
    """Read + comment-strip + parse collection.json. Not cached: assign rewrites the
    file mid-pipeline, so _collection_status (pre-assign) and _read_meta_total
    (post-assign) intentionally read at different times."""
    raw = (ROOT / "collection.json").read_text(encoding="utf-8")
    return json.loads(strip_comments(raw))


def _read_meta_total() -> str:
    try:
        data = _load_collection_json()
        return str(data.get("meta", {}).get("total_cards", 380))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "0"


def _collection_status() -> str:
    """Read total/unique from collection.json for the sync status line.

    Flags a run whose numbers came from Pokémon Zone's previous snapshot rather
    than a fresh read of the game — otherwise a sync that changed nothing because
    the upstream never refreshed is indistinguishable from one that found nothing
    new, which is exactly how the missing Ruler of the Skies pulls stayed
    invisible across three syncs.
    """
    try:
        data = _load_collection_json()
        meta = data.get("meta", {})
        total = meta.get("total_cards", "?")
        unique = len(data.get("collection", []))
        status = f"{total} cards, {unique} unique"
        if _read_player_stats().get("player_synced") is False:
            status += " — STALE: Pokémon Zone did not refresh from the game"
        return status
    except Exception:
        return "synced"


def _read_player_stats() -> dict:
    path = ROOT / "data" / "sync" / "player_stats.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _print_full_rankings(include_limited: bool = False, series: str | None = None) -> None:
    pack_ev_path = ROOT / "data" / "current" / "pack_ev.json"
    if not pack_ev_path.exists():
        return
    try:
        data = json.loads(pack_ev_path.read_text(encoding="utf-8"))
    except Exception:
        return

    packs = sorted(
        (p for p in data.get("packs", [])
         if not p.get("blocked") and (include_limited or p.get("purchasable", True))),
        key=lambda p: p.get("unified_score", 0),
        reverse=True,
    )
    if series:
        packs = [p for p in packs if p.get("set_code", "").upper().startswith(series.upper())]
    if not packs:
        return

    col_name = max(len(p.get("pack_name", "")) for p in packs)
    col_name = max(col_name, 4)
    col_set  = max(len(p.get("set_code", "")) for p in packs)
    col_set  = max(col_set, 3)
    max_cost = max((p.get("cost_per_unique_card_10x", 0.0) for p in packs), default=0.0)
    col_cost = max(len(f"{max_cost:.1f}") + 1, 6)

    series_label = f" ({series.upper()}-series)" if series else ""
    print()
    print(f"  Full Pack Rankings{series_label} — {len(packs)} packs  (open with Pack Hourglasses, 120 ⧗ per 10x)")
    print()
    print(f"  {'#':>3}  {'Set':<{col_set}}  {'Pack':<{col_name}}  {'Base':>9}  {'All':>9}  {'★+miss':>6}  {'EV/10x':>7}  {'★+cnt':>6}  {'⧗/EV':>{col_cost}}")
    print(f"  {'─' * 3}  {'─' * col_set}  {'─' * col_name}  {'─' * 9}  {'─' * 9}  {'─' * 6}  {'─' * 7}  {'─' * 6}  {'─' * col_cost}")

    for i, p in enumerate(packs, 1):
        name         = p.get("pack_name", "?")
        set_code     = p.get("set_code", "")
        base_owned   = p.get("base_owned_in_pool", 0)
        base_total   = p.get("base_cards_in_pool", 0)
        owned        = p.get("owned_in_pool", 0)
        total        = p.get("cards_in_pool", 0)
        new_ev       = p.get("new_card_ev_10x", 0.0)
        rare_miss    = p.get("missing_rare_plus", 0)
        rare_ev      = p.get("rare_plus_ev_10x", 0.0)
        cost         = p.get("cost_per_unique_card_10x", 0.0)
        base_str     = f"{base_owned}/{base_total}"
        all_str      = f"{owned}/{total}"
        print(f"  {i:>3}  {set_code:<{col_set}}  {name:<{col_name}}  {base_str:>9}  {all_str:>9}  {rare_miss:>6}  {new_ev:>6.1f}x  {rare_ev:>6.2f}  {cost:{col_cost - 1}.1f}⧗")


def _print_final_summary(show_promo: bool = False, include_limited: bool = False) -> None:
    pack_ev_path  = ROOT / "data" / "current" / "pack_ev.json"
    promo_ev_path = ROOT / "data" / "current" / "promo_pack_ev.json"

    top_pack = None
    print()
    if pack_ev_path.exists():
        try:
            packs = json.loads(pack_ev_path.read_text(encoding="utf-8")).get("packs", [])
            top_pack = max(
                (p for p in packs
                 if not p.get("blocked") and (include_limited or p.get("purchasable", True))),
                key=lambda p: p.get("unified_score", 0), default=None)
            if top_pack:
                missing = top_pack.get("missing_in_pool", "?")
                total   = top_pack.get("cards_in_pool", "?")
                score   = top_pack.get("unified_score", 0)
                print(f"  Top pack:   {top_pack['pack_name']} (unified={score:.4f})"
                      f" — {missing}/{total} cards unowned")
        except Exception:
            pass

    if show_promo and promo_ev_path.exists():
        try:
            top = next((p for p in json.loads(promo_ev_path.read_text(encoding="utf-8")).get("packs", [])
                        if p.get("new_card_ev", 0) > 0), None)
            if top:
                print(f"  Top promo:  {top['pack_name']} (new_ev={top['new_card_ev']:.4f})"
                      f" — Shop Tickets")
        except Exception:
            pass

    stats = _read_player_stats()
    if stats:
        pack_hg = stats.get("pack_hourglasses")
        if pack_hg is not None:
            hg_str = f"  Pack Hourglasses: {pack_hg}"
            if pack_hg >= 120 and top_pack:
                hg_str += f"  → buy 10x {top_pack['pack_name']} (costs 120 ⧗), then re-run"
            print(hg_str)
        if show_promo:
            shop = stats.get("shop_tickets")
            if shop is not None:
                print(f"  Shop Tickets:     {shop}")

    print(f"  Log:        {LOG_FILE.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full recommendation pipeline.")
    parser.add_argument("--skip-sync",    action="store_true")
    parser.add_argument("--login",        action="store_true")
    parser.add_argument("--dry-run-sync", action="store_true")
    parser.add_argument("--json-import",  metavar="FILE", nargs="?", const="auto")
    parser.add_argument("--promo",        action="store_true",
                        help="Also run promo EV and show promo/Shop Ticket summary")
    parser.add_argument("--full-rankings", action="store_true",
                        help="Print all 24 packs ranked to console + write review/full_pack_ranking.md")
    parser.add_argument("--include-limited", action="store_true",
                        help="Include limited-time packs not currently purchasable (e.g. Deluxe Pack: ex)")
    parser.add_argument("--series", choices=["A", "B", "a", "b"], metavar="{A,B}",
                        help="Filter full rankings to A-series or B-series packs only (requires --full-rankings)")
    args = parser.parse_args()

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG_FILE.open("a", encoding="utf-8") as _f:
        _f.write(f"\n{'=' * 60}\nPipeline run: {ts}\n{'=' * 60}\n")

    sync_had_review_items = False
    auth_expired = False
    # Snapshot the pre-sync collection so the post-reconcile delta (compute_sync_delta)
    # is a true before/after diff. Only set when we actually take the snapshot.
    prev_snapshot_taken = False
    print()

    # ── Sync ─────────────────────────────────────────────────────────────
    if not args.skip_sync:
        # Snapshot the collection as it stood before this sync (the previous run's
        # final, reconciled state) for the before/after delta computed post-reconcile.
        _norm_before = ROOT / "data" / "current" / "collection_normalized.json"
        if _norm_before.exists():
            _prev_snapshot = ROOT / "data" / "sync" / ".prev_collection.json"
            _prev_snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_norm_before, _prev_snapshot)
            prev_snapshot_taken = True

        sync_extra: list[str] = []
        if args.json_import:
            if args.json_import == "auto":
                try:
                    json_path = _find_latest_pz_json()
                    print(f"  Auto-detected: {json_path.name}")
                except FileNotFoundError as e:
                    print(f"\n  ERROR: {e}", file=sys.stderr)
                    return 1
            else:
                json_path = Path(args.json_import)
                if not json_path.exists():
                    print(f"\n  ERROR: File not found: {json_path}", file=sys.stderr)
                    return 1
            sync_extra += ["--json-import", str(json_path)]
        elif args.login:
            sync_extra.append("--login")
        if args.dry_run_sync:
            sync_extra.append("--dry-run")
        # Keep the pipeline deterministic and fully offline: new cards absent from
        # card_reference route to the review queue. Run sync standalone (without
        # run_recommendations) for a live coord fetch when adding a brand-new set.
        sync_extra.append("--no-fetch")

        # Proactive heads-up before a ~3–4 week stored session lapses mid-run.
        if not args.json_import and not args.login:
            _age = _auth_age_days()
            if _age is not None and _age >= 21:
                print(f"  ⓘ  Stored auth is {_age:.0f} days old (PZ sessions last ~3–4 weeks) — "
                      "refresh soon:\n     python3 scripts/sync_collection.py --curl-import")

        rc, stdout = _run_with_spinner("Sync collection", "scripts/sync_collection.py", sync_extra or None)

        if args.dry_run_sync:
            print(stdout)
            print("  DRY RUN — stopping before report generation.")
            return 0

        if rc == 1:
            _print_step("Sync collection", rc, "FATAL")
            print("\n  FATAL: Sync failed. Check data/pipeline.log", file=sys.stderr)
            return 1
        if rc == 3:
            _print_step("Sync collection", rc, "BLOCKED — unresolved review queue")
            return 1

        # rc == 4: auth/session expired (recoverable). Don't fail the run — fall back to
        # the existing collection so recommendations still generate, and surface the
        # one-command refresh prominently (sync_collection's message went to the log).
        auth_expired = (rc == 4)
        if auth_expired:
            _print_step("Sync collection", rc, "auth expired — using existing collection")
            print(
                "\n  ⚠  Pokémon Zone auth expired (sessions last ~3–4 weeks). The numbers below\n"
                "     use your existing collection.json. Refresh it in one step:\n"
                "       1. pokemon-zone.com/collection-tracker/ → DevTools → Network →\n"
                "          right-click an 'api/players/mine' request → Copy as cURL\n"
                "       2. python3 scripts/sync_collection.py --curl-import   (reads your clipboard)\n"
                "     …then re-run this command.\n",
                file=sys.stderr,
            )
        elif rc == 2:
            _print_step("Sync collection", 0, f"{_collection_status()} (review items pending)")
            sync_had_review_items = True
        else:
            _print_step("Sync collection", rc, _collection_status())

        # ── Reconcile per-printing coords ──────────────────────────────────
        # Sync can only update existing entries; pulls of a same-name card from a
        # NEW set merge onto the existing entry. Reconcile splits them per printing
        # against the fresh last_sync_raw.json. Idempotent; offline; skipped when
        # sync is skipped or auth expired (a stale raw snapshot must not overwrite
        # newer edits).
        if not auth_expired:
            rc, stdout = _run("Reconcile coords", "scripts/reconcile_coords_from_pz.py",
                              ["--apply", "--no-fetch"])
            # Reconcile recomputes per-coord counts from the raw PZ snapshot and is the
            # authoritative count. Surface its total so a sync/reconcile discrepancy (the
            # dual-location over-count class) is visible in the status, not buried.
            m_tot = re.search(r"total count:\s*(\d+)\s*\(PZ total:\s*(\d+)\)", stdout)
            if rc != 0:
                if m_tot and m_tot.group(1) != m_tot.group(2):
                    # Collection total can't be reconciled with Pokémon Zone — a real
                    # count-integrity failure, not a benign dup/unconfirmed-coord abort.
                    _print_step("Reconcile coords", rc,
                                f"COUNT MISMATCH — collection {m_tot.group(1)} vs PZ "
                                f"{m_tot.group(2)}; not applied (see data/pipeline.log)")
                else:
                    _print_step("Reconcile coords", rc, "WARN — not applied; see data/pipeline.log")
            else:
                tot = f", total={m_tot.group(1)}" if m_tot else ""
                m = re.search(r"re-coorded: (\d+)\s+split: (\d+)", stdout)
                if m and (m.group(1) != "0" or m.group(2) != "0"):
                    _print_step("Reconcile coords", 0,
                                f"re-coorded {m.group(1)}, split {m.group(2)}{tot}")
                else:
                    _print_step("Reconcile coords", 0, f"OK{tot}")
    else:
        print(f"  -  {'Sync collection':<22}  skipped")
        _rq = ROOT / "data" / "sync" / "sync_review_queue.json"
        if _rq.exists():
            try:
                q = json.loads(_rq.read_text(encoding="utf-8"))
                if not q.get("resolved", True) and (q.get("new_cards") or q.get("ambiguous_matches")):
                    sync_had_review_items = True
            except Exception:
                pass

    # ── Assign / normalize collection entries ─────────────────────────────
    # Fills missing set_code/card_number/rarity, strips is_ex, normalizes
    # set_code casing and rarity aliases. Idempotent — safe on every run.
    rc, stdout = _run("Normalize entries", "scripts/assign_collection_coords.py")
    if rc != 0:
        _print_step("Normalize entries", rc, "FATAL — check data/pipeline.log")
        return 1
    _print_step("Normalize entries", rc, "OK")

    # ── Printing groups (multi-expansion dex registration) ────────────────
    # Coords that are the same physical card. Since the 2026-07-29 update one copy
    # registers in the dex under every expansion the card appears in, so EV and the
    # web catalog credit ownership across a group. Derived from reprint_links plus
    # Pokémon Zone's expansionIds, so it has to be rebuilt after a sync refreshes
    # the raw snapshot. Non-fatal: a stale grouping only under-credits.
    rc, _ = _run("Printing groups", "scripts/build_printing_groups.py")
    _print_step("Printing groups", 0 if rc == 0 else rc,
                "OK" if rc == 0 else "WARN — ownership credited per coord only")

    # ── Normalize collection (web-facing artifacts) ───────────────────────
    # Produces collection_normalized.json + collection_summary.json, which the web
    # reads for owned counts. Run BEFORE validation so the collection view is always
    # current after a sync: a validate FATAL below still gates recommendations, but
    # must not leave the web showing a stale collection (the earlier regression where
    # a validate abort skipped this step and froze the displayed count).
    rc, stdout = _run("Normalize collection", "scripts/normalize_current_collection.py")
    if rc != 0:
        _print_step("Normalize collection", rc, "FATAL — check data/pipeline.log")
        return 1
    _print_step("Normalize collection", rc, "OK")

    # ── Reference freshness gate (non-fatal) ──────────────────────────────
    # Card metadata is validated against the frozen card_reference.json. Warn (don't block)
    # if it's stale relative to its source snapshots or older than the cache TTL, so syncs
    # never silently validate against out-of-date metadata (e.g. after a new set drops).
    _fresh_level, _fresh_msg = card_reference_freshness(CARD_REF_JSON, SOURCES_DIR)
    if _fresh_level == "ok":
        _print_step("Reference freshness", 0, _fresh_msg or "OK")
    else:
        _print_step("Reference freshness", 1, f"WARN — {_fresh_msg}")

    # ── Validate coords against card_reference.json (offline, 3-source validated) ──
    # Run offline (--no-fetch) so the pipeline stays headless and deterministic.
    # card_reference.json covers all 20 sets (Bulbapedia + Serebii + TCGdex where
    # available). Exit codes: 2 = serious coord error → FATAL; 1 = advisory HP diff
    # (WARN, don't block); 0 = clean.
    rc, stdout = _run("Validate coords", "scripts/validate_collection_coords.py",
                      ["--no-fetch"])
    if rc >= 2:
        _print_step("Validate coords", rc, "FATAL — serious coord error (see data/pipeline.log)")
        return 1
    elif rc == 1:
        _print_step("Validate coords", rc, "WARN — advisory HP diff(s); see data/pipeline.log")
    else:
        # Surface owned cards whose printing isn't fully cross-validated (single-source /
        # cross-set conflict). validate_collection_coords already lists each one in the log;
        # echo the count here so it's visible without log-diving.
        m = re.search(r"single:\s*(\d+),\s*conflict:\s*(\d+)", stdout)
        n_low = (int(m.group(1)) + int(m.group(2))) if m else 0
        status = ("OK" if not n_low
                  else f"OK — {n_low} owned card(s) <confirmed; verify printing (see data/pipeline.log)")
        _print_step("Validate coords", rc, status)

    # ── Validate ──────────────────────────────────────────────────────────
    rc, stdout = _run("Validate collection", "scripts/validate_current_collection.py",
                      ["--expected-total", _read_meta_total()])
    if rc != 0:
        _print_step("Validate collection", rc, "FATAL — check data/pipeline.log")
        return 1
    m = re.search(r"VALIDATION PASSED\s*\((.+?)\)", stdout)
    _print_step("Validate collection", rc, m.group(1) if m else "OK")

    # ── Sync delta ────────────────────────────────────────────────────────
    # Compute "added since last sync" from the pre-sync snapshot vs the final
    # (reconciled, normalized) collection — see scripts/compute_sync_delta.py.
    # Skipped on --skip-sync and on auth-expired (collection unchanged), so the
    # last real sync's delta is preserved.
    if prev_snapshot_taken and not auth_expired:
        rc, _ = _run("Sync delta", "scripts/compute_sync_delta.py")
        _print_step("Sync delta", rc, "OK" if rc == 0 else "WARN — see data/pipeline.log")

    # ── EV pipeline ───────────────────────────────────────────────────────
    for label, script in PIPELINE_STEPS:
        extra: list[str] | None = None
        if label == "Build pack EV" and args.promo:
            # Run promo EV immediately after pack EV, before recommendations
            rc, stdout = _run(label, script)
            if rc != 0:
                _print_step(label, rc, "FATAL — check data/pipeline.log")
                return 1
            _print_step(label, rc, _extract_status(label, stdout))

            rc, stdout = _run("Build promo EV", "scripts/build_promo_pack_ev.py")
            if rc != 0:
                _print_step("Build promo EV", rc, "FATAL — check data/pipeline.log")
                return 1
            _print_step("Build promo EV", rc, _extract_status("Build promo EV", stdout))
            continue

        if label == "Recommendations":
            extra = []
            if not args.promo:
                extra.append("--no-promo")
            if args.full_rankings:
                extra.append("--full-rankings")
            if args.include_limited:
                extra.append("--include-limited")
            extra = extra or None

        rc, stdout = _run(label, script, extra)
        if rc != 0:
            _print_step(label, rc, "FATAL — check data/pipeline.log")
            return 1
        _print_step(label, rc, _extract_status(label, stdout))

    _print_final_summary(show_promo=args.promo, include_limited=args.include_limited)

    if args.full_rankings:
        _print_full_rankings(include_limited=args.include_limited, series=args.series)

    if sync_had_review_items:
        print(f"\n  NOTE: Review queue has items. See: data/sync/sync_review_queue.json")

    # Cosmetic: collapse this run in the log if it was identical to the previous one.
    _collapse_repeated_run()

    # Auth expiry outranks review items: the numbers above came from a stale
    # collection, and callers (web sync runner) must not report a clean sync.
    if auth_expired:
        return EXIT_AUTH_EXPIRED
    return EXIT_REVIEW_ITEMS if sync_had_review_items else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
