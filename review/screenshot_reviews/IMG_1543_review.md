# IMG_1543.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1543_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=475
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `= ‘Cubchoo 70 ¢` | **Cubchoo** (82), Cubone (50), Cascoon (47) | stage=Basic; type=Water; rarity=one_diamond; set=B3 |  | |
| r1c2 | `Sobbte INET 60` | Sobble (50), Nasty Notice (46), Brigette (45) | — |  | |
| r1c3 | `soe Magnemite w60 4` | Magnemite (64), Magneton (51), Magnezone ex (51) | — |  | |
| r2c1 | `= Voltorb 50 +` | **Voltorb** (82), Moltres ex (50), Victor (50) | stage=Basic; type=Lightning; rarity=one_diamond; set=B3 |  | |
| r2c2 | `' Electrode 90 4` | Electrode (78), Electrike (60), Electivire (58) | — |  | |
| r2c3 | `“<< Morpeko w7Q 4` | Morpeko (70), Murkrow (50), Meowth ex (45) | — |  | |
| r3c1 | `*(no OCR text)*` | — | — |  | |
| r3c2 | `*(no OCR text)*` | — | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Top candidate: Cubchoo (82). Confirm visually.
- **r1c2** — Low confidence (50) (top: Sobble). Identify from contact sheet.
- **r1c3** — Low confidence (64) (top: Magnemite). Identify from contact sheet.
- **r2c1** — Top candidate: Voltorb (82). Confirm visually.
- **r2c2** — Top candidate: Electrode (78). Confirm visually.
- **r2c3** — Top candidate: Morpeko (70). Confirm visually.
- **r3c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1543_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1543_confirmed_TEMPLATE.csv review/confirmed/IMG_1543_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1543_confirmed.csv \
     --screenshot IMG_1543.PNG \
     --output batches/cards_batch_018.json
   python3 scripts/validate_batch.py batches/cards_batch_018.json
   ```
