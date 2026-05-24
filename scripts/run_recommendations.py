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
    python3 scripts/run_recommendations.py --full-ranking          # write review/full_pack_ranking.md with descriptions

Exit codes:
    0  Full pipeline completed
    1  Fatal error in any step
    2  Sync had review items; pipeline ran with existing collection.json
"""

import argparse
import itertools
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "data" / "pipeline.log"

PIPELINE_STEPS = [
    ("Build pack EV",        "scripts/build_pack_ev.py"),
    ("Recommendations",      "scripts/generate_pack_recommendation_report.py"),
    ("Spending plan",        "scripts/generate_hourglass_spending_plan.py"),
]

_STATUS_PATTERNS: dict[str, tuple] = {
    "Build pack EV":        (r"Packs scored:\s*(\d+)", lambda m: f"{m.group(1)} packs"),
    "Build promo EV":       (r"Promo packs in PZ data:\s*(\d+)", lambda m: f"{m.group(1)} promo packs"),
}


def _append_log(label: str, output: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 60}\n[{ts}] {label}\n{'=' * 60}\n")
        f.write(output)
        if not output.endswith("\n"):
            f.write("\n")


def _extract_status(label: str, stdout: str) -> str:
    entry = _STATUS_PATTERNS.get(label)
    if not entry:
        return "OK"
    pattern, fmt = entry
    m = re.search(pattern, stdout)
    return fmt(m) if m else "OK"


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


def _read_meta_total() -> str:
    try:
        raw = (ROOT / "collection.json").read_text(encoding="utf-8")
        cleaned = re.sub(r"//[^\n]*", "", raw)
        data = json.loads(cleaned)
        return str(data.get("meta", {}).get("total_cards", 380))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "0"


def _collection_status() -> str:
    """Read total/unique from collection.json for the sync status line."""
    try:
        raw = (ROOT / "collection.json").read_text(encoding="utf-8")
        cleaned = re.sub(r"//[^\n]*", "", raw)
        data = json.loads(cleaned)
        meta = data.get("meta", {})
        total = meta.get("total_cards", "?")
        unique = len(data.get("collection", []))
        return f"{total} cards, {unique} unique"
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


def _print_final_summary(show_promo: bool = False) -> None:
    pack_ev_path  = ROOT / "data" / "current" / "pack_ev.json"
    promo_ev_path = ROOT / "data" / "current" / "promo_pack_ev.json"

    top_pack = None
    print()
    if pack_ev_path.exists():
        try:
            packs = json.loads(pack_ev_path.read_text(encoding="utf-8")).get("packs", [])
            top_pack = max((p for p in packs if not p.get("blocked")),
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
    parser.add_argument("--full-ranking", action="store_true",
                        help="Write review/full_pack_ranking.md with descriptions for all 24 packs")
    args = parser.parse_args()

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG_FILE.open("a", encoding="utf-8") as _f:
        _f.write(f"\n{'=' * 60}\nPipeline run: {ts}\n{'=' * 60}\n")

    sync_had_review_items = False
    print()

    # ── Sync ─────────────────────────────────────────────────────────────
    if not args.skip_sync:
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
        if rc == 2:
            _print_step("Sync collection", 0, f"{_collection_status()} (review items pending)")
            sync_had_review_items = True
        else:
            _print_step("Sync collection", rc, _collection_status())
    else:
        print(f"  -  {'Sync collection':<22}  skipped")

    # ── Validate ──────────────────────────────────────────────────────────
    rc, stdout = _run("Validate collection", "scripts/validate_current_collection.py",
                      ["--expected-total", _read_meta_total()])
    if rc != 0:
        _print_step("Validate collection", rc, "FATAL — check data/pipeline.log")
        return 1
    m = re.search(r"VALIDATION PASSED\s*\((.+?)\)", stdout)
    _print_step("Validate collection", rc, m.group(1) if m else "OK")

    # ── Normalize ─────────────────────────────────────────────────────────
    rc, stdout = _run("Normalize collection", "scripts/normalize_current_collection.py")
    if rc != 0:
        _print_step("Normalize collection", rc, "FATAL — check data/pipeline.log")
        return 1
    _print_step("Normalize collection", rc, "OK")

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
            if args.full_ranking:
                extra.append("--full-ranking")
            extra = extra or None

        rc, stdout = _run(label, script, extra)
        if rc != 0:
            _print_step(label, rc, "FATAL — check data/pipeline.log")
            return 1
        _print_step(label, rc, _extract_status(label, stdout))

    _print_final_summary(show_promo=args.promo)

    if sync_had_review_items:
        print(f"\n  NOTE: Review queue has items. See: data/sync/sync_review_queue.json")

    return 2 if sync_had_review_items else 0


if __name__ == "__main__":
    sys.exit(main())
