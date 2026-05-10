#!/usr/bin/env python3
"""
Create a draft confirmed CSV and draft batch JSON from a generated template.

Reads a template CSV (from create_screenshot_review_package.py) and auto-fills
as many rows as possible without user input:
  - Prefilled names (autofill score >= 95 or 100) → used directly, confidence=medium
  - Top candidate score >= 80 → used as draft name, confidence=low, flagged for review
  - Everything else → UNKNOWN_<stem>_rNcM placeholder, confidence=low

All draft rows have:
  - quantity=0 (user must confirm from app)
  - needs_review=true
  - review_reason explaining what is uncertain

Outputs must be explicitly DRAFT files. Real batch files are never overwritten.

Usage:
    python3 scripts/create_draft_batch_from_template.py \\
        --screenshot IMG_1538.PNG \\
        --template review/confirmed/IMG_1538_confirmed_TEMPLATE.csv \\
        --confirmed-output review/confirmed/IMG_1538_confirmed_DRAFT.csv \\
        --batch-output batches/cards_batch_015_DRAFT.json \\
        --allow-unknown
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

VALID_SPECIAL_TYPES = {
    "normal", "full_art", "illustration_rare", "special_art", "immersive",
    "crown_gold", "shiny", "rainbow", "promo", "special_trainer",
    "alternate_art", "unknown",
}

AUTOFILL_SCORE_THRESHOLD = 95   # name came from autofill
CANDIDATE_SCORE_THRESHOLD = 80  # use top candidate as draft name


def parse_top_candidate(notes: str) -> tuple[str, int]:
    """
    Extract (name, score) of the top candidate from the notes field.
    Notes format: top3=Name(score); Name2(score2); ...; user_identify
    Returns ("", 0) if no candidate found.
    """
    m = re.search(r"top3=([^(]+)\((\d+)\)", notes)
    if m:
        name = m.group(1).strip()
        score = int(m.group(2))
        return name, score
    return "", 0


def parse_autofill_score(notes: str) -> int:
    """Extract score from autofill note: 'autofill (score N)'"""
    m = re.search(r"autofill\s*\(score\s*(\d+)\)", notes, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def normalize_for_id(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def make_id(card_name: str, special_type: str, existing_ids: set) -> str:
    base = f"{normalize_for_id(card_name)}_{normalize_for_id(special_type)}_unknown"
    candidate = f"{base}_v1"
    version = 1
    while candidate in existing_ids:
        version += 1
        candidate = f"{base}_v{version}"
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a draft batch from a review template CSV."
    )
    parser.add_argument("--screenshot", required=True, help="Screenshot filename, e.g. IMG_1538.PNG")
    parser.add_argument("--template", required=True, help="Path to template CSV")
    parser.add_argument("--confirmed-output", required=True, help="Output draft confirmed CSV path")
    parser.add_argument("--batch-output", required=True, help="Output draft batch JSON path")
    parser.add_argument("--allow-unknown", action="store_true",
                        help="Allow UNKNOWN placeholder names (required for partial templates)")
    args = parser.parse_args()

    screenshot = args.screenshot
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    template_path = Path(args.template)
    csv_out_path = Path(args.confirmed_output)
    batch_out_path = Path(args.batch_output)

    # Safety: never overwrite non-DRAFT files
    if not csv_out_path.name.endswith("_DRAFT.csv"):
        print(f"ERROR: --confirmed-output must end with _DRAFT.csv, got: {csv_out_path.name}")
        sys.exit(1)
    if not batch_out_path.name.endswith("_DRAFT.json"):
        print(f"ERROR: --batch-output must end with _DRAFT.json, got: {batch_out_path.name}")
        sys.exit(1)
    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}")
        sys.exit(1)
    if batch_out_path.exists():
        print(f"ERROR: output already exists: {batch_out_path}")
        print("Delete it first or choose a different path.")
        sys.exit(1)

    with template_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {"screenshot", "row", "column", "card_name", "quantity",
                         "special_type", "is_ex", "notes"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            missing = required_cols - set(reader.fieldnames or [])
            print(f"ERROR: template missing columns: {missing}")
            sys.exit(1)
        rows = list(reader)

    if len(rows) == 0:
        print("ERROR: template has no data rows.")
        sys.exit(1)

    csv_rows = []
    batch_entries = []
    existing_ids: set = set()

    stats = {"prefilled": 0, "candidate": 0, "unknown": 0}

    for row in rows:
        row_num = row.get("row", "").strip()
        col_num = row.get("column", "").strip()
        template_name = row.get("card_name", "").strip()
        template_is_ex = row.get("is_ex", "").strip().lower()
        notes_raw = row.get("notes", "").strip()
        pos_label = f"r{row_num}c{col_num}"

        # Determine card name, confidence, and draft notes
        autofill_score = parse_autofill_score(notes_raw)
        top_name, top_score = parse_top_candidate(notes_raw)

        draft_notes_parts: list[str] = []
        confidence = "low"

        if template_name:
            # Name was prefilled by review package (autofill >= 95 or 100)
            card_name = template_name
            confidence = "medium"
            draft_notes_parts.append(f"autofill_score_{autofill_score}" if autofill_score else "prefilled")
            draft_notes_parts.append("user_verify_name_and_quantity")
            stats["prefilled"] += 1
        elif top_score >= CANDIDATE_SCORE_THRESHOLD and top_name:
            # Good candidate — use as draft name
            card_name = top_name
            confidence = "low"
            draft_notes_parts.append(f"auto_draft_candidate_score_{top_score}")
            draft_notes_parts.append("user_verify")
            stats["candidate"] += 1
        else:
            # No reliable name
            if not args.allow_unknown:
                print(f"ERROR: {pos_label} has no candidate >= {CANDIDATE_SCORE_THRESHOLD} "
                      f"and --allow-unknown not set.")
                sys.exit(1)
            card_name = f"UNKNOWN_{stem}_{pos_label}"
            confidence = "low"
            draft_notes_parts.append("no_candidate")
            draft_notes_parts.append("user_identify_required")
            stats["unknown"] += 1

        # Preserve any ref: hints from original notes
        ref_hints = [p for p in notes_raw.split(";") if p.strip().startswith("ref:")]
        draft_notes_parts.extend(h.strip() for h in ref_hints)

        draft_notes = "; ".join(draft_notes_parts)

        # is_ex
        if template_is_ex in ("true", "1", "yes"):
            is_ex = True
            is_ex_str = "true"
        else:
            is_ex = False
            is_ex_str = "false"
            if not template_is_ex:
                draft_notes += "; is_ex_unverified"

        # Quantity: always 0 (draft — user must confirm from app)
        quantity = 0

        # Review reason
        review_parts = ["draft entry; confirm card_name and quantity"]
        if card_name.startswith("UNKNOWN_"):
            review_parts.append("card name unknown — identify from contact sheet")
        elif confidence == "low":
            review_parts.append(f"draft candidate (score {top_score}) — verify against contact sheet")

        review_reason = "; ".join(review_parts)

        # Write CSV row
        csv_rows.append({
            "screenshot": screenshot,
            "row": row_num,
            "column": col_num,
            "card_name": card_name,
            "quantity": "0",
            "special_type": "unknown",
            "is_ex": is_ex_str,
            "notes": draft_notes,
        })

        # Build batch entry
        card_id = make_id(card_name, "unknown", existing_ids)
        existing_ids.add(card_id)

        batch_entries.append({
            "id": card_id,
            "card_name": card_name,
            "quantity": quantity,
            "card_category": "Unknown",
            "pokemon_type": "Unknown",
            "stage": "Unknown",
            "hp": None,
            "is_ex": is_ex,
            "special_type": "unknown",
            "rarity": "unknown",
            "set_or_pack": "unknown",
            "variant_notes": draft_notes,
            "source_screenshot": screenshot,
            "source_row": int(row_num),
            "source_column": int(col_num),
            "confidence": confidence,
            "needs_review": True,
            "review_reason": review_reason,
        })

    # Write draft confirmed CSV
    csv_out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["screenshot", "row", "column", "card_name", "quantity",
                  "special_type", "is_ex", "notes"]
    with csv_out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Write draft batch JSON
    batch_out_path.parent.mkdir(parents=True, exist_ok=True)
    batch_out_path.write_text(
        json.dumps(batch_entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Draft CSV   : {csv_out_path}")
    print(f"Draft batch : {batch_out_path}")
    print(f"Entries     : {len(batch_entries)}")
    print(f"  Prefilled : {stats['prefilled']}")
    print(f"  Candidates: {stats['candidate']} (score >= {CANDIDATE_SCORE_THRESHOLD})")
    print(f"  UNKNOWN   : {stats['unknown']}")
    print(f"All quantity=0 — user must confirm from app")


if __name__ == "__main__":
    main()
