#!/usr/bin/env python3
"""
Summarize all draft batch JSON files in batches/*_DRAFT.json.

Outputs:
    review/draft_batch_summary.md

Usage:
    python3 scripts/summarize_draft_batches.py
"""

import glob
import json
from datetime import datetime, timezone
from pathlib import Path

DRAFT_GLOB = "batches/*_DRAFT.json"
OUT_MD = Path("review/draft_batch_summary.md")


def main() -> None:
    draft_files = sorted(glob.glob(DRAFT_GLOB))
    if not draft_files:
        print("No draft batch files found.")
        return

    total_entries = 0
    total_unknown = 0
    total_candidates = 0
    total_prefilled = 0
    total_qty_placeholders = 0
    total_needs_review = 0

    per_screenshot: list[dict] = []

    for df in draft_files:
        data = json.loads(Path(df).read_text(encoding="utf-8"))
        ss = data[0]["source_screenshot"] if data else "unknown"
        n = len(data)
        unknown = sum(1 for e in data if e["card_name"].startswith("UNKNOWN_"))
        candidates = sum(1 for e in data
                         if not e["card_name"].startswith("UNKNOWN_")
                         and "auto_draft_candidate" in e.get("variant_notes", ""))
        prefilled = sum(1 for e in data
                        if not e["card_name"].startswith("UNKNOWN_")
                        and "auto_draft_candidate" not in e.get("variant_notes", ""))
        qty_zero = sum(1 for e in data if e["quantity"] == 0)
        needs_rev = sum(1 for e in data if e["needs_review"])

        total_entries += n
        total_unknown += unknown
        total_candidates += candidates
        total_prefilled += prefilled
        total_qty_placeholders += qty_zero
        total_needs_review += needs_rev

        per_screenshot.append({
            "file": df,
            "screenshot": ss,
            "entries": n,
            "prefilled": prefilled,
            "candidates": candidates,
            "unknown": unknown,
            "qty_zero": qty_zero,
            "needs_review": needs_rev,
        })

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Draft Batch Summary",
        "",
        f"Generated: {now}",
        f"Draft files: {len(draft_files)}",
        "",
        "## Totals",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Total draft entries | {total_entries} |",
        f"| Prefilled names (autofill) | {total_prefilled} |",
        f"| Candidate names (score ≥ 80) | {total_candidates} |",
        f"| UNKNOWN names (need ID) | {total_unknown} |",
        f"| Quantity placeholders (qty=0) | {total_qty_placeholders} |",
        f"| Entries needing review | {total_needs_review} |",
        "",
        "## Action Required",
        "",
        f"- **{total_unknown} rows** have UNKNOWN card names — open the contact sheet and identify visually.",
        f"- **{total_candidates} rows** have candidate names (score ≥ 80) — verify against the contact sheet.",
        f"- **{total_qty_placeholders} rows** have quantity=0 — read the actual quantity from the app.",
        f"- Once all rows in a draft CSV are confirmed, save as a non-DRAFT confirmed CSV and run:",
        "  ```bash",
        "  python3 scripts/validate_confirmed_csv_against_reference.py --input review/confirmed/IMG_XXXX_confirmed.csv",
        "  python3 scripts/create_batch_from_confirmation.py --input ... --screenshot ... --output batches/cards_batch_NNN.json",
        "  python3 scripts/validate_batch.py batches/cards_batch_NNN.json",
        "  ```",
        "",
        "## Per-Screenshot Draft Summary",
        "",
        "| File | Screenshot | Entries | Prefilled | Candidates | UNKNOWN | Qty=0 | Needs Review |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for s in per_screenshot:
        lines.append(
            f"| {Path(s['file']).name} | {s['screenshot']} | {s['entries']} "
            f"| {s['prefilled']} | {s['candidates']} | {s['unknown']} "
            f"| {s['qty_zero']} | {s['needs_review']} |"
        )

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Draft files    : {len(draft_files)}")
    print(f"Total entries  : {total_entries}")
    print(f"  Prefilled    : {total_prefilled}")
    print(f"  Candidates   : {total_candidates}")
    print(f"  UNKNOWN      : {total_unknown}")
    print(f"  Qty=0        : {total_qty_placeholders}")
    print(f"  Needs review : {total_needs_review}")
    print(f"MD → {OUT_MD}")


if __name__ == "__main__":
    main()
