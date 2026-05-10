# Field Detection Evaluation Report

Generated: 2026-05-10T17:45:39Z
Confirmed positions: 55  |  Tesseract available: True

## Quantity Detection

| Metric | Value |
|---|---|
| Total confirmed | 55 |
| Quantity found by OCR | 7 (13%) |
| Quantity correct | 5 (9%) |

## is_ex Detection (name-pattern heuristic)

| Metric | Value |
|---|---|
| Total confirmed | 55 |
| Correct | 49 (89%) |
| False positives (predicted True, confirmed False) | 0 |
| False negatives (predicted False, confirmed True) | 6 |

## Card-Name Detection (from match_candidates)

| Metric | Value |
|---|---|
| Total confirmed | 55 |
| Top-1 correct | 10 (18%) |
| Top-3 correct | 18 (33%) |

## Recommendations

- Quantity OCR accuracy is low — chip region or thresholding may need tuning
- is_ex detection 89% accuracy — name-pattern heuristic is reliable for prefilling
- Card-name top-3 accuracy 33% — useful as review hint but not for auto-fill

## Per-Crop Results

| Crop | Confirmed Name | Qty OK | is_ex OK | Name Top-1 | Name Top-3 |
|---|---|---|---|---|---|
| IMG_1524_r1c1 | Quick-Grow Extract | — | ✓ | ✓ | ✓ |
| IMG_1524_r1c2 | Blaziken | — | ✓ | ✗ | ✗ |
| IMG_1524_r1c3 | Skrelp | — | ✓ | ✗ | ✓ |
| IMG_1524_r2c1 | Sobble | — | ✓ | ✗ | ✗ |
| IMG_1524_r2c2 | Clemont | — | ✓ | ✓ | ✓ |
| IMG_1524_r2c3 | Bulbasaur | — | ✓ | ✗ | ✗ |
| IMG_1524_r3c1 | Shroomish | — | ✓ | ✗ | ✗ |
| IMG_1524_r3c2 | Tepig | — | ✓ | ✗ | ✗ |
| IMG_1524_r3c3 | Zekrom | ✓ | ✓ | ✗ | ✗ |
| IMG_1525_r1c1 | Morpeko | — | ✓ | ✗ | ✗ |
| IMG_1525_r1c2 | Bonsly | — | ✓ | ✗ | ✗ |
| IMG_1525_r1c3 | Riolu | ✗ | ✓ | ✓ | ✓ |
| IMG_1525_r2c1 | Meltan | — | ✓ | ✗ | ✗ |
| IMG_1525_r2c2 | Moltres | — | ✗ | ✗ | ✗ |
| IMG_1525_r2c3 | Marowak | — | ✗ | ✗ | ✓ |
| IMG_1525_r3c1 | Incineroar | — | ✗ | ✗ | ✗ |
| IMG_1525_r3c2 | Mega Venusaur ex | — | ✓ | ✗ | ✗ |
| IMG_1525_r3c3 | Mega Charizard Y ex | ✗ | ✓ | ✗ | ✗ |
| IMG_1526_r1c1 | Vaporeon | — | ✗ | ✗ | ✗ |
| IMG_1526_r1c2 | Magnezone | — | ✗ | ✗ | ✓ |
| IMG_1526_r1c3 | Corviknight | — | ✗ | ✗ | ✗ |
| IMG_1526_r2c1 | Eelektross | — | ✓ | ✗ | ✗ |
| IMG_1526_r2c2 | Charizard | — | ✓ | ✗ | ✗ |
| IMG_1526_r2c3 | Genesect | — | ✓ | ✗ | ✗ |
| IMG_1526_r3c1 | Hearthflame Mask Ogerpon | — | ✓ | ✗ | ✗ |
| IMG_1526_r3c2 | Yveltal | — | ✓ | ✗ | ✗ |
| IMG_1526_r3c3 | Budew | — | ✓ | ✗ | ✓ |
| IMG_1527_r1c1 | Victini | — | ✓ | ✗ | ✗ |
| IMG_1527_r1c2 | Meloetta | — | ✓ | ✗ | ✗ |
| IMG_1527_r1c3 | Crobat | — | ✓ | ✗ | ✗ |
| IMG_1527_r2c1 | Urshifu | — | ✓ | ✗ | ✗ |
| IMG_1527_r2c2 | Stoutland | — | ✓ | ✗ | ✗ |
| IMG_1527_r2c3 | Sandslash | ✓ | ✓ | ✗ | ✗ |
| IMG_1527_r3c1 | Onix | — | ✓ | ✗ | ✗ |
| IMG_1527_r3c2 | Mienshao | — | ✓ | ✗ | ✓ |
| IMG_1527_r3c3 | Dodrio | ✓ | ✓ | ✗ | ✗ |
| IMG_1528_r1c1 | Giovanni | — | ✓ | ✓ | ✓ |
| IMG_1528_r1c2 | Sabrina | — | ✓ | ✓ | ✓ |
| IMG_1528_r1c3 | Leaf | — | ✓ | ✓ | ✓ |
| IMG_1528_r2c1 | Cyrus | — | ✓ | ✗ | ✗ |
| IMG_1528_r2c2 | Rare Candy | — | ✓ | ✓ | ✓ |
| IMG_1528_r2c3 | Lillie | ✓ | ✓ | ✓ | ✓ |
| IMG_1528_r3c1 | Giant Cape | — | ✓ | ✓ | ✓ |
| IMG_1528_r3c2 | Arcanine | — | ✓ | ✗ | ✗ |
| IMG_1528_r3c3 | Turtonator | ✓ | ✓ | ✗ | ✗ |
| IMG_1529_r1c1 | Palossand | — | ✓ | ✗ | ✗ |
| IMG_1529_r1c2 | Flame Patch | — | ✓ | ✗ | ✗ |
| IMG_1529_r1c3 | May | — | ✓ | ✓ | ✓ |
| IMG_1529_r2c1 | Copycat | — | ✓ | ✗ | ✗ |
| IMG_1529_r2c2 | Ivysaur | — | ✓ | ✗ | ✗ |
| IMG_1529_r2c3 | Wartortle | — | ✓ | ✗ | ✓ |
| IMG_1529_r3c1 | Clawitzer | — | ✓ | ✗ | ✗ |
| IMG_1529_r3c2 | Magneton | — | ✓ | ✗ | ✓ |
| IMG_1529_r3c3 | Heliolisk | — | ✓ | ✗ | ✓ |
| IMG_0000_r1c1 | Example Card | — | ✓ | ✗ | ✗ |