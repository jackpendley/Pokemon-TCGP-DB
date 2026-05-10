# Crop Override Report

## Summary

Two screenshots required per-screenshot calibration overrides to correct misaligned crops.
All other 22 screenshots use the global default calibration (top_y=546).

---

## IMG_1527.PNG — Slightly Misaligned

### Problem

With the default `top_y=546`, the first card row started 40px too low in the image.
The binder grid in this screenshot actually begins at y=506, not y=546.

Effect on crops with default calibration:
- Row 1 crops (y=546–1045) missed the top 40px of row 1 cards
- Row 1 crops included 41px of row 2 card tops at the bottom
- Row 3 crops extended 40px past the row 3 separator into background

### Detection Method

Pixel-level separator band detection on the full-width image:

| Separator | y range | Width | Mean brightness |
|-----------|---------|-------|-----------------|
| After row 1 | 990–1003 | 14px | 217 |
| After row 2 | 1490–1505 | 16px | 219 |
| After row 3 | 1989–2005 | 17px | 217 |

Derived values:
- `tile_h` = sep1_start − top_y → top_y = 990 − 484 = **506**
- `card_height_cell` = sep2_start − sep1_start = 1490 − 990 = **500** (within 1px of default 499; kept default)

### Override Applied

```json
"IMG_1527.PNG": {
  "top_y": 506
}
```

Old value: `top_y=546` | New value: `top_y=506` | Correction: −40px

### New Crop Boxes

| Row | y range | Contains separator |
|-----|---------|-------------------|
| 1 | 506–1005 | sep1 at y=990–1003 ✓ |
| 2 | 1005–1504 | sep2 at y=1490–1505 ✓ |
| 3 | 1504–2003 | sep3 at y=1989–2005 ✓ |

### QA Result

All 9 crops: **PASS**. No dimension issues, no title-band app-background flags, chip area variance normal.

---

## IMG_1530.PNG — Significantly Misaligned

### Problem

With the default `top_y=546`, the first card row started 100px too low in the image.
The binder grid in this screenshot actually begins at y=446, not y=546.

Effect on crops with default calibration:
- Row 1 crops (y=546–1045) missed the top 100px of row 1 cards and name banners
- Row 1 crops included ~101px of row 2 card tops at the bottom
- Row 3 crops extended 100px past the row 3 separator into the app chrome below the grid

This is the most severe misalignment in the batch.

### Detection Method

Pixel-level separator band detection on the full-width image:

| Separator | y range | Width | Mean brightness |
|-----------|---------|-------|-----------------|
| After row 1 | 930–944 | 15px | 217 |
| After row 2 | 1429–1446 | 18px | 218 |

Note: 3 additional wide bright bands were detected at y=1699–1953, likely binder UI elements below the card grid rather than inter-row separators (those bands were 26–53px wide and inconsistent with the 14–18px separator pattern).

Derived values:
- `top_y` = sep1_start − tile_h = 930 − 484 = **446**
- `card_height_cell` = sep2_start − sep1_start = 1429 − 930 = **499** (matches default exactly)

### Override Applied

```json
"IMG_1530.PNG": {
  "top_y": 446
}
```

Old value: `top_y=546` | New value: `top_y=446` | Correction: −100px

### New Crop Boxes

| Row | y range | Contains separator |
|-----|---------|-------------------|
| 1 | 446–945 | sep1 at y=930–944 ✓ |
| 2 | 945–1444 | sep2 at y=1429–1446 ✓ |
| 3 | 1444–1943 | sep3 approx at y=1928+ ✓ |

### QA Result

All 9 crops: **PASS**. No dimension issues, no title-band app-background flags, chip area variance normal.

---

## Overall QA After Overrides

| Metric | Value |
|--------|-------|
| Total crops | 216 |
| Pass | 215 |
| Warning | 1 (IMG_1547_r3c3 — likely empty binder slot at end of collection) |
| Fail | 0 |
| Screenshots using override | 2 (IMG_1527, IMG_1530) |
| Screenshots using default | 22 |

---

## User Visual Re-check Recommended

Please inspect the contact sheets for IMG_1527 and IMG_1530 to confirm:
- Row 1 cards show the full name banner and top of artwork
- Row 3 quantity chips are visible at the bottom-left of each crop
- No visible bleed from adjacent rows

Contact sheets: `review/contact_sheets/IMG_1527_contact.png` and `review/contact_sheets/IMG_1530_contact.png`

If any crop still looks off, adjust the override in `config/crop_config.json` and re-run:
```bash
python3 scripts/crop_all_screenshots.py --force
python3 scripts/evaluate_crop_quality.py --force
python3 scripts/create_contact_sheets.py
```
