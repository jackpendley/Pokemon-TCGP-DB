# Screenshot-to-Collection Alignment

> **No OCR was used.** This alignment is order-only (sequential positional mapping).
> Card names are **not verified** against screenshot images.
> Confidence scores reflect structural position uncertainty, not card identity certainty.

## Summary

| Metric | Value |
|---|---|
| Collection entries | 224 |
| Screenshot slots | 232 |
| Aligned (entry assigned) | 224 |
| Surplus slots (no entry) | 8 |
| Generated at | 2026-05-12T03:26:16+00:00 |

## Confidence Distribution

| Tier | Count | Score Range |
|---|---|---|
| high | 0 | ≥ 0.95 |
| medium | 0 | 0.80–0.949 |
| low | 224 | 0.50–0.799 |
| unresolved | 8 | < 0.50 or no entry |

## Structural Assumptions

1. Entries in collection_normalized.json are in the same sequential display order as the PTCGP app collection grid (set/expansion order).
2. Screenshots are ordered by filename (IMG_1556–IMG_1581), which corresponds to the user's downward scroll order through the collection grid.
3. Within each screenshot, slots are traversed r1c1→r1c2→r1c3→r2c1→r2c2→r2c3→r3c1→r3c2→r3c3 (left-to-right, top-to-bottom).
4. The first 224 slots (indices 0–223) map sequentially to collection entries 0–223.
5. The remaining 8 slots (indices 224–231) are surplus with no entry assignment. Most likely explanation: IMG_1581 is a scroll-overlap screenshot showing cards also visible in IMG_1580, or the final row of the app grid contains 1–2 empty trailing positions.
6. No OCR or image matching was used. Alignment is order-only.
7. Confidence >= 0.95 (high) is NOT awarded without OCR or image name confirmation.

## Confidence Model

- Base score (mid-row, non-final): **0.7**
- Boundary row penalty (r1 or r3): −0.08
- Final screenshot penalty: −0.15
- Surplus slot (no entry): **0.0**

> Maximum achievable score in no-OCR phase = **0.70** (r2 slot, non-final screenshot).
> No alignment record in this phase can reach high-confidence (≥ 0.95).

## Surplus Slots

8 slots have no entry assignment. Likely: 1 trailing empty grid position (IMG_1580 r3c3) + 7 scroll-overlap slots in IMG_1581 that duplicate the last 7 entries of IMG_1580. Requires OCR to confirm.

| Slot index | File | Position | Is final |
|---|---|---|---|
| 224 | IMG_1580.jpg | r3c3 | False |
| 225 | IMG_1581.jpg | r1c1 | True |
| 226 | IMG_1581.jpg | r1c2 | True |
| 227 | IMG_1581.jpg | r1c3 | True |
| 228 | IMG_1581.jpg | r2c1 | True |
| 229 | IMG_1581.jpg | r2c2 | True |
| 230 | IMG_1581.jpg | r2c3 | True |
| 231 | IMG_1581.jpg | r3c1 | True |

## Aligned Records (first 20)

| Slot | File | Position | Entry ID | Card Name | Count | HP | Confidence | Tier | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 0 | IMG_1556.jpg | r1c1 | charmander | Charmander | 4 | 60 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 1 | IMG_1556.jpg | r1c2 | charmander_flame_tail_art | Charmander | 2 | 70 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 2 | IMG_1556.jpg | r1c3 | charmeleon | Charmeleon | 2 | 80 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 3 | IMG_1556.jpg | r2c1 | charizard | Charizard | 1 | 150 | 0.7 | low | sequential_order_alignment |
| 4 | IMG_1556.jpg | r2c2 | mega_charizard_y_ex | Mega Charizard Y ex | 2 | 220 | 0.7 | low | sequential_order_alignment |
| 5 | IMG_1556.jpg | r2c3 | tepig | Tepig | 2 | 60 | 0.7 | low | sequential_order_alignment |
| 6 | IMG_1556.jpg | r3c1 | pignite | Pignite | 4 | 100 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 7 | IMG_1556.jpg | r3c2 | incineroar_ex | Incineroar ex | 1 | 180 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 8 | IMG_1556.jpg | r3c3 | houndour | Houndour | 1 | 60 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 9 | IMG_1557.jpg | r1c1 | houndoom | Houndoom | 1 | 90 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 10 | IMG_1557.jpg | r1c2 | moltres_ex | Moltres ex | 1 | 140 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 11 | IMG_1557.jpg | r1c3 | hearthflame_mask_ogerpon | Hearthflame Mask Ogerpon | 1 | 80 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 12 | IMG_1557.jpg | r2c1 | victini | Victini | 4 | 70 | 0.7 | low | sequential_order_alignment |
| 13 | IMG_1557.jpg | r2c2 | turtonator | Turtonator | 2 | 110 | 0.7 | low | sequential_order_alignment |
| 14 | IMG_1557.jpg | r2c3 | arcanine | Arcanine | 1 | 120 | 0.7 | low | sequential_order_alignment |
| 15 | IMG_1557.jpg | r3c1 | darumaka | Darumaka | 2 | 60 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 16 | IMG_1557.jpg | r3c2 | darmanitan | Darmanitan | 3 | 120 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 17 | IMG_1557.jpg | r3c3 | larvesta | Larvesta | 3 | 80 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 18 | IMG_1558.jpg | r1c1 | numel | Numel | 2 | 70 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| 19 | IMG_1558.jpg | r1c2 | castform_sunny_form | Castform Sunny Form | 1 | 70 | 0.62 | low | sequential_order_alignment; boundary_row_penalty |
| … | … | … | … | … | … | … | … | … | … |
_(Full data in `data/exports/screenshot_collection_alignment.csv`)_

## Warnings

- All confidence scores are order-based positional estimates only.
- No card name verification has been performed against screenshot images.
- High confidence (>= 0.95) is not awarded in this no-OCR phase.
- Surplus slots may be scroll-overlap duplicates or empty trailing positions; OCR is required to distinguish.
- Do not use this alignment as ground truth. Use it as a starting point for the next confidence scoring phase.

