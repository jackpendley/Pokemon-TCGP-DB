# IMG_1525.PNG — Card Review Aid

**Contact sheet:** `review/contact_sheets/IMG_1525_contact.png`
Open this image to visually inspect each crop before confirming names.

**Calibration:** default (top_y=546)
**QA:** 9/9 PASS

---

## Crop-by-Crop Review Table

Fill in the last two columns after inspecting the contact sheet.

| Position | Crop ID | OCR Text | Top 3 Fuzzy Matches (score) | Suggested | **Your Confirmed Name** | **Quantity** |
|---|---|---|---|---|---|---|
| r1c1 | IMG_1525_r1c1 | *(no OCR text)* | — | — | | |
| r1c2 | IMG_1525_r1c2 | `Bonsly 30` | Bunnelby (47), Bagon (43), Absol (43) | — | | |
| r1c3 | IMG_1525_r1c3 | `w Riolu - r` | **Riolu (83)**, Raikou (62), Prinplup (53) | **Riolu** ✓ | | |
| r2c1 | IMG_1525_r2c1 | *(garbled)* | Magmortar (50), Training Court (49), Rare Candy (48) | — | | |
| r2c2 | IMG_1525_r2c2 | *(no OCR text)* | — | — | | |
| r2c3 | IMG_1525_r2c3 | `SMarowakSe i140` | Marowak (64), Aromatisse (48), Ampharos ex (46) | — | | |
| r3c1 | IMG_1525_r3c1 | *(no OCR text)* | — | — | | |
| r3c2 | IMG_1525_r3c2 | *(garbled)* | Pansage (44), Blastoise ex (44), Aegislash ex (44) | — | | |
| r3c3 | IMG_1525_r3c3 | *(garbled)* | Pokémon League Headquarters (41), Hippopotas (39), Rescue Stretcher (38) | — | | |

**Legend:** Bold match = score ≥ 80 (auto-match threshold). ✓ = auto-matched.

---

## Notes

- **r1c3 (Riolu)** — Only auto-match for this screenshot. Confirm name and quantity from contact sheet.
- **r1c2** — OCR read "Bonsly" but fuzzy match didn't confirm it (score 47). Check contact sheet for Bonsly vs another card.
- **r2c3** — OCR contains "Marowak" but with noise; score 64. Likely Marowak — confirm visually.
- **r1c1, r2c2, r3c1** — No OCR text. These may be full-art, special art, or immersive cards whose name bands defeated OCR. Identify from contact sheet.
- **r3c2, r3c3** — Low-score matches with garbled OCR. Identify from contact sheet.

---

## Instructions

1. Open `review/contact_sheets/IMG_1525_contact.png`.
2. For each position, confirm the card name and quantity chip number.
3. Copy `review/confirmed/IMG_1525_confirmed_TEMPLATE.csv` to `review/confirmed/IMG_1525_confirmed.csv`.
4. Fill in `card_name` and `quantity` for every row.
5. Set `special_type` if you can clearly identify it; otherwise leave as `unknown`.
6. Add notes for anything uncertain.
7. Run:
   ```bash
   python3 scripts/create_batch_from_confirmation.py \
     --input review/confirmed/IMG_1525_confirmed.csv \
     --screenshot IMG_1525.PNG \
     --output batches/cards_batch_002.json
   python3 scripts/validate_batch.py batches/cards_batch_002.json
   ```
