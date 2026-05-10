# Crop Override Report

## Summary

17 screenshots required per-screenshot calibration overrides (top_y corrections) to prevent card name banners from being clipped.
7 screenshots use the global default calibration (top_y=546).

All 216 crops: **215 pass, 1 warning (IMG_1547_r3c3 empty binder slot), 0 fail.**

---

## Override Table

| Screenshot | Default top_y | Override top_y | Offset | Pass |
|---|---|---|---|---|
| IMG_1524.PNG | 546 | — (default) | +1 | ✓ 9/9 |
| IMG_1525.PNG | 546 | — (default) | +14 | ✓ 9/9 |
| IMG_1526.PNG | 546 | — (default) | +27 | ✓ 9/9 |
| IMG_1527.PNG | 546 | **506** | −40 | ✓ 9/9 |
| IMG_1528.PNG | 546 | **493** | −53 | ✓ 9/9 |
| IMG_1529.PNG | 546 | — (default) | −12 | ✓ 9/9 |
| IMG_1530.PNG | 546 | **446** | −100 | ✓ 9/9 |
| IMG_1531.PNG | 546 | **514** | −32 | ✓ 9/9 |
| IMG_1532.PNG | 546 | **519** | −27 | ✓ 9/9 |
| IMG_1533.PNG | 546 | **463** | −83 | ✓ 9/9 |
| IMG_1534.PNG | 546 | **486** | −60 | ✓ 9/9 |
| IMG_1535.PNG | 546 | **491** | −55 | ✓ 9/9 |
| IMG_1536.PNG | 546 | **514** | −32 | ✓ 9/9 |
| IMG_1537.PNG | 546 | **520** | −26 | ✓ 9/9 |
| IMG_1538.PNG | 546 | **489** | −57 | ✓ 9/9 |
| IMG_1539.PNG | 546 | — (default) | −12 | ✓ 9/9 |
| IMG_1540.PNG | 546 | **463** | −83 | ✓ 9/9 |
| IMG_1541.PNG | 546 | — (default) | −10 | ✓ 9/9 |
| IMG_1542.PNG | 546 | **477** | −69 | ✓ 9/9 |
| IMG_1543.PNG | 546 | **475** | −71 | ✓ 9/9 |
| IMG_1544.PNG | 546 | **517** | −29 | ✓ 9/9 |
| IMG_1545.PNG | 546 | **486** | −60 | ✓ 9/9 |
| IMG_1546.PNG | 546 | **494** | −52 | ✓ 9/9 |
| IMG_1547.PNG | 546 | — (default) | +18 | ✓ 8/9 (r3c3 empty slot) |

---

## Detection Method

Pixel-level separator band detection on the full-width image.

For each screenshot, scan every row for:
- Mean brightness > 210
- Variance < 60
- Bright-pixel fraction (value ≥ 200) > 0.88

Find contiguous qualifying row bands ≥ 10 rows wide. The first band is the inter-row separator after row 1 (sep1).

Derived values:
- `top_y = sep1_start − card_height_tile (484)`
- `card_height_cell = sep2_start − sep1_start` — verified ≈ 499 for all screenshots

---

## Tuning Passes

### Pass 1 — Initial user QA (IMG_1527, IMG_1530)

User reported two screenshots visually misaligned on contact sheet inspection.
Separator detection computed overrides; both screenshots re-QA'd and confirmed passing.

### Pass 2 — Full-batch sweep

User reported IMG_1532 still clips Pokémon names (−27px offset confirmed threshold).
User reported IMG_1533 worse (−83px offset confirmed).
Pattern: most later screenshots also have negative offsets.

Full separator detection run across all 24 screenshots confirmed:
- 7 screenshots have offsets ≤ −20px that were already passing default QA but would clip names
- 15 additional overrides written to `config/crop_config.json`
- Re-crop (`--force`) applied all 17 overrides
- Final QA: 215 pass, 1 warning (known empty slot), 0 fail

No monotonic drift pattern — each screenshot's `top_y` is independent of its neighbors.
All `card_height_cell` step measurements are within 498–504px (default 499 correct for all).

---

## Next Steps

Crop QA is complete. All 216 crops are correctly aligned.

Proceed to card identification:
1. Run OCR: `python3 scripts/ocr_card_crops.py`
2. Match: `python3 scripts/match_ocr_to_reference.py`
3. Review: `python3 scripts/generate_review_report.py`
4. Open `review/review_needed.md` and confirm card names
5. Create batch files per screenshot
