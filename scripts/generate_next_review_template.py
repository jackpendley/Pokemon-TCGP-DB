#!/usr/bin/env python3
"""
Generate a partially prefilled review template CSV for the next screenshot.

Uses available automation (autofill candidates, field detection results) to
prefill high-confidence fields. User must verify and fill remaining fields
before creating a batch file.

Reads:   data/extraction/match_candidates.json
         review/autofill_candidates.csv          (if present)
         data/extraction/field_detection_report.json  (if present)
Outputs: review/confirmed/<stem>_confirmed_TEMPLATE.csv

Usage:
    python3 scripts/generate_next_review_template.py \
        --screenshot IMG_1530.PNG \
        --output review/confirmed/IMG_1530_confirmed_TEMPLATE.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

MATCH_FILE = Path("data/extraction/match_candidates.json")
AUTOFILL_CSV = Path("review/autofill_candidates.csv")
FIELD_REPORT = Path("data/extraction/field_detection_report.json")
EXT_REF = Path("data/reference/external/external_card_reference.json")

POSITIONS = [(r, c) for r in (1, 2, 3) for c in (1, 2, 3)]

# Thresholds matching generate_autofill_candidates.py
AUTOFILL_HIGH = 95
AUTOFILL_MED = 90


def crop_id(screenshot: str, row: int, col: int) -> str:
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{row}c{col}"


def load_ext_ref_by_name(path: Path) -> dict[str, dict]:
    """Load external reference → dict normalized_name → card record."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    result: dict[str, dict] = {}
    for entry in data:
        n = entry.get("name", "").strip()
        if n:
            key = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", n.lower())).strip()
            if key not in result:
                result[key] = entry
    return result


def normalize_for_lookup(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", name.lower())).strip()


def is_ex_from_name(name: str) -> bool:
    if not name:
        return False
    n = name.strip().lower()
    return bool(re.search(r"\bex\b", n) or re.match(r"^mega\s", n))


def main():
    parser = argparse.ArgumentParser(
        description="Generate a prefilled review template for the next screenshot."
    )
    parser.add_argument("--screenshot", required=True, help="Screenshot filename, e.g. IMG_1530.PNG")
    parser.add_argument("--output", required=True, help="Output CSV path")
    args = parser.parse_args()

    screenshot = args.screenshot
    out_path = Path(args.output)

    if not MATCH_FILE.exists():
        print(f"ERROR: {MATCH_FILE} not found. Run match_ocr_to_reference.py first.")
        sys.exit(1)

    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
    mc_by_id = {c["crop_id"]: c for c in mc_data.get("candidates", [])}

    # Load autofill candidates
    autofill_by_id: dict = {}
    if AUTOFILL_CSV.exists():
        with AUTOFILL_CSV.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                autofill_by_id[row["crop_id"]] = row

    # Load field detection report
    field_report = {}
    if FIELD_REPORT.exists():
        field_report = json.loads(FIELD_REPORT.read_text(encoding="utf-8"))

    qty_accuracy = field_report.get("quantity", {}).get("accuracy", 0)
    ex_accuracy = field_report.get("is_ex", {}).get("accuracy", 0)
    qty_usable = qty_accuracy >= 0.6
    ex_usable = ex_accuracy >= 0.85

    # Load external reference for metadata hints
    ext_ref = load_ext_ref_by_name(EXT_REF)
    ext_available = bool(ext_ref)

    output_rows = []

    for row, col in POSITIONS:
        cid = crop_id(screenshot, row, col)
        mc = mc_by_id.get(cid, {})
        af = autofill_by_id.get(cid, {})

        top_matches = mc.get("top_matches", [])
        suggested = mc.get("suggested_card_name")
        top1_score = top_matches[0]["score"] if top_matches else 0
        best_ocr = mc.get("best_ocr_source", "")

        name_in_ocr = (
            suggested is not None
            and suggested.lower() in best_ocr.lower()
        ) if suggested else False

        # Determine card_name prefill
        card_name = ""
        name_notes = []

        if af.get("auto_fill") == "True":
            card_name = af.get("proposed_card_name", "")
            name_notes.append(f"autofill_score_{int(float(af.get('score', 0)))}; user_verify")
        elif top1_score >= AUTOFILL_HIGH and suggested:
            card_name = suggested
            name_notes.append(f"candidate_score_{int(top1_score)}; user_verify")
        elif top1_score >= AUTOFILL_MED and name_in_ocr and suggested:
            card_name = suggested
            name_notes.append(f"candidate_score_{int(top1_score)}_ocr_match; user_verify")
        elif top1_score >= 65 and suggested:
            name_notes.append(f"low_candidate={suggested}({int(top1_score)}); user_identify")
        else:
            top3_str = "; ".join(
                f"{m['name']}({int(m['score'])})" for m in top_matches[:3]
            )
            if top3_str:
                name_notes.append(f"top3={top3_str}; user_identify")
            else:
                name_notes.append("no_ocr_text; user_identify")

        # Add external reference metadata hints for high-confidence candidates
        if ext_available and (card_name or (top1_score >= 65 and suggested)):
            lookup_name = card_name if card_name else suggested
            if lookup_name:
                ext_rec = ext_ref.get(normalize_for_lookup(lookup_name))
                if ext_rec:
                    ext_hints = []
                    if ext_rec.get("is_ex"):
                        ext_hints.append("ext:is_ex=true")
                    cat = ext_rec.get("card_category")
                    if cat and cat not in ("Pokemon", "Unknown"):
                        ext_hints.append(f"ext:category={cat}")
                    stage = ext_rec.get("stage")
                    if stage and stage not in ("Unknown", "None"):
                        ext_hints.append(f"ext:stage={stage}")
                    if ext_hints:
                        name_notes.append("; ".join(ext_hints))

        # Determine is_ex prefill
        is_ex = ""
        if card_name and ex_usable:
            pred = is_ex_from_name(card_name)
            is_ex = "true" if pred else "false"
            if pred:
                name_notes.append("is_ex=true from name pattern")
        elif card_name:
            is_ex = "false"
            name_notes.append("is_ex=false assumed; verify")

        notes = "; ".join(name_notes)

        output_rows.append({
            "screenshot": screenshot,
            "row": str(row),
            "column": str(col),
            "card_name": card_name,
            "quantity": "",
            "special_type": "unknown",
            "is_ex": is_ex,
            "notes": notes,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["screenshot", "row", "column", "card_name", "quantity",
                  "special_type", "is_ex", "notes"]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    prefilled_names = sum(1 for r in output_rows if r["card_name"])
    prefilled_ex = sum(1 for r in output_rows if r["is_ex"])
    print(f"Template: {out_path}")
    print(f"Positions       : {len(output_rows)}")
    print(f"Name prefilled  : {prefilled_names}/9")
    print(f"is_ex prefilled : {prefilled_ex}/9")
    print(f"Qty prefilled   : 0/9  (always blank — read from quantity chip visually)")
    print(f"Ext ref hints   : {'enabled (' + str(len(ext_ref)) + ' names)' if ext_available else 'not available'}")
    if not qty_usable:
        print(f"  (qty OCR accuracy {qty_accuracy:.0%} too low for prefill — leave blank)")
    if not ex_usable:
        print(f"  (is_ex accuracy {ex_accuracy:.0%} below 85% — treat prefills as hints only)")


if __name__ == "__main__":
    main()
