# IMG_1547.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1547_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** default
**QA:** QA not available

---

## Crop-by-Crop Review Table

Fill in **Your Confirmed Name** and **Quantity** after inspecting the contact sheet.
Quantity must be read from the app — it is never prefilled automatically.

| Pos | OCR Text | Top 3 Candidates | Ref Hints | **Confirmed Name** | **Qty** |
|---|---|---|---|---|---|
| r1c1 | `ftem TRAINGR` | Training Area (64), Feraligatr (63), Training Court (61) | — |  | |
| r1c2 | `Item | TRAINER |` | Terrakion (57), Training Area (56), Training Court (53) | — |  | |
| r1c3 | `item TRAINGF |` | Training Area (64), Training Court (61), Terrakion (57) | — |  | |
| r2c1 | `Supporter TRAINER` | Training Court (58), Torterra (56), Terrakion (53) | — |  | |
| r2c2 | `o Victini wel` | Victini (70), Victreebel (52), Corviknight ex (51) | — |  | |
| r2c3 | `= <P “seo os Qe ee` | Espeon ex (52), Espeon (50), Escape Rope (48) | — |  | |
| r3c1 | `*(no OCR text)*` | — | — |  | |
| r3c2 | `*(no OCR text)*` | — | — |  | |
| r3c3 | `*(no OCR text)*` | — | — |  | |

**Legend:** Score ≥ 80 shown in **bold**. ✓ = auto-prefilled in template (verify before use).

---

## Notes

- **r1c1** — Low confidence (64) (top: Training Area). Identify from contact sheet.
- **r1c2** — Low confidence (57) (top: Terrakion). Identify from contact sheet.
- **r1c3** — Low confidence (64) (top: Training Area). Identify from contact sheet.
- **r2c1** — Low confidence (58) (top: Training Court). Identify from contact sheet.
- **r2c2** — Top candidate: Victini (70). Confirm visually.
- **r2c3** — Low confidence (52) (top: Espeon ex). Identify from contact sheet.
- **r3c1** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c2** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.
- **r3c3** — No OCR text / no candidates. Full-art or special card? Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1547_contact.png`.
2. For each position, confirm the card name and the number shown in the quantity chip (bottom-left corner).
3. Copy the template to a confirmed file:
   ```bash
   cp review/confirmed/IMG_1547_confirmed_TEMPLATE.csv review/confirmed/IMG_1547_confirmed.csv
   ```
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if clearly identifiable; otherwise leave as `unknown`.
6. Set `is_ex` to true/false if known; otherwise leave blank (script will infer from name).
7. Add notes for anything uncertain.
8. Convert to batch and validate:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1547_confirmed.csv \
     --screenshot IMG_1547.PNG \
     --output batches/cards_batch_021.json
   python3 scripts/validate_batch.py batches/cards_batch_021.json
   ```
