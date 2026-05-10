#!/usr/bin/env python3
"""
One-off crop tool: crop the 9-card 3×3 grid from a single PTCGP binder screenshot.

This is a manual/diagnostic tool for a single screenshot.
For batch processing all screenshots use crop_all_screenshots.py (the canonical tool).

Usage:
    python3 scripts/crop_3x3_cards.py <screenshot_path> <output_dir>

Example:
    python3 scripts/crop_3x3_cards.py screenshots/IMG_1524.PNG crops/IMG_1524

Defaults are loaded from config/crop_config.json when present; CLI flags override:
    --top-y       y-pixel where the first card row begins (default: 546)
    --card-height height of one card row including gap   (default: 499)
    --left-x      x-pixel where the leftmost column begins (default: 3)
    --card-width  width of one card column               (default: 392)

Output files:
    <output_dir>/r1c1.png ... r3c3.png
    <output_dir>/crop_manifest.json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required for image cropping.")
    print("       Install it with:  python3 -m pip install Pillow")
    sys.exit(1)

# Built-in calibration fallback — mirrors config/crop_config.json defaults.
# See crop_calibration_report.md for derivation.
GRID_LEFT_X        = 3
GRID_TOP_Y         = 546
CARD_WIDTH         = 392
CARD_HEIGHT_TILE   = 484
ROW_GAP            = 15
CARD_HEIGHT_CELL   = CARD_HEIGHT_TILE + ROW_GAP   # 499

CONFIG_FILE = Path("config/crop_config.json")


def _load_defaults() -> dict:
    """Load crop defaults from config/crop_config.json, falling back to built-in values."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            d = cfg.get("defaults", {})
            return {
                "top_y":       d.get("top_y", GRID_TOP_Y),
                "card_height": d.get("card_height_cell", CARD_HEIGHT_CELL),
                "left_x":      d.get("left_x", GRID_LEFT_X),
                "card_width":  d.get("card_width", CARD_WIDTH),
            }
        except Exception:
            pass
    return {
        "top_y":       GRID_TOP_Y,
        "card_height": CARD_HEIGHT_CELL,
        "left_x":      GRID_LEFT_X,
        "card_width":  CARD_WIDTH,
    }


DEFAULT_PARAMS = _load_defaults()

GRID_ROWS = 3
GRID_COLS = 3


def compute_boxes(params: dict) -> list:
    boxes = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            name = f"r{row + 1}c{col + 1}"
            x0 = params["left_x"] + col * params["card_width"]
            y0 = params["top_y"] + row * params["card_height"]
            x1 = x0 + params["card_width"]
            y1 = y0 + params["card_height"]
            boxes.append((name, (x0, y0, x1, y1)))
    return boxes


def main():
    parser = argparse.ArgumentParser(
        description="Crop 3x3 card grid from a PTCGP binder screenshot."
    )
    parser.add_argument("screenshot", type=Path, help="Source screenshot PNG")
    parser.add_argument("output_dir", type=Path, help="Directory for crop PNGs and manifest")
    parser.add_argument("--top-y",       type=int, help="Override top_y")
    parser.add_argument("--card-height", type=int, help="Override card_height")
    parser.add_argument("--left-x",      type=int, help="Override left_x")
    parser.add_argument("--card-width",  type=int, help="Override card_width")
    args = parser.parse_args()

    if not args.screenshot.exists():
        print(f"ERROR: screenshot not found: {args.screenshot}")
        sys.exit(1)

    params = dict(DEFAULT_PARAMS)
    if args.top_y is not None:
        params["top_y"] = args.top_y
    if args.card_height is not None:
        params["card_height"] = args.card_height
    if args.left_x is not None:
        params["left_x"] = args.left_x
    if args.card_width is not None:
        params["card_width"] = args.card_width

    args.output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(args.screenshot)
    img_w, img_h = img.size
    print(f"Source : {args.screenshot}  ({img_w}x{img_h} px)")
    print(f"Params : {params}")
    print()

    boxes = compute_boxes(params)
    manifest_entries = []

    for name, (x0, y0, x1, y1) in boxes:
        x1c = min(x1, img_w)
        y1c = min(y1, img_h)
        crop = img.crop((x0, y0, x1c, y1c))
        out_path = args.output_dir / f"{name}.png"
        crop.save(out_path)
        w, h = crop.size
        print(f"  {name}.png  box=({x0},{y0},{x1c},{y1c})  size={w}x{h}")
        manifest_entries.append({
            "name": name,
            "file": str(out_path),
            "source": str(args.screenshot),
            "box": {"x0": x0, "y0": y0, "x1": x1c, "y1": y1c},
            "size": {"width": w, "height": h},
        })

    manifest_path = args.output_dir / "crop_manifest.json"
    manifest_path.write_text(
        json.dumps({"params": params, "crops": manifest_entries}, indent=2),
        encoding="utf-8",
    )
    print()
    print(f"Manifest : {manifest_path}")
    print(f"Done — {len(manifest_entries)} crops written to {args.output_dir}/")


if __name__ == "__main__":
    main()
