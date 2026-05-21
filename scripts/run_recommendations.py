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

Exit codes:
    0  Full pipeline completed
    1  Fatal error in any step
    2  Sync had review items; pipeline ran with existing collection.json
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PIPELINE_STEPS = [
    ("Resolve pack sources",     "scripts/resolve_ambiguous_pack_sources.py"),
    ("Build pack EV",            "scripts/build_pack_ev.py"),
    ("Generate recommendations", "scripts/generate_pack_recommendation_report.py"),
    ("Generate spending plan",   "scripts/generate_hourglass_spending_plan.py"),
]


def run(label: str, script: str, extra_args: list[str] | None = None) -> int:
    cmd = [sys.executable, script] + (extra_args or [])
    print(f"\n{'─' * 55}")
    print(f"  {label}")
    print(f"{'─' * 55}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def _find_latest_pz_json() -> Path:
    """Return the newest pz_collection*.json in ~/Downloads."""
    downloads = Path.home() / "Downloads"
    candidates = sorted(downloads.glob("pz_collection*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(
            "No pz_collection*.json found in ~/Downloads.\n"
            "Click the 'PZ Sync' bookmarklet on pokemon-zone.com/collection-tracker/ first."
        )
    latest = candidates[-1]
    print(f"  Auto-detected: {latest.name}", flush=True)
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full recommendation pipeline.")
    parser.add_argument("--skip-sync",    action="store_true", help="Skip Pokemon Zone sync")
    parser.add_argument("--login",        action="store_true", help="Re-auth browser before sync")
    parser.add_argument("--dry-run-sync", action="store_true", help="Show sync diff only, stop before reports")
    parser.add_argument(
        "--json-import", metavar="FILE", nargs="?", const="auto",
        help="Import from bookmarklet JSON (omit FILE to auto-detect newest ~/Downloads/pz_collection*.json)",
    )
    args = parser.parse_args()

    sync_had_review_items = False

    # ── Step 1: Sync ──────────────────────────────────────────────────────
    if not args.skip_sync:
        sync_extra: list[str] = []

        if args.json_import:
            # Bookmarklet path: resolve file, then pass to sync script
            if args.json_import == "auto":
                try:
                    json_path = _find_latest_pz_json()
                except FileNotFoundError as e:
                    print(f"\nERROR: {e}", file=sys.stderr)
                    return 1
            else:
                json_path = Path(args.json_import)
                if not json_path.exists():
                    print(f"\nERROR: File not found: {json_path}", file=sys.stderr)
                    return 1
            sync_extra += ["--json-import", str(json_path)]
        elif args.login:
            sync_extra.append("--login")

        if args.dry_run_sync:
            sync_extra.append("--dry-run")

        rc = run("Sync collection from Pokemon Zone", "scripts/sync_collection.py",
                 sync_extra or None)

        if args.dry_run_sync:
            print("\nDRY RUN SYNC complete — stopping before report generation.")
            return 0

        if rc == 1:
            print("\nFATAL: Sync failed. Pipeline aborted.", file=sys.stderr)
            return 1
        if rc == 3:
            print("\nBLOCKED: Unresolved review queue. Run --skip-sync or resolve queue first.",
                  file=sys.stderr)
            return 1
        if rc == 2:
            print("\nNOTE: Sync completed with review items. Pipeline continuing with current collection.")
            sync_had_review_items = True
    else:
        print("Skipping sync — using current collection.json")

    # ── Step 2: Validate ──────────────────────────────────────────────────
    rc = run("Validate collection", "scripts/validate_current_collection.py",
             ["--expected-total", _read_meta_total()])
    if rc != 0:
        print("\nFATAL: Validation failed. Pipeline aborted.", file=sys.stderr)
        return 1

    # ── Step 3: Normalize ─────────────────────────────────────────────────
    rc = run("Normalize collection", "scripts/normalize_current_collection.py")
    if rc != 0:
        print("\nFATAL: Normalize failed. Pipeline aborted.", file=sys.stderr)
        return 1

    # ── Steps 4-7: EV pipeline ────────────────────────────────────────────
    for label, script in PIPELINE_STEPS:
        rc = run(label, script)
        if rc != 0:
            print(f"\nFATAL: '{label}' failed. Pipeline aborted.", file=sys.stderr)
            return 1

    # ── Done ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print("  Pipeline complete.")
    print(f"  Reports: review/inferred_pack_recommendations.md")
    print(f"           review/final_hourglass_spending_plan.md")
    print(f"           review/pack_ev.md")
    if sync_had_review_items:
        print(f"\n  NOTE: Review queue has items requiring attention.")
        print(f"        See: data/sync/sync_review_queue.json")
    print(f"{'=' * 55}\n")

    return 2 if sync_had_review_items else 0


def _read_meta_total() -> str:
    """Read meta.total_cards from collection.json for the validate step."""
    import json, re
    raw = (ROOT / "collection.json").read_text(encoding="utf-8")
    cleaned = re.sub(r"//[^\n]*", "", raw)
    data = json.loads(cleaned)
    return str(data.get("meta", {}).get("total_cards", 380))


if __name__ == "__main__":
    sys.exit(main())
