#!/usr/bin/env python3
"""
Generate a reference-backed confirmation template CSV for one screenshot.

Combines all available reference sources (match candidates, autofill candidates,
external Limitless data, confirmed lexicon) to produce the richest possible
prefill hints while keeping human confirmation mandatory.

Inputs:
    --screenshot IMG_1530.PNG
    --output review/confirmed/IMG_1530_confirmed_TEMPLATE.csv

Reads:
    data/extraction/match_candidates.json
    review/autofill_candidates.csv               (if present)
    data/reference/external/external_card_reference.json  (if present)
    data/reference/confirmed_lexicon.json         (if present)
    data/extraction/field_detection_report.json   (if present)

Prefill rules:
    card_name  — only when score >= 95 OR autofill candidate flagged True
    is_ex      — from name pattern when card_name is prefilled
    quantity   — always blank; must be read from app screenshot
    special_type — always "unknown" unless reference unambiguously says otherwise

Usage:
    python3 scripts/generate_reference_backed_template.py \\
        --screenshot IMG_1530.PNG \\
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
EXT_REF = Path("data/reference/external/external_card_reference.json")
LEXICON_FILE = Path("data/reference/confirmed_lexicon.json")
FIELD_REPORT = Path("data/extraction/field_detection_report.json")

POSITIONS = [(r, c) for r in (1, 2, 3) for c in (1, 2, 3)]

# Prefill thresholds
AUTOFILL_SCORE = 95    # always prefill at or above
AUTOFILL_OCR = 90      # prefill if name also appears in OCR text


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", name.lower())).strip()


def crop_id(screenshot: str, row: int, col: int) -> str:
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{row}c{col}"


def is_ex_from_name(name: str) -> bool:
    if not name:
        return False
    n = name.strip().lower()
    return bool(re.search(r"\bex\b", n) or re.match(r"^mega\s", n))


def load_ext_ref(path: Path) -> dict[str, dict]:
    """Return dict normalized_name → card record."""
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
            key = norm(n)
            if key not in result:
                result[key] = entry
    return result


def build_ext_hints(card_name: str, ext: dict[str, dict]) -> list[str]:
    """Return list of hint strings for the given card name from external reference."""
    if not ext or not card_name:
        return []
    rec = ext.get(norm(card_name))
    if not rec:
        return []
    hints = []
    if rec.get("is_ex"):
        hints.append("is_ex=true")
    cat = rec.get("card_category")
    if cat and cat not in ("Pokemon", "Unknown"):
        hints.append(f"category={cat}")
    stage = rec.get("stage")
    if stage and stage not in ("Unknown", "None", ""):
        hints.append(f"stage={stage}")
    ptype = rec.get("pokemon_type")
    if ptype and ptype not in ("Unknown", "None", ""):
        hints.append(f"type={ptype}")
    rarity = rec.get("rarity")
    if rarity and rarity != "unknown":
        hints.append(f"rarity={rarity}")
    set_code = rec.get("set_code")
    if set_code:
        hints.append(f"set={set_code}")
    return hints


def generate_rows(screenshot: str, mc_by_id: dict, autofill_by_id: dict,
                  ext: dict[str, dict], ex_usable: bool) -> list[dict]:
    """
    Generate 9 template rows for the screenshot.
    Returns list of dicts matching the confirmed CSV schema.
    """
    rows = []
    for row_num, col_num in POSITIONS:
        cid = crop_id(screenshot, row_num, col_num)
        mc = mc_by_id.get(cid, {})
        af = autofill_by_id.get(cid, {})

        top_matches = mc.get("top_matches", [])
        suggested = mc.get("suggested_card_name")
        top1_score = top_matches[0]["score"] if top_matches else 0
        best_ocr = mc.get("best_ocr_source", "")

        name_in_ocr = bool(
            suggested and best_ocr and suggested.lower() in best_ocr.lower()
        )

        # --- card_name prefill ---
        card_name = ""
        name_notes: list[str] = []

        if af.get("auto_fill") == "True":
            card_name = af.get("proposed_card_name", "")
            score_val = int(float(af.get("score", 0)))
            name_notes.append(f"autofill:{score_val}; user_verify")
        elif top1_score >= AUTOFILL_SCORE and suggested:
            card_name = suggested
            name_notes.append(f"score:{int(top1_score)}; user_verify")
        elif top1_score >= AUTOFILL_OCR and name_in_ocr and suggested:
            card_name = suggested
            name_notes.append(f"score:{int(top1_score)}_ocr_match; user_verify")

        # --- top-3 hint (always shown) ---
        if top_matches:
            top3 = "; ".join(
                f"{m['name']}({int(m['score'])})" for m in top_matches[:3]
            )
            prefix = "top3" if not card_name else "alt3"
            name_notes.append(f"{prefix}={top3}")
        else:
            name_notes.append("no_candidates; user_identify")

        # --- external reference hints ---
        # Show hints for the prefilled name, or for the top candidate if score >= 65
        hint_target = card_name if card_name else (suggested if top1_score >= 65 else "")
        if hint_target:
            ext_hints = build_ext_hints(hint_target, ext)
            if ext_hints:
                name_notes.append("ref:" + "; ".join(ext_hints))

        # --- is_ex prefill ---
        is_ex = ""
        if card_name:
            pred = is_ex_from_name(card_name)
            if pred:
                is_ex = "true"
                name_notes.append("is_ex=true(name)")
            elif ex_usable:
                is_ex = "false"
            else:
                is_ex = "false"
                name_notes.append("is_ex=false(assumed)")

        notes = "; ".join(name_notes)

        rows.append({
            "screenshot": screenshot,
            "row": str(row_num),
            "column": str(col_num),
            "card_name": card_name,
            "quantity": "",
            "special_type": "unknown",
            "is_ex": is_ex,
            "notes": notes,
        })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a reference-backed confirmation template CSV."
    )
    parser.add_argument("--screenshot", required=True,
                        help="Screenshot filename, e.g. IMG_1530.PNG")
    parser.add_argument("--output", required=True,
                        help="Output CSV path, e.g. review/confirmed/IMG_1530_confirmed_TEMPLATE.csv")
    args = parser.parse_args()

    screenshot = args.screenshot
    out_path = Path(args.output)

    if not MATCH_FILE.exists():
        print(f"ERROR: {MATCH_FILE} not found. Run match_ocr_to_reference.py first.")
        sys.exit(1)

    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
    mc_by_id = {c["crop_id"]: c for c in mc_data.get("candidates", [])}

    autofill_by_id: dict = {}
    if AUTOFILL_CSV.exists():
        with AUTOFILL_CSV.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                autofill_by_id[row["crop_id"]] = row

    field_report = {}
    if FIELD_REPORT.exists():
        field_report = json.loads(FIELD_REPORT.read_text(encoding="utf-8"))
    ex_accuracy = field_report.get("is_ex", {}).get("accuracy", 0)
    ex_usable = ex_accuracy >= 0.85

    ext = load_ext_ref(EXT_REF)

    rows = generate_rows(screenshot, mc_by_id, autofill_by_id, ext, ex_usable)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["screenshot", "row", "column", "card_name", "quantity",
                  "special_type", "is_ex", "notes"]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    prefilled = sum(1 for r in rows if r["card_name"])
    print(f"Template: {out_path}")
    print(f"Positions: {len(rows)}  |  Name prefilled: {prefilled}/9")
    print(f"Ext ref: {'enabled (' + str(len(ext)) + ' names)' if ext else 'not available'}")
    print(f"Qty: always blank — read from app quantity chip")


if __name__ == "__main__":
    main()
