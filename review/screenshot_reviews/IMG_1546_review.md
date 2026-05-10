# IMG_1546.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1546_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=494
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `*(no OCR text)*` | — | — |  | |
| r1c2 | `ae Minccino 50` | Minccino (72), Cinccino (63), Incineroar ex (59) | — |  | |
| r1c3 | `Sint —— <——_ |` | Sina (75), Shinx (66), Flint (66) | — |  | |
| r2c1 | `Potion` | **Potion** (100), Max Potion (75), Super Potion (66) | — | *Potion* ✓ | |
| r2c2 | `X Speed` | **X Speed** (100), X Special (62), Espeon ex (62) | — | *X Speed* ✓ | |
| r2c3 | `Hand Scope |` | Choice Band (66), Muscle Band (66), Houndstone (60) | — |  | |
| r3c1 | `Pokédex` | Dexio (66), Zapdos ex (62), Palkia ex (62) | — |  | |
| r3c2 | `Poke Ball` | **Poké Ball** (94), Love Ball (77), Net Ball (70) | — |  | |
| r3c3 | `iter TRAINER |` | Terrakion (66), Training Area (56), Training Court (53) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r1c2** — Top candidate: Minccino (72). Confirm visually.
- **r1c3** — Top candidate: Sina (75). Confirm visually.
- **r2c1** — `Potion` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c2** — `X Speed` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c3** — Low confidence (66) (top: Choice Band). Identify from contact sheet.
- **r3c1** — Low confidence (66) (top: Dexio). Identify from contact sheet.
- **r3c2** — Top candidate: Poké Ball (94). Confirm visually.
- **r3c3** — Low confidence (66) (top: Terrakion). Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1546_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1546_confirmed_TEMPLATE.csv review/confirmed/IMG_1546_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1546_confirmed.csv \
     --screenshot IMG_1546.PNG \
     --output batches/cards_batch_021.json
   python3 scripts/validate_batch.py batches/cards_batch_021.json
   ```
