# IMG_1534.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1534_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=486
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `race F Bronzong 120 @` | Bronzong (59), Bronzor (53), Brionne (46) | — |  | |
| r1c2 | `-—~' Bisharp sw 90` | Bisharp (70), Exp. Share (45), Bibarel ex (43) | — |  | |
| r1c3 | `Magearna 90` | **Magearna** (84), Magmar (58), Magneton (52) | stage=Basic; type=Metal; rarity=two_diamond; set=B3 |  | |
| r2c1 | `2 Wibray 90` | Vibrava (44), Braviary (42), Luxray ex (40) | — |  | |
| r2c2 | `Sint ral` | Net Ball (62), Bramblin (62), Ralts (61) | — |  | |
| r2c3 | `oc Herdier 90` | Herdier (70), Rocky Helmet (48), Shellder (47) | — |  | |
| r3c1 | `Audino w80` | Audino (75), Mega Audino ex (58), Deino (53) | — |  | |
| r3c2 | `“=! Corvisquire 80 *)` | **Corvisquire** (88), Squirtle (54), Corviknight ex (50) | stage=Stage 1; type=Colorless; rarity=two_diamond; set=B1 |  | |
| r3c3 | `Korrina` | **Korrina** (100), Koraidon (66), Chikorita (62) | category=Supporter; rarity=two_diamond; set=B3 | *Korrina* ✓ | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (59) (top: Bronzong). Identify from contact sheet.
- **r1c2** — Top candidate: Bisharp (70). Confirm visually.
- **r1c3** — Top candidate: Magearna (84). Confirm visually.
- **r2c1** — Low confidence (44) (top: Vibrava). Identify from contact sheet.
- **r2c2** — Low confidence (62) (top: Net Ball). Identify from contact sheet.
- **r2c3** — Top candidate: Herdier (70). Confirm visually.
- **r3c1** — Top candidate: Audino (75). Confirm visually.
- **r3c2** — Top candidate: Corvisquire (88). Confirm visually.
- **r3c3** — `Korrina` prefilled (autofill (score 100)). Confirm name and quantity.

---

## Instructions

1. Open `review/contact_sheets/IMG_1534_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1534_confirmed_TEMPLATE.csv review/confirmed/IMG_1534_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1534_confirmed.csv \
     --screenshot IMG_1534.PNG \
     --output batches/cards_batch_011.json
   python3 scripts/validate_batch.py batches/cards_batch_011.json
   ```
