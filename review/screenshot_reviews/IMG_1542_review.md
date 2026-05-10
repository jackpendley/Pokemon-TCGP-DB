# IMG_1542.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1542_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=477
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `*(no OCR text)*` | — | — |  | |
| r1c2 | `setforry sat)` | Castform (60), Float Stone (52), Castform Sunny Form (51) | — |  | |
| r1c3 | `*(no OCR text)*` | — | — |  | |
| r2c1 | `VY SF` | Scrafty (50), Shiftry (50), Silvally (46) | — |  | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `<< Wooper | 60` | **Wooper** (80), Paldean Wooper (60), Super Potion (47) | stage=Basic; type=Water; rarity=one_diamond; set=B3 |  | |
| r3c1 | `*(no OCR text)*` | — | — |  | |
| r3c2 | `Castformsaairem 70` | Castform (61), Castform Sunny Form (54), Castform Rainy Form (54) | — |  | |
| r3c3 | `el` | Seel (66), Numel (57), Elesa (57) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r1c2** — Low confidence (60) (top: Castform). Identify from contact sheet.
- **r1c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c1** — Low confidence (50) (top: Scrafty). Identify from contact sheet.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — Top candidate: Wooper (80). Confirm visually.
- **r3c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c2** — Low confidence (61) (top: Castform). Identify from contact sheet.
- **r3c3** — Low confidence (66) (top: Seel). Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1542_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1542_confirmed_TEMPLATE.csv review/confirmed/IMG_1542_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1542_confirmed.csv \
     --screenshot IMG_1542.PNG \
     --output batches/cards_batch_018.json
   python3 scripts/validate_batch.py batches/cards_batch_018.json
   ```
