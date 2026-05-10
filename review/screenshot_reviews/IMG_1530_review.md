# IMG_1530.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1530_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=446
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `le` | Leaf (66), Golem (57), Gible (57) | — |  | |
| r1c2 | `120` | Porygon2 (18), Quick-Grow Extract (0), Blaziken (0) | — |  | |
| r1c3 | `nF` | N (66), Mienfoo (44), Nuzleaf (44) | — |  | |
| r2c1 | `Steelix w150` | Steelix (73), Steelix ex (63), Mega Steelix ex (51) | — |  | |
| r2c2 | `ar 'Probopass 130` | Probopass (72), Aromatisse (46), Lapras (45) | — |  | |
| r2c3 | `ie... a` | Maxie (66), Ice Heal (66), Dive Ball (61) | — |  | |
| r3c1 | `soe Porygon2 90` | Porygon2 (69), Porygon-Z (66), Porygon-Z ex (66) | — |  | |
| r3c2 | `SSS *=` | Solosis (60), Nosepass (54), Sandslash (50) | — |  | |
| r3c3 | `Bouffalant 100` | **Bouffalant** (83), Rufflet (47), Salandit (45) | stage=Basic; type=Colorless; rarity=two_diamond; set=B1a |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (66) (top: Leaf). Identify from contact sheet.
- **r1c2** — Low confidence (18) (top: Porygon2). Identify from contact sheet.
- **r1c3** — Low confidence (66) (top: N). Identify from contact sheet.
- **r2c1** — Top candidate: Steelix (73). Confirm visually.
- **r2c2** — Top candidate: Probopass (72). Confirm visually.
- **r2c3** — Low confidence (66) (top: Maxie). Identify from contact sheet.
- **r3c1** — Low confidence (69) (top: Porygon2). Identify from contact sheet.
- **r3c2** — Low confidence (60) (top: Solosis). Identify from contact sheet.
- **r3c3** — Top candidate: Bouffalant (83). Confirm visually.

---

## Instructions

1. Open `review/contact_sheets/IMG_1530_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1530_confirmed_TEMPLATE.csv review/confirmed/IMG_1530_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1530_confirmed.csv \
     --screenshot IMG_1530.PNG \
     --output batches/cards_batch_007.json
   python3 scripts/validate_batch.py batches/cards_batch_007.json
   ```
