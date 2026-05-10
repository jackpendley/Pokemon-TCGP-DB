# IMG_1541.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1541_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** default
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `*(no OCR text)*` | — | — |  | |
| r1c2 | `“= Tangela 80` | **Tangela** (82), Tandemaus (52), Talonflame (50) | stage=Basic; type=Grass; rarity=one_star; set=B2 |  | |
| r1c3 | `- Treecko 60` | **Treecko** (82), Trevor (50), Morpeko (47) | stage=Basic; type=Grass; rarity=one_diamond; set=B3 |  | |
| r2c1 | `*(no OCR text)*` | — | — |  | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `*(no OCR text)*` | — | — |  | |
| r3c1 | `Sewaddle w60` | **Sewaddle** (80), Sandile (52), Roserade (50) | stage=Basic; type=Grass; rarity=one_diamond; set=B3 |  | |
| r3c2 | `Swadioon 80` | Swadloon (73), Gladion (55), Silcoon (55) | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r1c2** — Top candidate: Tangela (82). Confirm visually.
- **r1c3** — Top candidate: Treecko (82). Confirm visually.
- **r2c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c1** — Top candidate: Sewaddle (80). Confirm visually.
- **r3c2** — Top candidate: Swadloon (73). Confirm visually.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1541_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1541_confirmed_TEMPLATE.csv review/confirmed/IMG_1541_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1541_confirmed.csv \
     --screenshot IMG_1541.PNG \
     --output batches/cards_batch_018.json
   python3 scripts/validate_batch.py batches/cards_batch_018.json
   ```
