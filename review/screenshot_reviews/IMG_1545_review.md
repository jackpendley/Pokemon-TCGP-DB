# IMG_1545.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1545_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=486
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `*(no OCR text)*` | — | — |  | |
| r1c2 | `it a ep` | Giant Cape (58), Repeat Ball (55), Caterpie (53) | — |  | |
| r1c3 | `e Seviper 70` | Seviper (73), Sceptile ex (52), Expert Belt (52) | — |  | |
| r2c1 | `*(no OCR text)*` | — | — |  | |
| r2c2 | `pz 60 a` | Poké Ball (40), Paralyze Heal (40), Mega Pinsir ex (38) | — |  | |
| r2c3 | `Bronzor 60` | **Bronzor** (82), Bronzong (66), Byron (53) | stage=Basic; type=Metal; rarity=one_diamond; set=B3 |  | |
| r3c1 | `Chansey ue 100` | Chansey (66), Chandelure (58), Rare Candy (50) | — |  | |
| r3c2 | `2 Castform  § w70*` | Castform (72), Castform Snowy Form (60), Castform Sunny Form (54) | — |  | |
| r3c3 | `5 - 4` | Ho-Oh (25), Mew ex (22), Chi-Yu (22) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r1c2** — Low confidence (58) (top: Giant Cape). Identify from contact sheet.
- **r1c3** — Top candidate: Seviper (73). Confirm visually.
- **r2c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c2** — Low confidence (40) (top: Poké Ball). Identify from contact sheet.
- **r2c3** — Top candidate: Bronzor (82). Confirm visually.
- **r3c1** — Low confidence (66) (top: Chansey). Identify from contact sheet.
- **r3c2** — Top candidate: Castform (72). Confirm visually.
- **r3c3** — Low confidence (25) (top: Ho-Oh). Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1545_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1545_confirmed_TEMPLATE.csv review/confirmed/IMG_1545_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1545_confirmed.csv \
     --screenshot IMG_1545.PNG \
     --output batches/cards_batch_021.json
   python3 scripts/validate_batch.py batches/cards_batch_021.json
   ```
