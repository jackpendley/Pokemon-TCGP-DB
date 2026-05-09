#!/usr/bin/env python3
"""
Create labeled contact sheets from cropped card images.

Reads:   data/extraction/crop_manifest.json
Outputs: review/contact_sheets/<stem>_contact.png   (one per screenshot)
         review/contact_sheets/master_contact.png    (all crops combined, if ≤216 crops)

Usage:
    python3 scripts/create_contact_sheets.py [--no-master]
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

MANIFEST_FILE = Path("data/extraction/crop_manifest.json")
CONTACT_DIR = Path("review/contact_sheets")

# Layout config
THUMB_W = 196      # thumbnail width  (half of native ~392)
THUMB_H = 247      # thumbnail height (half of native ~495)
COLS_PER_SHEET = 3 # contact sheet columns (matches the 3×3 grid)
LABEL_H = 24       # pixels reserved below each thumbnail for text
PADDING = 4        # gap between cells
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (240, 240, 240)
MAX_CROPS_MASTER = 216  # skip master if more than this many crops


def load_font(size: int = 12):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (OSError, AttributeError):
        return ImageFont.load_default()


def build_sheet(crops: list, title: str, font) -> Image.Image:
    n = len(crops)
    cols = COLS_PER_SHEET
    rows = (n + cols - 1) // cols
    cell_w = THUMB_W + PADDING
    cell_h = THUMB_H + LABEL_H + PADDING
    sheet_w = cols * cell_w + PADDING
    sheet_h = rows * cell_h + PADDING + 30  # 30px for sheet title

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG_COLOR)
    draw = ImageDraw.Draw(sheet)
    draw.text((PADDING, PADDING), title, fill=TEXT_COLOR, font=font)

    for idx, crop_info in enumerate(crops):
        col = idx % cols
        row = idx // cols
        x = PADDING + col * cell_w
        y = 30 + PADDING + row * cell_h

        crop_path = Path(crop_info["file"])
        if crop_path.exists():
            try:
                img = Image.open(crop_path).convert("RGB")
                img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
                sheet.paste(img, (x, y))
            except Exception:
                draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=(80, 0, 0))
        else:
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=(60, 60, 60))

        label = (
            f"{crop_info.get('screenshot', '?')} "
            f"r{crop_info.get('row', '?')}c{crop_info.get('col', '?')} "
            f"#{idx + 1}"
        )
        draw.text((x, y + THUMB_H + 2), label, fill=TEXT_COLOR, font=font)

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
    CONTACT_DIR.mkdir(parents=True, exist_ok=True)
    font = load_font(12)

    all_crops = []
    for ss in manifest.get("screenshots", []):
        crops = ss.get("crops", [])
        if not crops:
            continue
        stem = Path(ss["filename"]).stem
        sheet = build_sheet(crops, f"{ss['filename']} ({len(crops)} cards)", font)
        out_path = CONTACT_DIR / f"{stem}_contact.png"
        sheet.save(out_path)
        print(f"  {out_path}  ({len(crops)} crops)")
        all_crops.extend(crops)

    if not args.no_master and all_crops:
        if len(all_crops) <= MAX_CROPS_MASTER:
            master = build_sheet(all_crops, f"MASTER — {len(all_crops)} crops", font)
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
