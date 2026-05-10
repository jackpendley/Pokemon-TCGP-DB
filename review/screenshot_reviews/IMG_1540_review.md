# IMG_1540.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1540_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=463
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `Starly w6O` | Starly (75), Staryu (62), Staraptor (52) | — |  | |
| r1c2 | `eave! Staravia 80 *` | Staravia (66), Altaria (52), Larvesta (50) | — |  | |
| r1c3 | `~-<« Buneary wOO >)` | Buneary (77), Bunnelby (52), Budew (50) | — |  | |
| r2c1 | `e<< Roselia w60 @` | Roselia (70), Steelix ex (52), Greninja ex (50) | — |  | |
| r2c2 | `*(no OCR text)*` | — | — |  | |
| r2c3 | `*(no OCR text)*` | — | — |  | |
| r3c1 | `Pel SOP Py =` | PokéStop (55), Lucky Ice Pop (52), Escape Rope (47) | — |  | |
| r3c2 | `*(no OCR text)*` | — | — |  | |
| r3c3 | `Mawile w80` | Mawile (75), Mega Mawile ex (58), Maxie (53) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Top candidate: Starly (75). Confirm visually.
- **r1c2** — Low confidence (66) (top: Staravia). Identify from contact sheet.
- **r1c3** — Top candidate: Buneary (77). Confirm visually.
- **r2c1** — Top candidate: Roselia (70). Confirm visually.
- **r2c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r2c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c1** — Low confidence (55) (top: PokéStop). Identify from contact sheet.
- **r3c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c3** — Top candidate: Mawile (75). Confirm visually.

---

## Instructions

1. Open `review/contact_sheets/IMG_1540_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1540_confirmed_TEMPLATE.csv review/confirmed/IMG_1540_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1540_confirmed.csv \
     --screenshot IMG_1540.PNG \
     --output batches/cards_batch_015.json
   python3 scripts/validate_batch.py batches/cards_batch_015.json
   ```
