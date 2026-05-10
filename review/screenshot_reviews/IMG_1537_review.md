# IMG_1537.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1537_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=520
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `A en ae | in|` | Awakening (63), Greninja ex (57), Arcanine (55) | — |  | |
| r1c2 | `=" Seedot ~50@` | **Seedot** (80), X Speed (50), Sentret (50) | stage=Basic; type=Grass; rarity=one_diamond; set=B1 |  | |
| r1c3 | `ys 0` | Gyarados ex (40), Yamask (40), Chi-Yu (40) | — |  | |
| r2c1 | `- Bulbasaur w60 a` | Bulbasaur (75), Venusaur ex (46), Malamar (45) | — |  | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `Sunkern 50` | **Sunkern** (82), Super Rod (52), Snover (50) | stage=Basic; type=Grass; rarity=one_diamond; set=B1a |  | |
| r3c1 | `<> | Burmy 60 @` | Burmy (76), Buneary (53), Luxray ex (47) | — |  | |
| r3c2 | `= _— — H` | Hop (50), Hau (50), Hapu (40) | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (63) (top: Awakening). Identify from contact sheet.
- **r1c2** — Top candidate: Seedot (80). Confirm visually.
- **r1c3** — Low confidence (40) (top: Gyarados ex). Identify from contact sheet.
- **r2c1** — Top candidate: Bulbasaur (75). Confirm visually.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — Top candidate: Sunkern (82). Confirm visually.
- **r3c1** — Top candidate: Burmy (76). Confirm visually.
- **r3c2** — Low confidence (50) (top: Hop). Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1537_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1537_confirmed_TEMPLATE.csv review/confirmed/IMG_1537_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1537_confirmed.csv \
     --screenshot IMG_1537.PNG \
     --output batches/cards_batch_012.json
   python3 scripts/validate_batch.py batches/cards_batch_012.json
   ```
