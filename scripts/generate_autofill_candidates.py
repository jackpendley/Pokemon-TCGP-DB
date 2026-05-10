#!/usr/bin/env python3
"""
Generate conservative autofill candidates for unconfirmed screenshot crops.

Reads:   data/extraction/match_candidates.json
         batches/cards_batch_*.json              (to identify already-confirmed crops)
         data/extraction/detection_validation_report.json  (optional)
Outputs: review/autofill_candidates.csv
         review/autofill_candidates.md

Autofill rules (conservative):
  auto_fill=true  if score >= 95
  auto_fill=true  if score >= 90 AND best_ocr_source contains the suggested name (case-insensitive)
  auto_fill=false otherwise

Usage:
    python3 scripts/generate_autofill_candidates.py
"""

import csv
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

MATCH_FILE = Path("data/extraction/match_candidates.json")
VALIDATION_REPORT = Path("data/extraction/detection_validation_report.json")
BATCHES_GLOB = "batches/cards_batch_*.json"
OUT_CSV = Path("review/autofill_candidates.csv")
OUT_MD = Path("review/autofill_candidates.md")

AUTOFILL_SCORE_HIGH = 95    # always autofill
AUTOFILL_SCORE_MED = 90     # autofill only if OCR source contains the name


def crop_id_from_entry(entry: dict) -> str:
    stem = entry["source_screenshot"].replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{entry['source_row']}c{entry['source_column']}"


def main():
    if not MATCH_FILE.exists():
        print(f"ERROR: {MATCH_FILE} not found. Run match_ocr_to_reference.py first.")
        return

    # Build set of confirmed crop_ids
    confirmed_ids: set = set()
    for bf in sorted(glob.glob(BATCHES_GLOB)):
        batch = json.loads(Path(bf).read_text(encoding="utf-8"))
        for entry in batch:
            confirmed_ids.add(crop_id_from_entry(entry))

    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
    candidates = mc_data.get("candidates", [])

    # Load validation report summary if available
    val_summary = None
    if VALIDATION_REPORT.exists():
        val_data = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
        val_summary = val_data.get("summary", {})

    rows = []
    autofill_count = 0

    for c in candidates:
        crop_id = c["crop_id"]
        if crop_id in confirmed_ids:
            continue   # already confirmed

        top_matches = c.get("top_matches", [])
        suggested = c.get("suggested_card_name")
        best_ocr_source = c.get("best_ocr_source", "")
        score = top_matches[0]["score"] if top_matches else 0
        top3 = "; ".join(
            f"{m['name']} ({m['score']:.0f})" for m in top_matches
        )

        # Parse screenshot / row / col from crop_id
        # Format: IMG_1528_r1c1
        parts = crop_id.rsplit("_", 1)
        screenshot = parts[0].replace("IMG_", "IMG_") + ".PNG" if len(parts) == 2 else crop_id
        rowcol = parts[1] if len(parts) == 2 else ""
        row = rowcol[1] if len(rowcol) >= 2 else ""
        col = rowcol[3] if len(rowcol) >= 4 else ""

        # Autofill decision
        name_in_ocr = (
            suggested is not None
            and suggested.lower() in best_ocr_source.lower()
        )

        if suggested and score >= AUTOFILL_SCORE_HIGH:
            auto_fill = True
            reason = f"score {score:.0f} >= {AUTOFILL_SCORE_HIGH}"
        elif suggested and score >= AUTOFILL_SCORE_MED and name_in_ocr:
            auto_fill = True
            reason = f"score {score:.0f} >= {AUTOFILL_SCORE_MED} and name in OCR"
        else:
            auto_fill = False
            reason = f"score {score:.0f} below threshold" if not suggested else f"score {score:.0f} < {AUTOFILL_SCORE_MED} or name not in OCR"

        if auto_fill:
            autofill_count += 1

        rows.append({
            "screenshot": screenshot,
            "row": row,
            "column": col,
            "crop_id": crop_id,
            "auto_fill": str(auto_fill),
            "proposed_card_name": suggested or "",
            "score": f"{score:.1f}",
            "top_3": top3,
            "reason": reason,
        })

    # Write CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["screenshot", "row", "column", "crop_id", "auto_fill",
                  "proposed_card_name", "score", "top_3", "reason"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Write Markdown
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    md_lines = [
        "# Autofill Candidates",
        "",
        f"Generated: {now}",
        f"Confirmed crops excluded: {len(confirmed_ids)}",
        f"Unconfirmed crops evaluated: {len(rows)}",
        f"Auto-fill eligible: {autofill_count}",
        "",
    ]
    if val_summary:
        md_lines += [
            "## Validation Context",
            "",
            f"- Confirmed-set top-1 accuracy: {val_summary.get('top1_accuracy', 0):.1%}",
            f"- Confirmed-set top-3 accuracy: {val_summary.get('top3_accuracy', 0):.1%}",
            f"- Avg score when correct: {val_summary.get('avg_score_when_correct', 0)}",
            "",
        ]
    md_lines += [
        "## Auto-Fill Eligible (score ≥ 95, or ≥ 90 with name in OCR)",
        "",
        "| Crop ID | Proposed Name | Score | Reason |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if r["auto_fill"] == "True":
            md_lines.append(
                f"| {r['crop_id']} | {r['proposed_card_name']} | {r['score']} | {r['reason']} |"
            )
    md_lines += [
        "",
        "## Needs Human Review",
        "",
        "| Crop ID | Top Match | Score | Top 3 Candidates |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if r["auto_fill"] != "True":
            md_lines.append(
                f"| {r['crop_id']} | {r['proposed_card_name'] or '—'} | {r['score']} | {r['top_3'] or '—'} |"
            )

    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Unconfirmed crops   : {len(rows)}")
    print(f"Auto-fill eligible  : {autofill_count}")
    print(f"Needs human review  : {len(rows) - autofill_count}")
    print(f"CSV → {OUT_CSV}")
    print(f"MD  → {OUT_MD}")


if __name__ == "__main__":
    main()
