#!/usr/bin/env python3
"""
Evaluate crop quality for all card crops from the manifest.

Uses simple pixel-level heuristics to flag crops that are likely misaligned,
clipped, or showing app background instead of card content.

Reads:   data/extraction/crop_manifest.json
Outputs: data/extraction/crop_quality_report.json
         review/crop_quality_report.md

Usage:
    python3 scripts/evaluate_crop_quality.py [--force]

Heuristics (all thresholds are configurable at the top of this script):
  - File exists and is readable
  - Crop dimensions match expected (card_width × card_height_cell from manifest)
  - Crop box was not clamped against source image edge (would shrink the crop)
  - Title band (top ~70px) is not uniformly bright — uniform brightness suggests
    the crop started in app chrome above the card grid
  - Quantity chip zone (bottom-left ~90×44px of tile area) has some variation —
    low variance suggests the chip is missing or the crop ran off the bottom
"""

import argparse
import json
import sys
import statistics
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required.  Install with:  python3 -m pip install Pillow")
    sys.exit(1)

MANIFEST_FILE = Path("data/extraction/crop_manifest.json")
REPORT_JSON   = Path("data/extraction/crop_quality_report.json")
REPORT_MD     = Path("review/crop_quality_report.md")

# ---------------------------------------------------------------------------
# Heuristic thresholds — adjust if too many false positives/negatives.
# ---------------------------------------------------------------------------
DIMENSION_TOLERANCE = 10   # px; crops within this of expected size are OK

# Title band: x=10–380, y=0–70 (card name + HP area at top of each crop)
TITLE_BAND = (10, 0, 380, 70)
TITLE_BRIGHT_WARN    = 225  # mean > this → too bright, may be app background
TITLE_VARIANCE_WARN  = 300  # variance < this → too uniform for card content

# Chip area: x=0–90, y=440–484 (bottom-left of tile, before separator row)
CHIP_BAND = (0, 440, 90, 484)
CHIP_VARIANCE_WARN = 150    # variance < this → chip area may be blank

# Bottom separator: x=0–392, y=484–499 (row gap — expected to be bright/uniform)
BOTTOM_BAND = (0, 484, 392, 499)


def region_stats(img_gray, box: tuple) -> dict:
    """Compute mean and variance of grayscale pixels in the given box."""
    x0, y0, x1, y1 = box
    iw, ih = img_gray.size
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(iw, x1), min(ih, y1)
    if x0 >= x1 or y0 >= y1:
        return {"mean": 0.0, "variance": 0.0}
    region = img_gray.crop((x0, y0, x1, y1))
    pixels = list(region.tobytes())
    n = len(pixels)
    if n < 2:
        return {"mean": float(pixels[0]) if n else 0.0, "variance": 0.0}
    mean = sum(pixels) / n
    variance = sum((p - mean) ** 2 for p in pixels) / n
    return {"mean": round(mean, 1), "variance": round(variance, 1)}


def evaluate_crop(crop_info: dict, exp_w: int, exp_h: int) -> dict:
    crop_path = Path(crop_info.get("file", ""))
    crop_id   = crop_info.get("crop_id", "?")
    row       = crop_info.get("row", "?")
    col       = crop_info.get("col", "?")
    screenshot = crop_info.get("screenshot", "?")
    manifest_box  = crop_info.get("box")
    manifest_size = crop_info.get("size")

    base = {"crop_id": crop_id, "screenshot": screenshot, "row": row, "col": col,
            "file": str(crop_path)}

    # 1 — file existence
    if not crop_path.exists():
        return {**base, "status": "fail", "checks": {"file_exists": False},
                "issues": ["crop file missing"]}

    # 2 — file readable
    try:
        img = Image.open(crop_path)
        img.verify()
        img = Image.open(crop_path).convert("L")
    except Exception as exc:
        return {**base, "status": "fail",
                "checks": {"file_exists": True, "file_readable": False},
                "issues": [f"crop unreadable: {exc}"]}

    img_w, img_h = img.size
    checks = {
        "file_exists": True,
        "file_readable": True,
        "actual_width": img_w,
        "actual_height": img_h,
    }
    issues = []

    # 3 — dimensions
    w_ok = abs(img_w - exp_w) <= DIMENSION_TOLERANCE
    h_ok = abs(img_h - exp_h) <= DIMENSION_TOLERANCE
    checks["dimensions_ok"] = w_ok and h_ok
    if not w_ok or not h_ok:
        issues.append(
            f"unexpected dimensions {img_w}×{img_h} (expected ~{exp_w}×{exp_h})"
        )

    # 4 — crop was clamped at source edge (box shrank below expected size)
    checks["clamped"] = False
    if manifest_box:
        box_w = manifest_box["x1"] - manifest_box["x0"]
        box_h = manifest_box["y1"] - manifest_box["y0"]
        clamped = (box_w < exp_w - DIMENSION_TOLERANCE) or (
            box_h < exp_h - DIMENSION_TOLERANCE
        )
        if clamped:
            checks["clamped"] = True
            issues.append(
                f"crop box clamped at source edge "
                f"(box={box_w}×{box_h} px, expected ~{exp_w}×{exp_h} px)"
            )

    # 5 — title band stats
    ts = region_stats(img, TITLE_BAND)
    checks["title_mean"]     = ts["mean"]
    checks["title_variance"] = ts["variance"]
    title_app_background = ts["mean"] > TITLE_BRIGHT_WARN and ts["variance"] < TITLE_VARIANCE_WARN
    if title_app_background:
        issues.append(
            f"title band looks like app background "
            f"(mean={ts['mean']:.0f}>{TITLE_BRIGHT_WARN}, "
            f"variance={ts['variance']:.0f}<{TITLE_VARIANCE_WARN})"
        )

    # 6 — chip area stats
    cs = region_stats(img, CHIP_BAND)
    checks["chip_mean"]     = cs["mean"]
    checks["chip_variance"] = cs["variance"]
    chip_blank = cs["variance"] < CHIP_VARIANCE_WARN
    if chip_blank:
        issues.append(
            f"chip area too uniform — quantity badge may be missing or cut off "
            f"(variance={cs['variance']:.0f}<{CHIP_VARIANCE_WARN})"
        )

    # 7 — bottom separator (informational; expected to be bright/uniform)
    bs = region_stats(img, BOTTOM_BAND)
    checks["bottom_mean"]     = bs["mean"]
    checks["bottom_variance"] = bs["variance"]

    # Status
    hard_fail = not checks["dimensions_ok"] or checks["clamped"]
    if hard_fail:
        status = "fail"
    elif issues:
        status = "warning"
    else:
        status = "pass"

    return {**base, "status": status, "checks": checks, "issues": issues}


def main():
    parser = argparse.ArgumentParser(description="Evaluate crop quality for all card crops.")
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if report already exists.")
    args = parser.parse_args()

    if REPORT_JSON.exists() and not args.force:
        print(f"Report already exists: {REPORT_JSON}")
        print("Use --force to re-run.")
        sys.exit(0)

    if not MANIFEST_FILE.exists():
        print(f"ERROR: {MANIFEST_FILE} not found.  Run crop_all_screenshots.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    global_defaults = manifest.get("global_defaults", {})

    all_results = []
    by_screenshot = {}

    for ss in manifest.get("screenshots", []):
        filename = ss["filename"]
        ss_params = ss.get("calibration_params", global_defaults) or global_defaults
        exp_w = ss_params.get("card_width", 392)
        exp_h = ss_params.get("card_height_cell", 499)

        ss_results = []
        for crop_info in ss.get("crops", []):
            result = evaluate_crop(crop_info, exp_w, exp_h)
            all_results.append(result)
            ss_results.append(result)

        by_screenshot[filename] = ss_results
        p = sum(1 for r in ss_results if r["status"] == "pass")
        w = sum(1 for r in ss_results if r["status"] == "warning")
        f = sum(1 for r in ss_results if r["status"] == "fail")
        print(f"  {filename:20s}  pass={p}  warn={w}  fail={f}")

    counts = {s: sum(1 for r in all_results if r["status"] == s)
              for s in ("pass", "warning", "fail")}
    counts["total"] = len(all_results)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "dimension_tolerance": DIMENSION_TOLERANCE,
            "title_bright_warn": TITLE_BRIGHT_WARN,
            "title_variance_warn": TITLE_VARIANCE_WARN,
            "chip_variance_warn": CHIP_VARIANCE_WARN,
        },
        "summary": counts,
        "crops": all_results,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Markdown report ---
    screenshots_flagged = [
        fn for fn, results in by_screenshot.items()
        if any(r["status"] == "fail" for r in results)
        or sum(1 for r in results if r["status"] == "warning") >= 5
    ]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Crop Quality Report",
        "",
        f"Generated: {now}",
        "",
        f"**Total crops:** {counts['total']}  ",
        f"**Pass:** {counts['pass']}  ",
        f"**Warning:** {counts['warning']}  ",
        f"**Fail:** {counts['fail']}",
        "",
        "---",
        "",
        "## Summary by Screenshot",
        "",
        "| Screenshot | Total | Pass | Warn | Fail | Notes |",
        "|---|---|---|---|---|---|",
    ]

    for fn, results in by_screenshot.items():
        p = sum(1 for r in results if r["status"] == "pass")
        w = sum(1 for r in results if r["status"] == "warning")
        f = sum(1 for r in results if r["status"] == "fail")
        note = ""
        if f > 0 or w >= 5:
            note = "⚠ needs override review"
        elif w > 0:
            note = "minor warnings"
        lines.append(f"| {fn} | {len(results)} | {p} | {w} | {f} | {note} |")

    lines += [""]

    if screenshots_flagged:
        lines += [
            "## Screenshots Needing Override Review",
            "",
            "These screenshots have failures or ≥5 warnings. "
            "Add per-screenshot overrides in `config/crop_config.json`.",
            "See `crop_override_workflow.md` for the procedure.",
            "",
        ]
        for fn in screenshots_flagged:
            lines.append(f"- `{fn}`")
        lines += [""]

    problem_crops = [r for r in all_results if r["status"] != "pass"]
    if problem_crops:
        lines += ["## Problem Crops", ""]
        for r in problem_crops:
            icon = "❌" if r["status"] == "fail" else "⚠️"
            lines += [
                f"### {icon} `{r['crop_id']}` — {r['status'].upper()}",
                "",
            ]
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            c = r.get("checks", {})
            if "title_mean" in c:
                lines.append(
                    f"- Title band: mean={c['title_mean']:.0f}, variance={c['title_variance']:.0f}"
                )
            if "chip_variance" in c:
                lines.append(f"- Chip area variance: {c['chip_variance']:.0f}")
            lines.append(f"- File: `{r['file']}`")
            lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(
        f"Quality: {counts['pass']} pass, {counts['warning']} warning, {counts['fail']} fail"
        f"  (total {counts['total']})"
    )
    if screenshots_flagged:
        print(f"Screenshots needing override review ({len(screenshots_flagged)}):")
        for fn in screenshots_flagged:
            print(f"  - {fn}")
    print(f"JSON  →  {REPORT_JSON}")
    print(f"MD    →  {REPORT_MD}")


if __name__ == "__main__":
    main()
