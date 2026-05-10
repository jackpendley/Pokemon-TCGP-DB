# IMG_1538.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1538_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=489
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `in SEO` | Pineco (66), Finneon (61), Iono (60) | — |  | |
| r1c2 | `—— Houndoom 090` | **Houndoom** (80), Houndoom ex (78), Houndour (60) | stage=Stage 1; type=Fire; rarity=one_diamond; set=B1a |  | |
| r1c3 | `acre || |` | Cacturne (66), Arven (66), Mareep (60) | — |  | |
| r2c1 | `=< Clauncher 60)` | **Clauncher** (85), Haunter (52), Candice (52) | stage=Basic; type=Water; rarity=one_diamond; set=B1a |  | |
| r2c2 | `nant: Magnemite #50 47` | Magnemite (62), Maintenance (51), Magneton (50) | — |  | |
| r2c3 | `--« Helioptile 60 :` | **Helioptile** (87), Sceptile ex (58), Sceptile (57) | stage=Basic; type=Lightning; rarity=one_diamond; set=B1a |  | |
| r3c1 | `Sy a` | Gastly (60), May (57), Chansey (54) | — |  | |
| r3c2 | `— Seless dow` | Drowzee (58), Colress (58), Dwebble (58) | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (66) (top: Pineco). Identify from contact sheet.
- **r1c2** — Top candidate: Houndoom (80). Confirm visually.
- **r1c3** — Low confidence (66) (top: Cacturne). Identify from contact sheet.
- **r2c1** — Top candidate: Clauncher (85). Confirm visually.
- **r2c2** — Low confidence (62) (top: Magnemite). Identify from contact sheet.
- **r2c3** — Top candidate: Helioptile (87). Confirm visually.
- **r3c1** — Low confidence (60) (top: Gastly). Identify from contact sheet.
- **r3c2** — Low confidence (58) (top: Drowzee). Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1538_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1538_confirmed_TEMPLATE.csv review/confirmed/IMG_1538_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1538_confirmed.csv \
     --screenshot IMG_1538.PNG \
     --output batches/cards_batch_015.json
   python3 scripts/validate_batch.py batches/cards_batch_015.json
   ```
