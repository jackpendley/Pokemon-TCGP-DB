#!/usr/bin/env python3
"""
Batch-crop all PTCGP binder screenshots into 3×3 card grids.

Reads:   screenshots_inventory.json    (ordered screenshot list)
         config/crop_config.json       (calibration; falls back to built-in defaults)
Outputs: crops/IMG_XXXX/r1c1.png ... r3c3.png   (one dir per screenshot)
         data/extraction/crop_manifest.json       (global manifest)

Usage:
    python3 scripts/crop_all_screenshots.py [--force]

    --force   Re-crop screenshots even if their output directory already exists.

To fix misaligned screenshots, add entries to config/crop_config.json under
per_screenshot_overrides.  See crop_override_workflow.md for the full procedure.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required.  Install with:  python3 -m pip install Pillow")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Built-in defaults — used as fallback when config/crop_config.json is absent.
# Calibrated empirically for 1179×2556 PTCGP binder screenshots (iPhone 15 Pro).
# See crop_calibration_report.md for full derivation.
# ---------------------------------------------------------------------------
_BUILTIN_DEFAULTS = {
    "left_x":           3,
    "top_y":            546,
    "card_width":       392,
    "card_height_tile": 484,
    "row_gap":          15,
    "card_height_cell": 499,   # tile + gap; step between row y-origins
}

GRID_ROWS = 3
GRID_COLS = 3

CONFIG_FILE    = Path("config/crop_config.json")
INVENTORY_FILE = Path("screenshots_inventory.json")
CROPS_ROOT     = Path("crops")
MANIFEST_OUT   = Path("data/extraction/crop_manifest.json")


def load_crop_config() -> tuple:
    """
    Return (defaults, per_screenshot_overrides) from CONFIG_FILE.
    Falls back to _BUILTIN_DEFAULTS with empty overrides if config is absent.
    """
    if not CONFIG_FILE.exists():
        print(f"  INFO  {CONFIG_FILE} not found — using built-in defaults.")
        return dict(_BUILTIN_DEFAULTS), {}

    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  WARN  Could not parse {CONFIG_FILE}: {exc} — using built-in defaults.")
        return dict(_BUILTIN_DEFAULTS), {}

    raw = cfg.get("defaults", {})
    defaults = dict(_BUILTIN_DEFAULTS)
    for key in _BUILTIN_DEFAULTS:
        if key in raw:
            defaults[key] = raw[key]
    # Recompute cell if tile or gap were explicitly overridden but cell was not
    if "card_height_cell" not in raw and ("card_height_tile" in raw or "row_gap" in raw):
        defaults["card_height_cell"] = defaults["card_height_tile"] + defaults["row_gap"]

    overrides = cfg.get("per_screenshot_overrides", {})
    return defaults, overrides


def effective_params(filename: str, defaults: dict, overrides: dict) -> tuple:
    """
    Merge global defaults with any per-screenshot override.
    Returns (params_dict, calibration_source) where source is "default" or "override".
    """
    override = overrides.get(filename, {})
    if not override:
        return dict(defaults), "default"

    params = dict(defaults)
    for key in _BUILTIN_DEFAULTS:
        if key in override:
            params[key] = override[key]
    # Recompute cell if tile or gap were overridden but cell was not
    if "card_height_cell" not in override and (
        "card_height_tile" in override or "row_gap" in override
    ):
        params["card_height_cell"] = params["card_height_tile"] + params["row_gap"]
    return params, "override"


def compute_boxes(params: dict) -> list:
    boxes = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            name = f"r{row + 1}c{col + 1}"
            x0 = params["left_x"] + col * params["card_width"]
            y0 = params["top_y"] + row * params["card_height_cell"]
            x1 = x0 + params["card_width"]
            y1 = y0 + params["card_height_cell"]
            boxes.append((name, row + 1, col + 1, (x0, y0, x1, y1)))
    return boxes


def crop_screenshot(src_path: Path, out_dir: Path, params: dict) -> list:
    img = Image.open(src_path)
    img_w, img_h = img.size
    out_dir.mkdir(parents=True, exist_ok=True)

    boxes = compute_boxes(params)
    entries = []
    for name, row, col, (x0, y0, x1, y1) in boxes:
        x1c = min(x1, img_w)
        y1c = min(y1, img_h)
        crop = img.crop((x0, y0, x1c, y1c))
        out_path = out_dir / f"{name}.png"
        crop.save(out_path)
        w, h = crop.size
        entries.append({
            "crop_id": f"{src_path.stem}_{name}",
            "name": name,
            "file": str(out_path),
            "screenshot": src_path.name,
            "row": row,
            "col": col,
            "box": {"x0": x0, "y0": y0, "x1": x1c, "y1": y1c},
            "size": {"width": w, "height": h},
        })
    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Batch-crop all PTCGP screenshots into 3×3 card grids."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-crop even if output directories already exist.",
    )
    args = parser.parse_args()

    if not INVENTORY_FILE.exists():
        print(f"ERROR: {INVENTORY_FILE} not found.  Run scripts/inventory_screenshots.py first.")
        sys.exit(1)

    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    entries = inventory.get("entries", [])
    if not entries:
        print("ERROR: No entries found in screenshots_inventory.json.")
        sys.exit(1)

    defaults, overrides = load_crop_config()
    if overrides:
        print(f"  Loaded {len(overrides)} per-screenshot override(s) from {CONFIG_FILE}")

    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)

    all_screenshots = []
    total_crops = 0
    skipped = 0

    for entry in entries:
        src_path = Path(entry["path"])
        filename = entry["filename"]
        stem = Path(filename).stem
        out_dir = CROPS_ROOT / stem

        params, cal_source = effective_params(filename, defaults, overrides)

        if out_dir.exists() and not args.force:
            print(f"  SKIP  {filename}  (already cropped — use --force to redo)")
            skipped += 1
            # Rebuild crop list from existing files for the manifest
            existing_crops = []
            for name_str in [f"r{r}c{c}" for r in range(1, 4) for c in range(1, 4)]:
                p = out_dir / f"{name_str}.png"
                if p.exists():
                    row = int(name_str[1])
                    col = int(name_str[3])
                    existing_crops.append({
                        "crop_id": f"{stem}_{name_str}",
                        "name": name_str,
                        "file": str(p),
                        "screenshot": filename,
                        "row": row,
                        "col": col,
                        "box": None,
                        "size": None,
                    })
            all_screenshots.append({
                "filename": filename,
                "path": str(src_path),
                "calibration_source": cal_source,
                "calibration_params": params,
                "crops": existing_crops,
                "skipped": True,
            })
            continue

        if not src_path.exists():
            print(f"  WARN  {filename}  not found at {src_path} — skipping")
            all_screenshots.append({
                "filename": filename,
                "path": str(src_path),
                "calibration_source": cal_source,
                "calibration_params": params,
                "crops": [],
                "skipped": True,
                "error": "source file not found",
            })
            continue

        source_label = "  [override]" if cal_source == "override" else ""
        print(f"  CROP  {filename} → {out_dir}/{source_label}")
        crops = crop_screenshot(src_path, out_dir, params)
        total_crops += len(crops)
        all_screenshots.append({
            "filename": filename,
            "path": str(src_path),
            "calibration_source": cal_source,
            "calibration_params": params,
            "crops": crops,
            "skipped": False,
        })

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global_defaults": defaults,
        "override_count": len(overrides),
        "total_screenshots": len(all_screenshots),
        "total_crops": total_crops,
        "skipped_screenshots": skipped,
        "screenshots": all_screenshots,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print()
    print(f"Processed {len(all_screenshots)} screenshots, {total_crops} new crops, {skipped} skipped.")
    if overrides:
        override_active = sum(
            1 for e in all_screenshots if e.get("calibration_source") == "override"
        )
        print(f"Per-screenshot overrides applied to {override_active} screenshot(s).")
    print(f"Manifest  → {MANIFEST_OUT}")


if __name__ == "__main__":
    main()
