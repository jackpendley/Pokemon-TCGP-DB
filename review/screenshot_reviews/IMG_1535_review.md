# IMG_1535.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1535_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=491
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `Cheren` | **Cheren** (100), Serena (66), Archen (66) | category=Supporter; rarity=two_diamond; set=B3 | *Cheren* ✓ | |
| r1c2 | `Arena of Antiquity |` | **Arena of Antiquity** (100), Rare Candy (50), Fantina (48) | category=Stadium; rarity=two_diamond; set=B3 | *Arena of Antiquity* ✓ | |
| r1c3 | `*(no OCR text)*` | — | — |  | |
| r2c1 | `TS` | Ralts (57), Tauros (50), Latias (50) | — |  | |
| r2c2 | `= Shellder | .60@` | **Shellder** (84), Shelly (58), Shellos (55) | stage=Basic; type=Water; rarity=one_star; set=B1a |  | |
| r2c3 | `*(no OCR text)*` | — | — |  | |
| r3c1 | `*(no OCR text)*` | — | — |  | |
| r3c2 | `*(no OCR text)*` | — | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — `Cheren` prefilled (autofill (score 100)). Confirm name and quantity.
- **r1c2** — `Arena of Antiquity` prefilled (autofill (score 100)). Confirm name and quantity.
- **r1c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c1** — Low confidence (57) (top: Ralts). Identify from contact sheet.
- **r2c2** — Top candidate: Shellder (84). Confirm visually.
- **r2c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1535_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1535_confirmed_TEMPLATE.csv review/confirmed/IMG_1535_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1535_confirmed.csv \
     --screenshot IMG_1535.PNG \
     --output batches/cards_batch_012.json
   python3 scripts/validate_batch.py batches/cards_batch_012.json
   ```
