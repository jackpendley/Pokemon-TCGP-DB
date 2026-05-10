# IMG_1533.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1533_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=463
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `o~«'Magneton 904` | Magneton (72), Magnezone ex (61), Magnezone (60) | — |  | |
| r1c2 | `a Pe wll 4` | Aero Ball (52), Petilil (47), Quaxwell (44) | — |  | |
| r1c3 | `*(no OCR text)*` | — | — |  | |
| r2c1 | `*(no OCR text)*` | — | — |  | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `el . .` | Seel (66), Numel (57), Elesa (57) | — |  | |
| r3c1 | `whine G` | Phione (61), Growlithe (50), Shinx (50) | — |  | |
| r3c2 | `. Mandibuzz  100*)` | **Mandibuzz** (81), Meganium (47), Electabuzz (43) | stage=Stage 1; type=Darkness; rarity=two_diamond; set=B3 |  | |
| r3c3 | `Ee EEE` | Eevee (72), Eevee ex (71), Indeedee ex (58) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Top candidate: Magneton (72). Confirm visually.
- **r1c2** — Low confidence (52) (top: Aero Ball). Identify from contact sheet.
- **r1c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — Low confidence (66) (top: Seel). Identify from contact sheet.
- **r3c1** — Low confidence (61) (top: Phione). Identify from contact sheet.
- **r3c2** — Top candidate: Mandibuzz (81). Confirm visually.
- **r3c3** — Top candidate: Eevee (72). Confirm visually.

---

## Instructions

1. Open `review/contact_sheets/IMG_1533_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1533_confirmed_TEMPLATE.csv review/confirmed/IMG_1533_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1533_confirmed.csv \
     --screenshot IMG_1533.PNG \
     --output batches/cards_batch_010.json
   python3 scripts/validate_batch.py batches/cards_batch_010.json
   ```
