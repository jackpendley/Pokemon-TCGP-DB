# Crop Calibration Report

## Summary

The initial crop calibration was incorrect. The `top_y` origin was set 311 px too high, placing it inside the app chrome rather than at the start of the card grid. Combined with a slightly underestimated cell height, this caused the row 3 crop boxes to end at y=1720, missing the row 3 quantity chips entirely (which sit at y≈1998–2028).

The calibration was corrected by empirically detecting the uniform inter-row separator bands in the original screenshots using pixel-level analysis.

---

## Old (Incorrect) Calibration

| Parameter | Old Value | Effect |
|-----------|-----------|--------|
| `top_y` | 235 | Started inside the binder app chrome/header, 311 px above the first card row |
| `card_height` | 495 | Both the crop height and the row step — slightly too small |
| `left_x` | 3 | Correct |
| `card_width` | 392 | Correct |

### What each old crop actually showed

| Crop | y range | Actual content |
|------|---------|----------------|
| r1c1–r1c3 | 235–730 | ~311 px of app chrome + top ~184 px of row 1 cards (name band visible, rest cut off) |
| r2c1–r2c3 | 730–1225 | Bottom ~300 px of row 1 cards (including row 1 quantity chips) + top ~180 px of row 2 cards |
| r3c1–r3c3 | 1225–1720 | Bottom ~299 px of row 2 cards (including row 2 quantity chips) + top ~175 px of row 3 cards |

No crop captured a complete card tile. Row 3 quantity chips (y≈1998–2028) were entirely outside all crop windows.

---

## Root Cause Analysis

The calibration was established based on a guess rather than measurement. The binder view in Pokémon TCG Pocket (iPhone 15 Pro, 1179×2556 px) has:

- Fixed app chrome (status bar + navigation bar): y=0–235
- Scrollable binder header (tab selector + card count): y=235–496
- Solid binder background above row 1: y=496–545 (50 px, nearly zero pixel variance — detected as a uniform bright band)
- **Row 1 card content starts: y=546**

Inter-row separator bands were detected by scanning for high-brightness, low-variance, high-bright-fraction horizontal strips across the full image width:

| Separator | y range | Width |
|-----------|---------|-------|
| After row 1 | 1030–1044 | 15 px |
| After row 2 | 1529–1544 | 16 px |
| After row 3 | 2029–2042 | 14 px |

From these measurements:
- **Card tile content height**: 1030 − 546 = **484 px**
- **Cell height** (tile + separator): 484 + 15 = **499 px**
- **Row 2 start**: 546 + 499 = **1045 px** ✓ (matches separator end at 1044)
- **Row 3 start**: 1045 + 499 = **1544 px** ✓ (matches separator end at 1544)

---

## New (Correct) Calibration

| Constant | Value | Description |
|----------|-------|-------------|
| `GRID_LEFT_X` | 3 | x-origin of the leftmost card column |
| `GRID_TOP_Y` | 546 | y-origin of row 1 card content |
| `CARD_WIDTH` | 392 | Width of one card tile column |
| `CARD_HEIGHT_TILE` | 484 | Card tile content height (no separator) |
| `ROW_GAP` | 15 | Inter-row binder separator height |
| `CARD_HEIGHT_CELL` | 499 | Step between row origins (tile + gap) |

`DEFAULT_PARAMS["top_y"] = GRID_TOP_Y = 546`
`DEFAULT_PARAMS["card_height"] = CARD_HEIGHT_CELL = 499`

### What each new crop shows

| Crop | y range | Content |
|------|---------|---------|
| r1c1–r1c3 | 546–1045 | Complete row 1 card (484 px) + 15 px separator |
| r2c1–r2c3 | 1045–1544 | Complete row 2 card (484 px) + 15 px separator |
| r3c1–r3c3 | 1544–2043 | Complete row 3 card (484 px) + 15 px separator |

### Quantity chip coverage

- Row 1 chip zone: y≈1015–1030 → within crop y=546–1045 ✓
- Row 2 chip zone: y≈1514–1529 → within crop y=1045–1544 ✓
- Row 3 chip zone: y≈1998–2028 → within crop y=1544–2043 ✓

All quantity chips are now captured in their respective crop rows.

---

## Verification Results (post-fix)

- **24 screenshots processed**, 216 crops total (9 per screenshot)
- **All crops**: 392×499 px, all boxes within 1179×2556 bounds
- **Zero-byte files**: none
- **Visual inspection** (r1c1, r3c1 from IMG_1524): both show complete cards with quantity chip "1" visible at the bottom-left
- **All crop counts**: exactly 9 per screenshot across all 24 screenshots

---

## Can OCR/Matching Proceed?

Yes — once the user has visually confirmed the contact sheets look correct
(complete cards, no clipping, quantity chips visible for all rows), the
pipeline can proceed to:

1. `python3 scripts/build_card_reference.py`
2. `python3 scripts/ocr_card_crops.py`
3. `python3 scripts/match_ocr_to_reference.py`
4. `python3 scripts/generate_review_report.py`
