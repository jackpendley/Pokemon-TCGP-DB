#!/usr/bin/env python3
"""
Compute last_sync_delta.json from a before/after collection diff.

Run by run_recommendations.py AFTER the pipeline has produced the final
collection_normalized.json (post sync + reconcile + normalize). Diffing the
pre-sync snapshot (data/sync/.prev_collection.json) against the final collection
makes the delta reflect what actually changed per printing.

This replaces the matcher-derived delta sync_collection.py used to write: the
matcher aggregates a same-name pull (e.g. an Illustration Rare) onto an existing
base-coord entry, and reconcile_coords_from_pz.py only splits that into its own
entry afterward — so a delta written mid-sync mislabels new alt-art cards as
copies of the base. A pure before/after collection diff is immune to that.
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sync_collection import SYNC_DIR, SYNC_DELTA, append_sync_history

PREV_SNAPSHOT = SYNC_DIR / ".prev_collection.json"
COLLECTION_NORMALIZED = ROOT / "data" / "current" / "collection_normalized.json"


def _counts_by_coord(entries: list) -> dict:
    """Map (SET_CODE_UPPER, card_number) → {name, set_code, card_number, count}."""
    out: dict = {}
    for e in entries:
        cn = e.get("card_number")
        if cn is None:
            continue
        sc = str(e.get("set_code", "")).upper()
        out[(sc, cn)] = {
            "name": e.get("name"),
            "set_code": e.get("set_code"),
            "card_number": cn,
            "count": e.get("count", 0),
        }
    return out


def build_delta(prev: dict, curr: dict) -> dict:
    """Per-coord additions (count increases + brand-new coords). Decreases/removals
    are ignored, matching the previous delta's "what was added" scope."""
    added = []
    for coord, info in curr.items():
        prev_count = prev.get(coord, {}).get("count", 0)
        new_count = info["count"]
        if new_count > prev_count:
            added.append({
                "name": info["name"],
                "set_code": info["set_code"],
                "card_number": info["card_number"],
                "previous_count": prev_count,
                "new_count": new_count,
                "added": new_count - prev_count,
                "is_new": prev_count == 0,
            })
    # New cards first, then by coord — stable, readable order.
    added.sort(key=lambda e: (not e["is_new"], str(e["set_code"]), e["card_number"]))
    return {
        "generated_at": date.today().isoformat(),
        "added_count": len(added),
        "added": added,
    }


def _load_collection(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("collection", []) if isinstance(data, dict) else data


def main() -> int:
    if not COLLECTION_NORMALIZED.exists():
        print("  Sync delta: no collection_normalized.json — skipped.")
        return 0

    curr = _counts_by_coord(_load_collection(COLLECTION_NORMALIZED))

    if not PREV_SNAPSHOT.exists():
        # No baseline (first run): don't report the whole collection as "new".
        delta = {"generated_at": date.today().isoformat(), "added_count": 0, "added": []}
    else:
        prev = _counts_by_coord(_load_collection(PREV_SNAPSHOT))
        delta = build_delta(prev, curr)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_DELTA.write_text(
        json.dumps(delta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    append_sync_history(delta)
    print(f"  Sync delta: {delta['added_count']} card(s) added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
