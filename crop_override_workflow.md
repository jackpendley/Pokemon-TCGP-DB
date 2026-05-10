# Crop Override Workflow

This document explains how to fix misaligned crops for specific screenshots without reprocessing every screenshot manually.

---

## Do Not Manually Crop Individual Cards

Manual cropping of 216 cards across 24 screenshots is not the right approach. Instead:

1. Let the automated pipeline generate all crops.
2. Review the contact sheets and QA report.
3. Add per-screenshot overrides **only** for screenshots that are misaligned.
4. Rerun only the affected screenshots.

Manual 3×3 grid cropping (`scripts/crop_3x3_cards.py`) is a last-resort fallback for a single screenshot that cannot be fixed by calibration.

---

## Recommended Workflow

### Step 1 — Generate all crops

```bash
python3 scripts/crop_all_screenshots.py --force
```

Outputs: `crops/IMG_XXXX/r1c1.png` … `r3c3.png` for every screenshot.

---

### Step 2 — Evaluate crop quality

```bash
python3 scripts/evaluate_crop_quality.py
```

Outputs:
- `data/extraction/crop_quality_report.json` — machine-readable pass/warning/fail for every crop
- `review/crop_quality_report.md` — human-readable summary with screenshots needing attention

---

### Step 3 — Generate contact sheets

```bash
python3 scripts/create_contact_sheets.py
```

Outputs: `review/contact_sheets/<stem>_contact.png`

Contact sheets show each card thumbnail with its row/column label and QA status badge (PASS / WARN / FAIL) if the quality report is present.

---

### Step 4 — Visually inspect contact sheets

Open the per-screenshot contact sheets in `review/contact_sheets/`. Focus on screenshots flagged in `review/crop_quality_report.md`.

Signs of misalignment:
- App chrome (navigation bar, binder header) visible at top of row 1 crops
- Quantity chips cut off at the bottom of row 3 crops
- Cards from the wrong row appearing in a crop

---

### Step 5 — Add per-screenshot overrides (only for bad screenshots)

Open `config/crop_config.json` and add entries to `per_screenshot_overrides`.

**Example:** If `IMG_1525.PNG` has its row 1 starting 2px lower than the default:

```json
{
  "per_screenshot_overrides": {
    "IMG_1525.PNG": {
      "top_y": 548
    }
  }
}
```

You may override any of these keys:

| Key | Effect |
|-----|--------|
| `top_y` | Shifts all rows up or down |
| `left_x` | Shifts all columns left or right |
| `card_width` | Adjusts column width |
| `card_height_tile` | Adjusts tile content height |
| `row_gap` | Adjusts separator gap height |
| `card_height_cell` | Overrides the step between rows directly |

If you set `card_height_tile` and/or `row_gap` but not `card_height_cell`, it is recomputed automatically.

---

### Step 6 — Rerun only for the screenshots you fixed

```bash
python3 scripts/crop_all_screenshots.py --force
python3 scripts/evaluate_crop_quality.py --force
python3 scripts/create_contact_sheets.py
```

Inspect the contact sheets again. Repeat Steps 4–6 until quality is acceptable.

---

### Step 7 — Proceed to OCR and matching

Only proceed to OCR/matching once crop QA is acceptable:

```bash
python3 scripts/ocr_card_crops.py --force
python3 scripts/match_ocr_to_reference.py
python3 scripts/generate_review_report.py
```

---

## Override Configuration Reference

`config/crop_config.json` structure:

```json
{
  "version": 1,
  "defaults": {
    "left_x": 3,
    "top_y": 546,
    "card_width": 392,
    "card_height_tile": 484,
    "row_gap": 15,
    "card_height_cell": 499
  },
  "per_screenshot_overrides": {
    "IMG_1525.PNG": {
      "top_y": 548,
      "left_x": 3
    },
    "IMG_1531.PNG": {
      "top_y": 542,
      "card_height_tile": 486
    }
  }
}
```

The manifest (`data/extraction/crop_manifest.json`) records `calibration_source` ("default" or "override") and `calibration_params` for each screenshot so you can audit which calibration was used.

---

## Fallback: Manual Single-Screenshot Crop

If a screenshot cannot be fixed by calibration overrides, use the single-screenshot crop tool as a one-off:

```bash
python3 scripts/crop_3x3_cards.py screenshots/IMG_XXXX.PNG crops/IMG_XXXX \
    --top-y 550 --card-height 501
```

This is for exceptional cases only. Do not use it to process all 24 screenshots.
