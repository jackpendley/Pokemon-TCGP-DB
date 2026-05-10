# IMG_1532.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1532_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=519
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `P` | Hop (50), Opal (40), Hapu (40) | — |  | |
| r1c2 | `“==\Leavanny 140` | **Leavanny** (80), Penny (47), Heavy Ball (45) | stage=Stage 2; type=Grass; rarity=two_diamond; set=B3 |  | |
| r1c3 | `a iH` | Raichu (60), Raihan (60), Tabitha (54) | — |  | |
| r2c1 | `SS a` | Claw Fossil (53), Armor Fossil (50), Nosepass (50) | — |  | |
| r2c2 | `==" Poliwhirl Ln »90@` | Poliwhirl (75), Power Plant (53), Poliwrath (50) | — |  | |
| r2c3 | `“=< paldean TaurOSi w 100 @)` | **Paldean Tauros** (80), Tauros ex (53), Alolan Marowak (51) | stage=Basic; type=Fighting; rarity=two_diamond; set=B2a |  | |
| r3c1 | `Quagsire 7 w130` | Quagsire (69), Squirtle (43), Sandshrew (41) | — |  | |
| r3c2 | `a neal 100` | Heal Ball (52), Cacnea (50), Tangela (47) | — |  | |
| r3c3 | `=~’ Gorebyss ww 100@` | Gorebyss (69), Colress (45), Gourgeist (41) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (50) (top: Hop). Identify from contact sheet.
- **r1c2** — Top candidate: Leavanny (80). Confirm visually.
- **r1c3** — Low confidence (60) (top: Raichu). Identify from contact sheet.
- **r2c1** — Low confidence (53) (top: Claw Fossil). Identify from contact sheet.
- **r2c2** — Top candidate: Poliwhirl (75). Confirm visually.
- **r2c3** — Top candidate: Paldean Tauros (80). Confirm visually.
- **r3c1** — Low confidence (69) (top: Quagsire). Identify from contact sheet.
- **r3c2** — Low confidence (52) (top: Heal Ball). Identify from contact sheet.
- **r3c3** — Low confidence (69) (top: Gorebyss). Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1532_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1532_confirmed_TEMPLATE.csv review/confirmed/IMG_1532_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1532_confirmed.csv \
     --screenshot IMG_1532.PNG \
     --output batches/cards_batch_009.json
   python3 scripts/validate_batch.py batches/cards_batch_009.json
   ```
