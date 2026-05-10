#!/usr/bin/env python3
"""
Evaluate automated field detection (quantity, is_ex, card_name) against
confirmed batch ground truth.

Reads:   batches/cards_batch_*.json           (confirmed ground truth)
         crops/<stem>/rNcM.png               (card crop images)
         data/extraction/ocr_results.json
         data/extraction/match_candidates.json
Outputs: data/extraction/field_detection_report.json
         field_detection_report.md

Usage:
    python3 scripts/evaluate_field_detection.py
"""

import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    print("ERROR: Pillow required.  Install with: python3 -m pip install Pillow")
    sys.exit(1)

try:
    import pytesseract
    TESS_AVAILABLE = True
except ImportError:
    TESS_AVAILABLE = False

BATCHES_GLOB = "batches/cards_batch_[0-9][0-9][0-9].json"
OCR_FILE = Path("data/extraction/ocr_results.json")
MATCH_FILE = Path("data/extraction/match_candidates.json")
CROPS_DIR = Path("crops")
REPORT_JSON = Path("data/extraction/field_detection_report.json")
REPORT_MD = Path("field_detection_report.md")

# Quantity chip region within a 392×499 crop (tile area only, before separator)
CHIP_X0, CHIP_Y0, CHIP_X1, CHIP_Y1 = 0, 440, 90, 484
CHIP_SCALE = 4   # upscale factor for digit OCR

# is_ex name heuristics
EX_NAME_PATTERNS = [
    r"\bex\b",          # ends with or contains standalone "ex"
    r"^mega\s",         # Mega EX cards
]


def crop_id_from_entry(entry: dict) -> str:
    stem = entry["source_screenshot"].replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{entry['source_row']}c{entry['source_column']}"


def crop_path_from_entry(entry: dict) -> Path:
    stem = entry["source_screenshot"].replace(".PNG", "").replace(".png", "")
    return CROPS_DIR / stem / f"r{entry['source_row']}c{entry['source_column']}.png"


# ---------------------------------------------------------------------------
# Quantity detection
# ---------------------------------------------------------------------------

def detect_quantity_from_crop(crop_img: Image.Image) -> tuple[str, float]:
    """
    Detect quantity chip value from a card crop image.
    Returns (predicted_str, confidence) where confidence is 0–1.
    predicted_str is the raw digit string found, or "" if nothing found.
    """
    w, h = crop_img.size
    x0 = max(0, CHIP_X0)
    y0 = max(0, CHIP_Y0)
    x1 = min(w, CHIP_X1)
    y1 = min(h, CHIP_Y1)
    if x1 <= x0 or y1 <= y0:
        return "", 0.0

    chip = crop_img.crop((x0, y0, x1, y1)).convert("L")
    # Upscale and sharpen
    chip = chip.resize((chip.width * CHIP_SCALE, chip.height * CHIP_SCALE), Image.LANCZOS)
    chip = chip.filter(ImageFilter.SHARPEN)
    # Invert if dark background (chip is light digits on dark)
    avg = sum(chip.tobytes()) / (chip.width * chip.height)
    if avg < 128:
        chip = ImageOps.invert(chip)

    if not TESS_AVAILABLE:
        return "", 0.0

    try:
        text = pytesseract.image_to_string(
            chip, config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789x"
        ).strip()
        digits = re.sub(r"[^0-9]", "", text)
        if digits and 1 <= int(digits) <= 99:
            return digits, 0.8
        return "", 0.2
    except Exception:
        return "", 0.0


# ---------------------------------------------------------------------------
# is_ex detection
# ---------------------------------------------------------------------------

def detect_is_ex_from_name(card_name: str) -> tuple[bool, str]:
    """Detect is_ex from the confirmed card_name string using name patterns."""
    name_lower = card_name.strip().lower()
    for pattern in EX_NAME_PATTERNS:
        if re.search(pattern, name_lower):
            return True, f"name matches pattern '{pattern}'"
    return False, "no ex pattern in name"


def detect_is_ex_from_ocr(ocr_text: str) -> tuple[bool, str]:
    """Detect is_ex from raw OCR text."""
    tokens = re.split(r"\W+", ocr_text.lower())
    if "ex" in tokens:
        return True, "OCR text contains 'ex' token"
    return False, "no 'ex' token in OCR text"


def predict_is_ex(card_name: str, ocr_text: str) -> tuple[bool, float, str]:
    """
    Predict is_ex. Returns (predicted, confidence, reason).
    Name-based heuristic takes priority over OCR.
    """
    name_pred, name_reason = detect_is_ex_from_name(card_name)
    if name_pred:
        return True, 0.9, name_reason
    ocr_pred, ocr_reason = detect_is_ex_from_ocr(ocr_text)
    if ocr_pred:
        return True, 0.6, ocr_reason
    return False, 0.8, "no ex signals found"


# ---------------------------------------------------------------------------
# card_name detection (from match_candidates)
# ---------------------------------------------------------------------------

def names_match(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def name_in_top(name: str, top_matches: list) -> bool:
    norm = name.strip().lower()
    return any(m.get("name", "").strip().lower() == norm for m in top_matches)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    batch_files = sorted(glob.glob(BATCHES_GLOB))
    if not batch_files:
        print("No batch files found.")
        sys.exit(1)

    ocr_data = json.loads(OCR_FILE.read_text(encoding="utf-8")) if OCR_FILE.exists() else {}
    ocr_by_id = {r["crop_id"]: r for r in ocr_data.get("results", [])}

    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8")) if MATCH_FILE.exists() else {}
    mc_by_id = {c["crop_id"]: c for c in mc_data.get("candidates", [])}

    results = []
    qty_correct = qty_total = qty_found = 0
    ex_correct = ex_total = ex_fp = ex_fn = 0
    name_top1 = name_top3 = name_total = 0

    for bf in batch_files:
        batch = json.loads(Path(bf).read_text(encoding="utf-8"))
        for entry in batch:
            cid = crop_id_from_entry(entry)
            crop_file = crop_path_from_entry(entry)
            confirmed_qty = entry["quantity"]
            confirmed_ex = entry["is_ex"]
            confirmed_name = entry["card_name"]

            ocr_item = ocr_by_id.get(cid, {})
            ocr_text = ocr_item.get("raw_ocr_text", "")
            mc_item = mc_by_id.get(cid, {})
            top_matches = mc_item.get("top_matches", [])
            suggested = mc_item.get("suggested_card_name")

            rec: dict = {
                "crop_id": cid,
                "confirmed_name": confirmed_name,
                "confirmed_qty": confirmed_qty,
                "confirmed_is_ex": confirmed_ex,
                "crop_exists": crop_file.exists(),
            }

            # --- Quantity detection ---
            pred_qty_str, qty_conf = "", 0.0
            if crop_file.exists():
                try:
                    img = Image.open(crop_file)
                    pred_qty_str, qty_conf = detect_quantity_from_crop(img)
                except Exception as e:
                    pred_qty_str, qty_conf = "", 0.0

            pred_qty = int(pred_qty_str) if pred_qty_str else None
            qty_match = pred_qty == confirmed_qty if pred_qty is not None else None

            rec["pred_qty"] = pred_qty
            rec["qty_confidence"] = qty_conf
            rec["qty_match"] = qty_match

            qty_total += 1
            if pred_qty is not None:
                qty_found += 1
                if qty_match:
                    qty_correct += 1

            # --- is_ex detection ---
            pred_ex, ex_conf, ex_reason = predict_is_ex(confirmed_name, ocr_text)
            ex_match = pred_ex == confirmed_ex
            rec["pred_is_ex"] = pred_ex
            rec["ex_confidence"] = ex_conf
            rec["ex_reason"] = ex_reason
            rec["ex_match"] = ex_match

            ex_total += 1
            if ex_match:
                ex_correct += 1
            elif pred_ex and not confirmed_ex:
                ex_fp += 1
            elif not pred_ex and confirmed_ex:
                ex_fn += 1

            # --- card_name detection ---
            t1 = names_match(confirmed_name, suggested or "")
            t3 = name_in_top(confirmed_name, top_matches)
            top1_score = top_matches[0]["score"] if top_matches else 0
            rec["name_top1_correct"] = t1
            rec["name_top3_correct"] = t3
            rec["name_top1_score"] = round(top1_score, 1)
            rec["suggested_name"] = suggested

            name_total += 1
            if t1:
                name_top1 += 1
            if t3:
                name_top3 += 1

            results.append(rec)

    # Summaries
    qty_acc = round(qty_correct / qty_total, 3) if qty_total else 0
    qty_found_rate = round(qty_found / qty_total, 3) if qty_total else 0
    ex_acc = round(ex_correct / ex_total, 3) if ex_total else 0
    name_t1_acc = round(name_top1 / name_total, 3) if name_total else 0
    name_t3_acc = round(name_top3 / name_total, 3) if name_total else 0

    # Recommendations
    recs = []
    if qty_acc < 0.5:
        recs.append("Quantity OCR accuracy is low — chip region or thresholding may need tuning")
    else:
        recs.append(f"Quantity detection accuracy {qty_acc:.0%} is usable as a prefill hint")
    if ex_acc >= 0.8:
        recs.append(f"is_ex detection {ex_acc:.0%} accuracy — name-pattern heuristic is reliable for prefilling")
    else:
        recs.append(f"is_ex detection {ex_acc:.0%} accuracy — false positives/negatives too high for auto-fill")
    if name_t3_acc >= 0.3:
        recs.append(f"Card-name top-3 accuracy {name_t3_acc:.0%} — useful as review hint but not for auto-fill")
    if name_t1_acc >= 0.5:
        recs.append(f"Card-name top-1 accuracy {name_t1_acc:.0%} — may support conservative auto-fill at score >= 95")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confirmed_positions": qty_total,
        "tess_available": TESS_AVAILABLE,
        "quantity": {
            "total": qty_total, "found": qty_found, "correct": qty_correct,
            "accuracy": qty_acc, "found_rate": qty_found_rate,
        },
        "is_ex": {
            "total": ex_total, "correct": ex_correct, "accuracy": ex_acc,
            "false_positives": ex_fp, "false_negatives": ex_fn,
        },
        "card_name": {
            "total": name_total, "top1_correct": name_top1, "top3_correct": name_top3,
            "top1_accuracy": name_t1_acc, "top3_accuracy": name_t3_acc,
        },
        "recommendations": recs,
        "per_crop": results,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Field Detection Evaluation Report",
        "",
        f"Generated: {report['generated_at'][:19]}Z",
        f"Confirmed positions: {qty_total}  |  Tesseract available: {TESS_AVAILABLE}",
        "",
        "## Quantity Detection",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total confirmed | {qty_total} |",
        f"| Quantity found by OCR | {qty_found} ({qty_found_rate:.0%}) |",
        f"| Quantity correct | {qty_correct} ({qty_acc:.0%}) |",
        "",
        "## is_ex Detection (name-pattern heuristic)",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total confirmed | {ex_total} |",
        f"| Correct | {ex_correct} ({ex_acc:.0%}) |",
        f"| False positives (predicted True, confirmed False) | {ex_fp} |",
        f"| False negatives (predicted False, confirmed True) | {ex_fn} |",
        "",
        "## Card-Name Detection (from match_candidates)",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total confirmed | {name_total} |",
        f"| Top-1 correct | {name_top1} ({name_t1_acc:.0%}) |",
        f"| Top-3 correct | {name_top3} ({name_t3_acc:.0%}) |",
        "",
        "## Recommendations",
        "",
    ]
    for r in recs:
        lines.append(f"- {r}")
    lines += ["", "## Per-Crop Results", ""]
    lines += ["| Crop | Confirmed Name | Qty OK | is_ex OK | Name Top-1 | Name Top-3 |",
              "|---|---|---|---|---|---|"]
    for r in results:
        qok = "✓" if r["qty_match"] else ("—" if r["qty_match"] is None else "✗")
        eok = "✓" if r["ex_match"] else "✗"
        n1 = "✓" if r["name_top1_correct"] else "✗"
        n3 = "✓" if r["name_top3_correct"] else "✗"
        lines.append(
            f"| {r['crop_id']} | {r['confirmed_name']} | {qok} | {eok} | {n1} | {n3} |"
        )

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Confirmed positions : {qty_total}")
    print(f"Quantity accuracy   : {qty_acc:.0%} ({qty_correct}/{qty_total}), found {qty_found_rate:.0%}")
    print(f"is_ex accuracy      : {ex_acc:.0%} ({ex_correct}/{ex_total})  FP={ex_fp} FN={ex_fn}")
    print(f"Name top-1 accuracy : {name_t1_acc:.0%} ({name_top1}/{name_total})")
    print(f"Name top-3 accuracy : {name_t3_acc:.0%} ({name_top3}/{name_total})")
    print(f"JSON → {REPORT_JSON}")
    print(f"MD   → {REPORT_MD}")


if __name__ == "__main__":
    main()
