# Manual Confirmation Instructions

## Goal

Confirm the identity of each card in one screenshot at a time.
The output is a per-screenshot confirmed CSV that gets converted into a batch JSON file.

---

## Inputs You Need (per screenshot)

1. **Contact sheet** — `review/contact_sheets/IMG_XXXX_contact.png`
   Open this image to visually inspect each of the 9 card crops.

2. **OCR/match suggestions** — `review/extraction_candidates.csv`
   Filter to the screenshot's rows for OCR text and fuzzy match candidates.
   Use these as hints, not truth.

3. **Review aid** — `review/screenshot_reviews/IMG_XXXX_review.md`
   A compact per-screenshot table with OCR text and top match candidates
   pre-filled. Exists for selected screenshots.

---

## Per-Screenshot Workflow

### Step 1 — Copy the template

Copy the per-screenshot template (if it exists) or the blank template:

```
cp review/confirmed/IMG_1525_confirmed_TEMPLATE.csv review/confirmed/IMG_1525_confirmed.csv
```

or from blank:

```
cp review/manual_confirmation_template.csv review/confirmed/IMG_1526_confirmed.csv
```

Edit the `IMG_XXXX.PNG` screenshot name in the file to match the actual screenshot.

### Step 2 — Fill in the CSV

For each row, open the contact sheet and fill in:

| Column | What to enter |
|---|---|
| `screenshot` | exact filename, e.g. `IMG_1525.PNG` |
| `row` | 1, 2, or 3 |
| `column` | 1, 2, or 3 |
| `card_name` | exact card name as it appears in the Pokémon TCG Pocket app |
| `quantity` | exact number shown in the quantity chip (bottom-left of each card) |
| `special_type` | see Special Type Reference below |
| `is_ex` | `true` or `false` — only `true` if "ex" is clearly on the card |
| `notes` | any uncertainty, observations, or why you set needs_review |

### Step 3 — Convert to batch JSON

```bash
python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1525_confirmed.csv \
  --screenshot IMG_1525.PNG \
  --output batches/cards_batch_002.json
```

Use `--allow-fewer` if the screenshot has fewer than 9 fully visible cards
(e.g., the last screenshot in the collection).

### Step 4 — Validate

```bash
python3 scripts/validate_batch.py batches/cards_batch_002.json
```

Fix any validation errors before proceeding to the next screenshot.

---

## Special Type Reference

Use exactly one of these values:

| Value | When to use |
|---|---|
| `normal` | Standard card — no special art, no foil border |
| `full_art` | Full-bleed artwork, no white card border |
| `illustration_rare` | Illustrated scene extending behind card elements; sparkle effects |
| `special_art` | Elaborate artwork with sparkle/foil, distinct from illustration_rare |
| `immersive` | Full-screen immersive card (rare, extends to screen edge) |
| `crown_gold` | Gold/crown border treatment |
| `shiny` | Shiny variant of a Pokémon |
| `rainbow` | Rainbow foil treatment |
| `promo` | Promo card (often from events or special series) |
| `special_trainer` | Trainer card with special art / rainbow foil border |
| `alternate_art` | Alternate artwork of an otherwise normal card |
| `unknown` | Cannot determine from the crop — use this when unsure |

If you use `unknown`, the batch script will automatically set `needs_review=true`.

---

## Rules

- **Do not guess card names.** If you cannot read the name clearly, enter `unknown` in `card_name`.
- **Exact app quantity.** Read the number from the quantity chip. If the chip is not visible, enter `0` and add a note.
- **Accuracy over speed.** A `needs_review=true` entry is correct behavior, not a failure.
- **One CSV per screenshot.** Name it `IMG_XXXX_confirmed.csv`.
- **Do not put commas in the notes field** unless the field is quoted.
- **Every fully visible card gets an entry.** If a card is partially clipped, skip it only if the quantity chip is not visible.
- **The goal is exact app-style card tracking.** Two cards with the same Pokémon name but different art/border are separate entries.

---

## Saving confirmed CSVs

Save to: `review/confirmed/IMG_XXXX_confirmed.csv`

These files are tracked in git so the confirmation record is preserved.

---

## Batch Numbering

Batch numbers follow screenshot order:

| Screenshot | Batch file |
|---|---|
| IMG_1524.PNG | batches/cards_batch_001.json (already complete) |
| IMG_1525.PNG | batches/cards_batch_002.json |
| IMG_1526.PNG | batches/cards_batch_003.json |
| IMG_1527.PNG | batches/cards_batch_004.json |
| … | … |
| IMG_1547.PNG | batches/cards_batch_024.json |
