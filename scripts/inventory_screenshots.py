#!/usr/bin/env python3
"""
Inventory the /screenshots folder without OCR.

Updated for the new cropped 3x3 grid screenshots (IMG_1556–IMG_1581).
Each screenshot shows exactly the 3x3 card grid. The final screenshot has 7 cards.

Generates:
    data/current/screenshot_inventory.json
    data/current/screenshot_manifest.json
    review/screenshot_inventory.md
    review/screenshot_manifest.md

Usage:
    python3 scripts/inventory_screenshots.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False
    print("WARNING: Pillow not installed — image dimensions will be skipped. Run: pip3 install Pillow")

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
OUT_DIR = ROOT / "data" / "current"
INVENTORY_JSON = OUT_DIR / "screenshot_inventory.json"
MANIFEST_JSON = OUT_DIR / "screenshot_manifest.json"
INVENTORY_MD = ROOT / "review" / "screenshot_inventory.md"
MANIFEST_MD = ROOT / "review" / "screenshot_manifest.md"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

STANDARD_SLOTS = 9
FINAL_SLOTS = 7


def grid_positions(n_slots):
    positions = []
    row, col = 1, 1
    for _ in range(n_slots):
        positions.append(f"r{row}c{col}")
        col += 1
        if col > 3:
            col = 1
            row += 1
    return positions


def get_dimensions(path):
    if not HAVE_PIL:
        return None, None
    try:
        with Image.open(path) as img:
            return img.size  # (width, height)
    except Exception as e:
        print(f"  WARN: Cannot read {path.name}: {e}")
        return None, None


def inventory_screenshots():
    if not SCREENSHOTS_DIR.exists():
        print(f"ERROR: {SCREENSHOTS_DIR} does not exist", file=sys.stderr)
        sys.exit(1)

    files = sorted([
        f for f in SCREENSHOTS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS
        and not f.name.startswith(".")
    ])

    if not files:
        print(f"ERROR: No image files found in {SCREENSHOTS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"  Found {len(files)} image file(s)")

    entries = []
    for i, f in enumerate(files):
        is_final = (i == len(files) - 1)
        n_slots = FINAL_SLOTS if is_final else STANDARD_SLOTS
        positions = grid_positions(n_slots)

        stat = f.stat()
        width, height = get_dimensions(f)

        entry = {
            "filename": f.name,
            "path": str(f.relative_to(ROOT)),
            "index": i + 1,
            "is_final": is_final,
            "grid_type": "3x3_final_7" if is_final else "3x3_standard",
            "expected_card_slots": n_slots,
            "slot_positions": positions,
            "width": width,
            "height": height,
            "file_size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        }
        entries.append(entry)

    return entries


def build_manifest_entries(entries):
    manifest = []
    for entry in entries:
        slots = [
            {"position": pos, "card_name": "", "quantity": None, "notes": ""}
            for pos in entry["slot_positions"]
        ]
        manifest.append({
            "filename": entry["filename"],
            "index": entry["index"],
            "grid_type": entry["grid_type"],
            "expected_card_slots": entry["expected_card_slots"],
            "slots": slots,
        })
    return manifest


def write_inventory_md(entries, path):
    total_slots = sum(e["expected_card_slots"] for e in entries)
    lines = [
        "# Screenshot Inventory",
        "",
        f"**Total files:** {len(entries)}  ",
        f"**Total expected card slots:** {total_slots}  ",
        f"**Source directory:** `screenshots/`  ",
        "",
        "| # | Filename | Dimensions | Grid | Slots | Size | Modified |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        dims = f"{e['width']}×{e['height']}" if e["width"] else "—"
        size_kb = f"{e['file_size_bytes'] // 1024} KB"
        modified = e["modified"][:10]
        grid = "3×3 (7 visible)" if e["is_final"] else "3×3 standard"
        lines.append(
            f"| {e['index']} | `{e['filename']}` | {dims} | {grid} | {e['expected_card_slots']} | {size_kb} | {modified} |"
        )
    lines += [
        "",
        f"**Total card slots: {total_slots}**",
        "",
        "## Notes",
        "",
        "- Standard screenshots: 3×3 grid (9 card tiles with quantity chips).",
        "- Final screenshot: 7 visible cards (last row incomplete).",
        "- Slot positions are labeled r1c1 through r3c3.",
        "- `card_name` and `quantity` fields are blank — filled by manual review or future OCR.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest_md(manifest, path):
    lines = [
        "# Screenshot Manifest",
        "",
        "Slot-level grid manifest. `card_name` and `quantity` are blank placeholders.",
        "",
    ]
    for m in manifest:
        lines.append(f"## {m['filename']} ({m['grid_type']}, {m['expected_card_slots']} slots)")
        lines.append("")
        lines.append("| Position | Card Name | Quantity | Notes |")
        lines.append("|---|---|---|---|")
        for s in m["slots"]:
            lines.append(f"| {s['position']} | {s['card_name']} | {s['quantity']} | {s['notes']} |")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print(f"\n=== inventory_screenshots.py ===")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "review").mkdir(exist_ok=True)

    entries = inventory_screenshots()

    standard = [e for e in entries if not e["is_final"]]
    finals = [e for e in entries if e["is_final"]]
    total_slots = sum(e["expected_card_slots"] for e in entries)

    print(f"  Standard 3×3 files: {len(standard)} × 9 = {len(standard) * 9} slots")
    print(f"  Final 7-card file:  {len(finals)} × 7 = {len(finals) * 7} slots")
    print(f"  Total card slots:   {total_slots}")

    INVENTORY_JSON.write_text(
        json.dumps({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "screenshot_count": len(entries),
            "standard_count": len(standard),
            "final_count": len(finals),
            "total_card_slots": total_slots,
            "screenshots": entries,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Written: {INVENTORY_JSON.relative_to(ROOT)}")

    manifest = build_manifest_entries(entries)
    MANIFEST_JSON.write_text(
        json.dumps({"manifest": manifest}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Written: {MANIFEST_JSON.relative_to(ROOT)}")

    write_inventory_md(entries, INVENTORY_MD)
    print(f"  Written: {INVENTORY_MD.relative_to(ROOT)}")

    write_manifest_md(manifest, MANIFEST_MD)
    print(f"  Written: {MANIFEST_MD.relative_to(ROOT)}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
