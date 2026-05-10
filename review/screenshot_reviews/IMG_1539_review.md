# IMG_1539.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1539_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** default
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `"Aromatics BES 100 @` | Aromatisse (66), Fomantis (48), Raticate (48) | — |  | |
| r1c2 | `os i` | Latios (60), Ariados (54), Spidops (54) | — |  | |
| r1c3 | `Makuhita 80` | **Makuhita** (84), Palkia ex (50), Machamp ex (47) | stage=Basic; type=Fighting; rarity=one_diamond; set=B1 |  | |
| r2c1 | `=< (Nosepass` | **Nosepass** (100), Nessa (61), Probopass (58) | stage=Basic; type=Fighting; rarity=one_diamond; set=B1a | *Nosepass* ✓ | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `=! Mienshao 90 BS` | Mienshao (72), Mienfoo (47), Bisharp (47) | — |  | |
| r3c1 | `Grimer 800` | Grimer (75), Alolan Grimer (60), Grimsley (55) | — |  | |
| r3c2 | `Ee 0` | Seel (50), Bede (50), Eevee (44) | — |  | |
| r3c3 | `Porygon 60 -` | **Porygon** (82), Porygon2 (77), Porygon-Z (73) | stage=Basic; type=Colorless; rarity=one_diamond; set=B1a |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (66) (top: Aromatisse). Identify from contact sheet.
- **r1c2** — Low confidence (60) (top: Latios). Identify from contact sheet.
- **r1c3** — Top candidate: Makuhita (84). Confirm visually.
- **r2c1** — `Nosepass` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — Top candidate: Mienshao (72). Confirm visually.
- **r3c1** — Top candidate: Grimer (75). Confirm visually.
- **r3c2** — Low confidence (50) (top: Seel). Identify from contact sheet.
- **r3c3** — Top candidate: Porygon (82). Confirm visually.

---

## Instructions

1. Open `review/contact_sheets/IMG_1539_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1539_confirmed_TEMPLATE.csv review/confirmed/IMG_1539_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1539_confirmed.csv \
     --screenshot IMG_1539.PNG \
     --output batches/cards_batch_015.json
   python3 scripts/validate_batch.py batches/cards_batch_015.json
   ```
