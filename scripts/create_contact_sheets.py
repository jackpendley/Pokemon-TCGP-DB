#!/usr/bin/env python3
"""
Create labeled contact sheets from cropped card images.

Reads:   data/extraction/crop_manifest.json
         data/extraction/crop_quality_report.json   (optional — adds QA badges)
Outputs: review/contact_sheets/<stem>_contact.png   (one per screenshot)
         review/contact_sheets/master_contact.png    (all crops combined, if ≤216 crops)

Usage:
    python3 scripts/create_contact_sheets.py [--no-master]

If crop_quality_report.json is present, labels are color-coded:
  green background  = PASS
  orange background = WARN
  red background    = FAIL
  dark background   = no QA data
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is required.  Install with:  python3 -m pip install Pillow")
    sys.exit(1)

MANIFEST_FILE  = Path("data/extraction/crop_manifest.json")
QA_REPORT_FILE = Path("data/extraction/crop_quality_report.json")
CONTACT_DIR    = Path("review/contact_sheets")

# Layout config
THUMB_W = 196           # thumbnail width  (half of native ~392)
THUMB_H = 247           # thumbnail height (half of native ~499)
COLS_PER_SHEET = 3      # contact sheet columns (matches the 3×3 grid)
LABEL_H = 28            # pixels reserved below each thumbnail for text
PADDING = 4             # gap between cells
SHEET_TITLE_H = 30      # pixels for sheet title at top

BG_COLOR = (30, 30, 30)
TEXT_COLOR = (240, 240, 240)
MAX_CROPS_MASTER = 216  # skip master if more than this many crops

# QA status label background colors
QA_COLORS = {
    "pass":    (0, 90, 0),
    "warning": (110, 80, 0),
    "fail":    (130, 0, 0),
    None:      (45, 45, 65),   # no QA data
}


def load_font(size: int = 11):
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, AttributeError):
            pass
    return ImageFont.load_default()


def load_qa_index(qa_path: Path) -> dict:
    """Return {crop_id: status_str} from QA report, or {} if absent."""
    if not qa_path.exists():
        return {}
    try:
        data = json.loads(qa_path.read_text(encoding="utf-8"))
        return {r["crop_id"]: r["status"] for r in data.get("crops", [])}
    except Exception:
        return {}


def build_sheet(crops: list, title: str, font, qa_index: dict) -> Image.Image:
    n = len(crops)
    cols = COLS_PER_SHEET
    rows = (n + cols - 1) // cols
    cell_w = THUMB_W + PADDING
    cell_h = THUMB_H + LABEL_H + PADDING
    sheet_w = cols * cell_w + PADDING
    sheet_h = rows * cell_h + PADDING + SHEET_TITLE_H

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG_COLOR)
    draw = ImageDraw.Draw(sheet)
    draw.text((PADDING, PADDING), title, fill=TEXT_COLOR, font=font)

    for idx, crop_info in enumerate(crops):
        col = idx % cols
        row = idx // cols
        x = PADDING + col * cell_w
        y = SHEET_TITLE_H + PADDING + row * cell_h

        crop_path = Path(crop_info["file"])
        if crop_path.exists():
            try:
                img = Image.open(crop_path).convert("RGB")
                # Read actual dimensions for label
                actual_w, actual_h = img.size
                img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
                sheet.paste(img, (x, y))
            except Exception:
                actual_w, actual_h = 0, 0
                draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=(80, 0, 0))
        else:
            actual_w, actual_h = 0, 0
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=(60, 60, 60))

        # QA status
        crop_id = crop_info.get("crop_id", "")
        qa_status = qa_index.get(crop_id)  # "pass", "warning", "fail", or None
        label_bg = QA_COLORS.get(qa_status, QA_COLORS[None])

        # Label background strip
        label_y = y + THUMB_H
        draw.rectangle(
            [x, label_y, x + THUMB_W, label_y + LABEL_H],
            fill=label_bg,
        )

        # Label text: r1c1 392×499 PASS
        r = crop_info.get("row", "?")
        c = crop_info.get("col", "?")
        dim_str = f"{actual_w}×{actual_h}" if actual_w else "missing"
        qa_str = qa_status.upper() if qa_status else ""
        label = f"r{r}c{c}  {dim_str}  {qa_str}".strip()
        draw.text((x + 2, label_y + 2), label, fill=TEXT_COLOR, font=font)

    return sheet


def main():
    parser = argparse.ArgumentParser(description="Create contact sheets from card crops.")
    parser.add_argument(
        "--no-master", action="store_true", help="Skip the master contact sheet."
    )
    args = parser.parse_args()

    if not MANIFEST_FILE.exists():
        print(f"ERROR: {MANIFEST_FILE} not found.  Run crop_all_screenshots.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    qa_index = load_qa_index(QA_REPORT_FILE)
    if qa_index:
        print(f"  Loaded QA status for {len(qa_index)} crops from {QA_REPORT_FILE}")
    else:
        print(f"  No QA report found at {QA_REPORT_FILE} — labels will have no QA badges.")
        print(f"  Run: python3 scripts/evaluate_crop_quality.py")

    CONTACT_DIR.mkdir(parents=True, exist_ok=True)
    font = load_font(11)

    all_crops = []
    for ss in manifest.get("screenshots", []):
        crops = ss.get("crops", [])
        if not crops:
            continue
        stem = Path(ss["filename"]).stem
        cal = ss.get("calibration_source", "default")
        sheet = build_sheet(
            crops,
            f"{ss['filename']}  [{cal}]  ({len(crops)} cards)",
            font,
            qa_index,
        )
        out_path = CONTACT_DIR / f"{stem}_contact.png"
        sheet.save(out_path)
        print(f"  {out_path}  ({len(crops)} crops, cal={cal})")
        all_crops.extend(crops)

    if not args.no_master and all_crops:
        if len(all_crops) <= MAX_CROPS_MASTER:
            master = build_sheet(
                all_crops, f"MASTER — {len(all_crops)} crops", font, qa_index
            )
            master_path = CONTACT_DIR / "master_contact.png"
            master.save(master_path)
            print(f"  {master_path}  (master, {len(all_crops)} crops)")
        else:
            print(
                f"  Skipping master sheet: {len(all_crops)} crops > {MAX_CROPS_MASTER} limit."
            )

    print(f"\nDone. Contact sheets written to {CONTACT_DIR}/")


if __name__ == "__main__":
    main()
