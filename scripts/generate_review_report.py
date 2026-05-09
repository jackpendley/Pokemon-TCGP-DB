#!/usr/bin/env python3
"""
Generate human-readable review files from OCR + match candidate data.

Reads:   data/extraction/crop_manifest.json
         data/extraction/ocr_results.json
         data/extraction/match_candidates.json
Outputs: review/review_needed.md
         review/extraction_candidates.csv

Usage:
    python3 scripts/generate_review_report.py
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_FILE = Path("data/extraction/crop_manifest.json")
OCR_FILE = Path("data/extraction/ocr_results.json")
MATCH_FILE = Path("data/extraction/match_candidates.json")

REVIEW_DIR = Path("review")
REVIEW_MD = REVIEW_DIR / "review_needed.md"
REVIEW_CSV = REVIEW_DIR / "extraction_candidates.csv"


def load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"ERROR: {label} not found at {path}.")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    manifest = load_json(MANIFEST_FILE, "crop_manifest.json")
    ocr_data = load_json(OCR_FILE, "ocr_results.json")
    match_data = load_json(MATCH_FILE, "match_candidates.json")

    # Build lookup dicts keyed by crop_id
    ocr_by_id = {r["crop_id"]: r for r in ocr_data.get("results", [])}
    match_by_id = {c["crop_id"]: c for c in match_data.get("candidates", [])}

    # Flatten all crops from manifest in order
    all_rows = []
    for ss in manifest.get("screenshots", []):
        for crop in ss.get("crops", []):
            cid = crop["crop_id"]
            ocr = ocr_by_id.get(cid, {})
            match = match_by_id.get(cid, {})
            top_matches = match.get("top_matches", [])
            best = top_matches[0] if top_matches else {}
            all_rows.append({
                "crop_id": cid,
                "screenshot": crop["screenshot"],
                "row": crop["row"],
                "col": crop["col"],
                "ocr_guess": ocr.get("cleaned_title_guess", ""),
                "ocr_conf": ocr.get("confidence", 0.0),
                "best_match_name": best.get("name", ""),
                "best_match_score": best.get("score", 0),
                "suggested_card_name": match.get("suggested_card_name", ""),
                "needs_review": match.get("needs_review", True),
                "reason": match.get("reason", ""),
                "top_matches_json": json.dumps(top_matches),
            })

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # --- CSV: all crops ---
    csv_fields = [
        "crop_id", "screenshot", "row", "col",
        "ocr_guess", "ocr_conf",
        "best_match_name", "best_match_score",
        "suggested_card_name", "needs_review", "reason",
        "top_matches_json",
    ]
    with REVIEW_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"CSV  →  {REVIEW_CSV}  ({len(all_rows)} rows)")

    # --- Markdown: only review-needed crops, grouped by screenshot ---
    needs_review = [r for r in all_rows if r["needs_review"]]
    by_screenshot: dict[str, list] = {}
    for r in needs_review:
        by_screenshot.setdefault(r["screenshot"], []).append(r)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Extraction Review Report",
        "",
        f"Generated: {now}",
        "",
        f"**Total crops:** {len(all_rows)}  ",
        f"**Auto-matched:** {len(all_rows) - len(needs_review)}  ",
        f"**Needs review:** {len(needs_review)}",
        "",
        "---",
        "",
    ]

    if not needs_review:
        lines += ["All crops were auto-matched above threshold. No manual review needed.", ""]
    else:
        for screenshot, crops in by_screenshot.items():
            lines += [f"## {screenshot}", ""]
            for c in crops:
                lines += [
                    f"### `{c['crop_id']}` (row {c['row']}, col {c['col']})",
                    "",
                    f"- **OCR guess:** `{c['ocr_guess'] or '(empty)'}` (conf {c['ocr_conf']:.2f})",
                    f"- **Best match:** `{c['best_match_name']}` (score {c['best_match_score']})",
                    f"- **Reason:** {c['reason']}",
                    "",
                    "**Action needed:** Open the crop file and confirm the card name:",
                    f"  `crops/{Path(c['screenshot']).stem}/{c['row']}{c['col'].replace('col', 'c')}.png`",
                    "",
                    "Top candidates:",
                ]
                try:
                    top = json.loads(c["top_matches_json"])
                    for t in top:
                        lines.append(f"  - `{t['name']}` — score {t['score']}")
                except Exception:
                    lines.append("  *(no candidates)*")
                lines.append("")

    REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"MD   →  {REVIEW_MD}  ({len(needs_review)} crops need review)")


if __name__ == "__main__":
    main()
