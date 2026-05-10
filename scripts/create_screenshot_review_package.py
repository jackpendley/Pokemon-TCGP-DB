#!/usr/bin/env python3
"""
Create a complete review package for one screenshot.

Generates:
    review/screenshot_reviews/<stem>_review.md   — human review guide with OCR/candidates table
    review/confirmed/<stem>_confirmed_TEMPLATE.csv — prefilled confirmation template

Reads:
    data/extraction/match_candidates.json
    data/extraction/crop_quality_report.json      (if present, for QA status)
    config/crop_config.json                        (for calibration info)
    review/autofill_candidates.csv                 (if present)
    data/reference/external/external_card_reference.json  (if present)
    data/extraction/field_detection_report.json    (if present)

Usage:
    python3 scripts/create_screenshot_review_package.py --screenshot IMG_1530.PNG
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Import template generation logic
sys.path.insert(0, str(Path(__file__).parent))
import csv as csv_mod

MATCH_FILE = Path("data/extraction/match_candidates.json")
CROP_QUALITY = Path("data/extraction/crop_quality_report.json")
CROP_CONFIG = Path("config/crop_config.json")
AUTOFILL_CSV = Path("review/autofill_candidates.csv")
EXT_REF = Path("data/reference/external/external_card_reference.json")
FIELD_REPORT = Path("data/extraction/field_detection_report.json")
CONTACT_SHEETS_DIR = Path("review/contact_sheets")
REVIEWS_DIR = Path("review/screenshot_reviews")
CONFIRMED_DIR = Path("review/confirmed")

POSITIONS = [(r, c) for r in (1, 2, 3) for c in (1, 2, 3)]


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", name.lower())).strip()


def crop_id_str(screenshot: str, row: int, col: int) -> str:
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{row}c{col}"


def is_ex_from_name(name: str) -> bool:
    if not name:
        return False
    n = name.strip().lower()
    return bool(re.search(r"\bex\b", n) or re.match(r"^mega\s", n))


def load_ext_ref(path: Path) -> dict[str, dict]:
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


def get_calib_info(screenshot: str) -> tuple[int, str]:
    """Return (top_y, label) from crop config."""
    if not CROP_CONFIG.exists():
        return 546, "default"
    try:
        cfg = json.loads(CROP_CONFIG.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return 546, "default"
    overrides = cfg.get("per_screenshot_overrides", {})
    if screenshot in overrides:
        top_y = overrides[screenshot].get("top_y", 546)
        return top_y, f"override top_y={top_y}"
    return cfg.get("top_y", 546), "default"


def get_qa_status(screenshot: str) -> str:
    """Return QA summary from crop quality report."""
    if not CROP_QUALITY.exists():
        return "QA not run"
    try:
        data = json.loads(CROP_QUALITY.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "QA unavailable"
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    results = [r for r in data.get("results", []) if r.get("screenshot") == screenshot
               or r.get("crop_id", "").startswith(stem)]
    if not results:
        return "QA not available"
    fails = sum(1 for r in results if r.get("status") == "FAIL")
    warns = sum(1 for r in results if r.get("status") == "WARN")
    passes = len(results) - fails - warns
    return f"{passes}/{len(results)} PASS, {warns} WARN, {fails} FAIL"


def build_crop_data(screenshot: str, mc_by_id: dict, autofill_by_id: dict,
                    ext: dict[str, dict]) -> list[dict]:
    """
    Build per-crop data dict for both the markdown table and CSV template.
    """
    crops = []
    for row_num, col_num in POSITIONS:
        cid = crop_id_str(screenshot, row_num, col_num)
        mc = mc_by_id.get(cid, {})
        af = autofill_by_id.get(cid, {})

        top_matches = mc.get("top_matches", [])
        suggested = mc.get("suggested_card_name")
        top1_score = top_matches[0]["score"] if top_matches else 0
        best_ocr = mc.get("best_ocr_source", "")

        name_in_ocr = bool(
            suggested and best_ocr and suggested.lower() in best_ocr.lower()
        )

        # Prefill decision
        prefill_name = ""
        prefill_reason = ""
        if af.get("auto_fill") == "True":
            prefill_name = af.get("proposed_card_name", "")
            prefill_reason = f"autofill (score {int(float(af.get('score', 0)))})"
        elif top1_score >= 95 and suggested:
            prefill_name = suggested
            prefill_reason = f"score {int(top1_score)} ≥ 95"
        elif top1_score >= 90 and name_in_ocr and suggested:
            prefill_name = suggested
            prefill_reason = f"score {int(top1_score)} + OCR match"

        # Top-3 string for display
        if top_matches:
            top3_display = ", ".join(
                f"**{m['name']}** ({int(m['score'])})" if i == 0 and m["score"] >= 80
                else f"{m['name']} ({int(m['score'])})"
                for i, m in enumerate(top_matches[:3])
            )
        else:
            top3_display = "—"

        # OCR display
        ocr_display = best_ocr.strip() if best_ocr and best_ocr.strip() else "*(no OCR text)*"
        if len(ocr_display) > 40:
            ocr_display = ocr_display[:37] + "…"

        # External hints for the name we'd suggest (prefilled or top candidate)
        hint_target = prefill_name if prefill_name else (suggested if top1_score >= 60 else "")
        ext_hints = build_ext_hints(hint_target, ext) if hint_target else []

        crops.append({
            "row": row_num,
            "col": col_num,
            "cid": cid,
            "ocr": ocr_display,
            "top1_score": top1_score,
            "top3_display": top3_display,
            "top_matches": top_matches,
            "suggested": suggested,
            "prefill_name": prefill_name,
            "prefill_reason": prefill_reason,
            "ext_hints": ext_hints,
        })

    return crops


def write_markdown(screenshot: str, crops: list[dict], calib_label: str, qa_status: str,
                   out_path: Path, template_path: Path) -> None:
    stem = screenshot.replace(".PNG", "").replace(".png", "")
    contact_sheet = CONTACT_SHEETS_DIR / f"{stem}_contact.png"
    batch_num = _next_batch_num()

    lines = [
        f"# {screenshot} — Card Review Aid",
        "",
        f"**Contact sheet:** `{contact_sheet}`",
        "Open this image to visually inspect each crop before confirming names.",
        "",
        f"**Calibration:** {calib_label}",
        f"**QA:** {qa_status}",
        "",
        "---",
        "",
        "## Crop-by-Crop Review Table",
        "",
        "Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.",
        "Quantity must be read from the app — it is never prefilled automatically.",
        "",
        "| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |",
        "|---|---|---|---|---|---|",
    ]

    for crop in crops:
        pos = f"r{crop['row']}c{crop['col']}"
        ocr = crop["ocr"]
        top3 = crop["top3_display"]
        hints = "; ".join(crop["ext_hints"]) if crop["ext_hints"] else "—"
        prefill = f"*{crop['prefill_name']}* ✓" if crop["prefill_name"] else ""
        lines.append(f"| {pos} | `{ocr}` | {top3} | {hints} | {prefill} | |")

    lines += [
        "",
        "**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).",
        "",
        "---",
        "",
        "## Notes",
        "",
    ]

    # Auto-generate per-crop notes for interesting cases
    for crop in crops:
        pos = f"r{crop['row']}c{crop['col']}"
        top_name = crop["top_matches"][0]["name"] if crop["top_matches"] else None
        if crop["prefill_name"]:
            lines.append(f"- **{pos}** — `{crop['prefill_name']}` prefilled ({crop['prefill_reason']}). Confirm name and quantity.")
        elif crop["top1_score"] >= 70 and top_name:
            lines.append(f"- **{pos}** — Top candidate: {top_name} ({int(crop['top1_score'])}). Confirm visually.")
        elif crop["top1_score"] == 0:
            lines.append(f"- **{pos}** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.")
        else:
            hint = f" (top: {top_name})" if top_name else ""
            lines.append(f"- **{pos}** — Low confidence ({int(crop['top1_score'])}){hint}. Identify from contact sheet.")

    lines += [
        "",
        "---",
        "",
        "## Instructions",
        "",
        f"1. Open `{contact_sheet}`.",
        "2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).",
        f"3. Copy the template to a confirmed file:",
        "   ```bash",
        f"   cp {template_path} {str(template_path).replace('_TEMPLATE', '')}",
        "   ```",
        "4. Fill in `card_name` and `quantity` for every row.",
        "5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.",
        "6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).",
        "7. Add notes for anything uncertain.",
        "8. Convert to batch and validate:",
        "   ```bash",
        f"   python3 scripts/create_batch_from_confirmation.py \\",
        f"     --input {str(template_path).replace('_TEMPLATE', '')} \\",
        f"     --screenshot {screenshot} \\",
        f"     --output batches/cards_batch_{batch_num:03d}.json",
        f"   python3 scripts/validate_batch.py batches/cards_batch_{batch_num:03d}.json",
        "   ```",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_template_csv(screenshot: str, crops: list[dict], ext: dict,
                       ex_usable: bool, out_path: Path) -> int:
    """Write the confirmed CSV template. Returns count of prefilled names."""
    rows = []
    for crop in crops:
        name_notes: list[str] = []

        if crop["prefill_name"]:
            name_notes.append(f"{crop['prefill_reason']}; user_verify")
        else:
            # top-3 hint
            if crop["top_matches"]:
                top3 = "; ".join(
                    f"{m['name']}({int(m['score'])})" for m in crop["top_matches"][:3]
                )
                name_notes.append(f"top3={top3}; user_identify")
            else:
                name_notes.append("no_candidates; user_identify")

        # External hints (always add if target is identifiable)
        if crop["ext_hints"]:
            name_notes.append("ref:" + "; ".join(crop["ext_hints"]))

        # is_ex
        is_ex = ""
        if crop["prefill_name"]:
            if is_ex_from_name(crop["prefill_name"]):
                is_ex = "true"
                name_notes.append("is_ex=true(name)")
            else:
                is_ex = "false"
                if not ex_usable:
                    name_notes.append("is_ex=false(assumed)")

        rows.append({
            "screenshot": screenshot,
            "row": str(crop["row"]),
            "column": str(crop["col"]),
            "card_name": crop["prefill_name"],
            "quantity": "",
            "special_type": "unknown",
            "is_ex": is_ex,
            "notes": "; ".join(name_notes),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["screenshot", "row", "column", "card_name", "quantity",
                  "special_type", "is_ex", "notes"]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv_mod.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return sum(1 for r in rows if r["card_name"])


def _next_batch_num() -> int:
    """Infer the next batch number from existing batch files."""
    existing = sorted(Path("batches").glob("cards_batch_[0-9]*.json")) if Path("batches").exists() else []
    if not existing:
        return 1
    nums = []
    for f in existing:
        try:
            nums.append(int(f.stem.split("_")[-1]))
        except ValueError:
            pass
    return max(nums) + 1 if nums else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a review package (markdown + CSV template) for one screenshot."
    )
    parser.add_argument("--screenshot", required=True,
                        help="Screenshot filename, e.g. IMG_1530.PNG")
    args = parser.parse_args()

    screenshot = args.screenshot
    stem = screenshot.replace(".PNG", "").replace(".png", "")

    if not MATCH_FILE.exists():
        print(f"ERROR: {MATCH_FILE} not found. Run match_ocr_to_reference.py first.")
        sys.exit(1)

    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
    mc_by_id = {c["crop_id"]: c for c in mc_data.get("candidates", [])}

    autofill_by_id: dict = {}
    if AUTOFILL_CSV.exists():
        with AUTOFILL_CSV.open(encoding="utf-8", newline="") as fh:
            for row in csv_mod.DictReader(fh):
                autofill_by_id[row["crop_id"]] = row

    field_report = {}
    if FIELD_REPORT.exists():
        field_report = json.loads(FIELD_REPORT.read_text(encoding="utf-8"))
    ex_accuracy = field_report.get("is_ex", {}).get("accuracy", 0)
    ex_usable = ex_accuracy >= 0.85

    ext = load_ext_ref(EXT_REF)
    calib_top_y, calib_label = get_calib_info(screenshot)
    qa_status = get_qa_status(screenshot)

    crops = build_crop_data(screenshot, mc_by_id, autofill_by_id, ext)

    template_path = CONFIRMED_DIR / f"{stem}_confirmed_TEMPLATE.csv"
    review_path = REVIEWS_DIR / f"{stem}_review.md"

    prefilled = write_template_csv(screenshot, crops, ext, ex_usable, template_path)
    write_markdown(screenshot, crops, calib_label, qa_status, review_path, template_path)

    print(f"Review package created for {screenshot}")
    print(f"  Markdown : {review_path}")
    print(f"  Template : {template_path}")
    print(f"  Prefilled: {prefilled}/9 names")
    print(f"  Ext ref  : {'enabled (' + str(len(ext)) + ' names)' if ext else 'not available'}")
    print(f"  Next batch: cards_batch_{_next_batch_num():03d}.json")
    print()
    print("Next steps:")
    print(f"  1. Open review/contact_sheets/{stem}_contact.png")
    print(f"  2. Open {review_path}")
    print(f"  3. Copy template: cp {template_path} {str(template_path).replace('_TEMPLATE', '')}")
    print(f"  4. Fill in card_name and quantity for every row")
    print(f"  5. Run: python3 scripts/create_batch_from_confirmation.py \\")
    print(f"            --input {str(template_path).replace('_TEMPLATE', '')} \\")
    print(f"            --screenshot {screenshot} \\")
    print(f"            --output batches/cards_batch_{_next_batch_num():03d}.json")


if __name__ == "__main__":
    main()
