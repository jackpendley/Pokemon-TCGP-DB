# IMG_1531.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1531_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** override top_y=514
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `ecFurfrou o w70` | Furfrou (63), Castform Snowy Form (47), Murkrow (45) | — |  | |
| r1c2 | `Clemont’s Backpack` | **Clemont's Backpack** (100), Blacephalon ex (56), Clemont (56) | category=Item; rarity=two_diamond; set=B1a | *Clemont's Backpack* ✓ | |
| r1c3 | `Quick-Grow Extract` | **Quick-Grow Extract** (100), Leaf Extract (53), Quick Ball (50) | category=Item; rarity=two_diamond; set=B1a | *Quick-Grow Extract* ✓ | |
| r2c1 | `Clemont` | **Clemont** (100), Calem (66), Cramorant (62) | category=Supporter; rarity=two_diamond; set=B1a | *Clemont* ✓ | |
| r2c2 | `Serena` | **Serena** (100), Seadra (66), Cheren (66) | category=Supporter; rarity=two_diamond; set=B1a | *Serena* ✓ | |
| r2c3 | `0 a a` | Abra (44), Lana (44), Hala (44) | — |  | |
| r3c1 | `SS :` | Nessa (57), Surskit (44), Shellos (44) | — |  | |
| r3c2 | `-~=«! Doublade ee 90` | Doublade (72), Mega Blaziken ex (46), Blastoise ex (46) | — |  | |
| r3c3 | `ST` | Misty (57), Scott (57), Staryu (50) | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (63) (top: Furfrou). Identify from contact sheet.
- **r1c2** — `Clemont's Backpack` prefilled (autofill (score 100)). Confirm name and quantity.
- **r1c3** — `Quick-Grow Extract` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c1** — `Clemont` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c2** — `Serena` prefilled (autofill (score 100)). Confirm name and quantity.
- **r2c3** — Low confidence (44) (top: Abra). Identify from contact sheet.
- **r3c1** — Low confidence (57) (top: Nessa). Identify from contact sheet.
- **r3c2** — Top candidate: Doublade (72). Confirm visually.
- **r3c3** — Low confidence (57) (top: Misty). Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1531_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1531_confirmed_TEMPLATE.csv review/confirmed/IMG_1531_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1531_confirmed.csv \
     --screenshot IMG_1531.PNG \
     --output batches/cards_batch_008.json
   python3 scripts/validate_batch.py batches/cards_batch_008.json
   ```
