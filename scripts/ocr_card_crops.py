#!/usr/bin/env python3
"""
OCR the card-name band from each cropped card image.

Reads:   data/extraction/crop_manifest.json
Outputs: data/extraction/ocr_results.json

Usage:
    python3 scripts/ocr_card_crops.py [--force]

Requirements:
    pip install pytesseract Pillow
    brew install tesseract   (macOS) or equivalent

If pytesseract or the tesseract binary is unavailable, the script reports
exactly what is missing and writes placeholder results so downstream steps
can still run.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    print("ERROR: Pillow is required.  Install with:  python3 -m pip install Pillow")
    sys.exit(1)

MANIFEST_FILE = Path("data/extraction/crop_manifest.json")
OCR_OUT = Path("data/extraction/ocr_results.json")

# ---------------------------------------------------------------------------
# Name-band region within each card crop.
# Cards in the PTCGP binder view at 1179×2556 crop to roughly 392×499 px.
# The card name appears in a banner at the TOP of the card tile, but may be
# accompanied by noise (HP value, energy icons, type labels).
# A wider band (y=0–70) captures the full name region.
# Grayscale + SHARPEN + 3× upscale gives the best results on game fonts.
# ---------------------------------------------------------------------------
NAME_BAND = {
    "x0": 10,
    "y0": 0,
    "x1": 380,
    "y1": 70,
}

# psm 6 = assume a uniform block of text (better than psm 7 for multi-line card banners)
TESS_CONFIG = r"--oem 3 --psm 6"


def check_dependencies():
    issues = []

    pytesseract_ok = False
    try:
        import pytesseract  # noqa: F401
        pytesseract_ok = True
    except ImportError:
        issues.append(
            "pytesseract not installed.  Run:  python3 -m pip install pytesseract"
        )

    tesseract_ok = shutil.which("tesseract") is not None
    if not tesseract_ok:
        issues.append(
            "tesseract binary not found.  On macOS run:  brew install tesseract"
        )

    return pytesseract_ok, tesseract_ok, issues


def clean_name(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"[^A-Za-z0-9 '\-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ocr_crop(img_path: Path, pytesseract_mod) -> tuple:
    # Grayscale is more reliable than RGB for PTCGP card fonts on colored backgrounds
    img = Image.open(img_path).convert("L")
    band = img.crop(
        (NAME_BAND["x0"], NAME_BAND["y0"], NAME_BAND["x1"], NAME_BAND["y1"])
    )
    # Upscale 3× + sharpen to improve OCR accuracy on small text
    band = band.filter(ImageFilter.SHARPEN).resize(
        (band.width * 3, band.height * 3), Image.LANCZOS
    )

    try:
        raw_text = pytesseract_mod.image_to_string(band, config=TESS_CONFIG)
    except Exception:
        raw_text = ""

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    joined = " | ".join(lines)
    avg_conf = 0.5 if lines else 0.0  # non-zero when any text found

    return joined, clean_name(joined), avg_conf, lines


def main():
    parser = argparse.ArgumentParser(description="OCR card name bands from crop images.")
    parser.add_argument(
        "--force", action="store_true", help="Re-run OCR even if output already exists."
    )
    args = parser.parse_args()

    if OCR_OUT.exists() and not args.force:
        print(f"OCR output already exists: {OCR_OUT}")
        print("Use --force to re-run.")
        sys.exit(0)

    if not MANIFEST_FILE.exists():
        print(f"ERROR: {MANIFEST_FILE} not found.  Run crop_all_screenshots.py first.")
        sys.exit(1)

    pytesseract_ok, tesseract_ok, issues = check_dependencies()
    if issues:
        print("WARNING: OCR dependencies missing:")
        for issue in issues:
            print(f"  • {issue}")
        print("Continuing with empty OCR results — downstream steps will still run.\n")

    pytesseract_mod = None
    if pytesseract_ok and tesseract_ok:
        import pytesseract as _pt
        pytesseract_mod = _pt

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    OCR_OUT.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for ss in manifest.get("screenshots", []):
        for crop_info in ss.get("crops", []):
            crop_path = Path(crop_info["file"])
            raw, cleaned, conf, lines = ("", "", 0.0, [])

            if pytesseract_mod and crop_path.exists():
                try:
                    raw, cleaned, conf, lines = ocr_crop(crop_path, pytesseract_mod)
                except Exception as exc:
                    print(f"  WARN  OCR failed for {crop_path}: {exc}")

            results.append({
                "crop_id": crop_info["crop_id"],
                "screenshot": crop_info["screenshot"],
                "row": crop_info["row"],
                "col": crop_info["col"],
                "raw_ocr_text": raw,
                "ocr_lines": lines,
                "cleaned_title_guess": cleaned,
                "confidence": conf,
            })

            status = f"{cleaned!r} ({conf:.2f})" if cleaned else "(empty)"
            print(f"  {crop_info['crop_id']:30s}  {status}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ocr_available": pytesseract_ok and tesseract_ok,
        "results": results,
    }
    OCR_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nOCR results ({len(results)} crops)  →  {OCR_OUT}")


if __name__ == "__main__":
    main()
