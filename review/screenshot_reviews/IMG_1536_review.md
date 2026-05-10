# IMG_1536.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1536_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=514
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `Dratini 70` | **Dratini** (82), Drapion (58), Dragonair (52) | stage=Basic; type=Dragon; rarity=one_diamond; set=B2b |  | |
| r1c2 | `'Pidgey 60` | **Pidgey** (80), Pidgeot (62), Pidgeotto (55) | stage=Basic; type=Colorless; rarity=one_diamond; set=B1 |  | |
| r1c3 | `Rattata 40` | **Rattata** (82), Raticate (55), Patrat (50) | — |  | |
| r2c1 | `spe Raticate 64480` | Raticate (61), Dragonite ex (46), Caterpie (46) | — |  | |
| r2c2 | `Jigglypuff 50 *` | **Jigglypuff** (87), Wigglytuff (69), Sigilyph (47) | stage=Basic; type=Colorless; rarity=one_diamond; set=B2b |  | |
| r2c3 | `<< Farfetch’d 60 *)` | Flame Patch (50), Fletchling (43), Rare Candy (43) | — |  | |
| r3c1 | `s'Dubwool 120` | Dubwool (70), Wooloo (42), Buzzwole ex (41) | — |  | |
| r3c2 | `*(no OCR text)*` | — | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Top candidate: Dratini (82). Confirm visually.
- **r1c2** — Top candidate: Pidgey (80). Confirm visually.
- **r1c3** — Top candidate: Rattata (82). Confirm visually.
- **r2c1** — Low confidence (61) (top: Raticate). Identify from contact sheet.
- **r2c2** — Top candidate: Jigglypuff (87). Confirm visually.
- **r2c3** — Low confidence (50) (top: Flame Patch). Identify from contact sheet.
- **r3c1** — Top candidate: Dubwool (70). Confirm visually.
- **r3c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1536_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1536_confirmed_TEMPLATE.csv review/confirmed/IMG_1536_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1536_confirmed.csv \
     --screenshot IMG_1536.PNG \
     --output batches/cards_batch_012.json
   python3 scripts/validate_batch.py batches/cards_batch_012.json
   ```
