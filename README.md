# Pokemon TCG Pocket Collection Database

Builds and maintains an exact Pokémon TCG Pocket card collection database from app screenshots.

## Collection Target

Expected total: **331 cards**

Canonical database file: `cards.json`

## Workflow

```
setup → screenshots_manifest → one screenshot per batch → audit → merge → validate → review crops → final audit → deck advice
```

1. **Setup** — initialize project structure (this phase)
2. **Manifest** — document all screenshots in `screenshots_manifest.md`
3. **Extract** — process one screenshot at a time into `batches/cards_batch_XXX.json`
4. **Audit** — review ambiguous cards in `ambiguous_cards.md`, provide crops if needed
5. **Merge** — run `scripts/merge_batches.py` to consolidate batches into `cards.json`
6. **Validate** — run validation script to confirm total and data integrity
7. **Review crops** — resolve any remaining ambiguous cards
8. **Final audit** — confirm all 331 cards are accounted for
9. **Deck advice** — generate recommendations from `cards.json`

## Scripts

### Validate the database

```bash
python scripts/validate_cards.py --expected-total 331
```

Checks data integrity, field validity, uniqueness, and that total quantity equals 331. Exits non-zero on failure.

### Export to CSV

```bash
python scripts/export_cards_csv.py
```

Exports `cards.json` to `cards.csv`. Do not manually edit `cards.csv`.

### Merge batches (when instructed)

```bash
python scripts/merge_batches.py
```

Merges all `batches/cards_batch_*.json` files into `cards.json`. Only run when explicitly instructed.

## Card Schema

See `cards.schema.json` for the full card object definition.

Key fields: `id`, `card_name`, `quantity`, `special_type`, `card_category`, `confidence`, `needs_review`

## Ambiguous Cards

Cards that could not be identified with high confidence are logged in `ambiguous_cards.md` with instructions for what crop or screenshot to provide for confirmation.

## Screenshots and Image Files

`screenshots/` is intentionally excluded from git (see `.gitignore`). Image files are never committed.

- `screenshots/` contains 24 PNG source screenshots (IMG_1524.PNG – IMG_1547.PNG), all 1179×2556 px.
- `Archive.zip` was removed — it was a byte-for-byte redundant copy, verified by sha256 before deletion.
- `screenshots/__MACOSX/` was removed — it contained only macOS AppleDouble metadata, not image data.

Screenshot inventory is tracked through:
- `screenshots_manifest.md` — human-readable manifest with dimensions, hashes, and cleanup status
- `screenshots_inventory.json` — machine-readable full inventory

Card extraction processes one screenshot at a time, saving results to `batches/cards_batch_XXX.json`.

### Re-generate the screenshot inventory

```bash
python3 scripts/inventory_screenshots.py
```

## Crop Calibration and QA

Before running OCR or creating batch files, verify that all 216 card crops
are correctly aligned.  Follow these steps:

### A. Crop all screenshots

```bash
python3 scripts/crop_all_screenshots.py --force
```

Reads calibration from `config/crop_config.json` (global defaults plus optional
per-screenshot overrides).  Outputs `crops/IMG_XXXX/r1c1.png … r3c3.png` and
`data/extraction/crop_manifest.json` (records which calibration was used per screenshot).

### B. Evaluate crop quality

```bash
python3 scripts/evaluate_crop_quality.py
```

Runs pixel-level heuristics on every crop and flags misaligned or clipped crops.
Outputs:
- `data/extraction/crop_quality_report.json`
- `review/crop_quality_report.md` — lists screenshots needing override review

### C. Inspect contact sheets

```bash
python3 scripts/create_contact_sheets.py
```

Outputs `review/contact_sheets/<stem>_contact.png`.  Each thumbnail is labeled
with its row/column, actual dimensions, and QA status badge (PASS / WARN / FAIL)
when the quality report is present.

### D. Fix misaligned screenshots

If a screenshot has bad crops, add a per-screenshot override in
`config/crop_config.json` under `per_screenshot_overrides`:

```json
"IMG_1525.PNG": { "top_y": 548 }
```

Then re-run steps A–C for the affected screenshots.  See
`crop_override_workflow.md` for the full procedure.

### E. Proceed to OCR only after crop QA is acceptable

Do not run OCR or create batch files until the contact sheets look correct
(complete cards, no clipping, quantity chips visible in all row 3 crops).

---

## Automated Extraction Pipeline

The pipeline replaces manual Claude-vision extraction with a reproducible
Python workflow.  Human review is still required for low-confidence cards,
but all mechanical work is automated.

### A. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

Also install Tesseract for OCR (macOS):

```bash
brew install tesseract
```

### B. Build card reference

Downloads and caches a PTCGP card-name index for fuzzy matching.

```bash
python3 scripts/build_card_reference.py
```

Outputs:
- `data/reference/card_reference.json`
- `data/reference/card_names.txt`

If the download fails, use the bundled seed file:

```bash
python3 scripts/build_card_reference.py --seed data/reference/manual_card_names_seed.txt
```

Or supply a local JSON file: `--local path/to/cards.json`.

### C. Crop screenshots

Batch-crops all 24 screenshots into 3×3 card grids.

```bash
python3 scripts/crop_all_screenshots.py
```

Outputs: `crops/IMG_XXXX/r1c1.png … r3c3.png` and
`data/extraction/crop_manifest.json`.  Use `--force` to re-crop.

### D. Create contact sheets

Builds labeled overview images for visual inspection.

```bash
python3 scripts/create_contact_sheets.py
```

Outputs: `review/contact_sheets/<stem>_contact.png` (gitignored).

### E. OCR crops

Extracts card name text from the top band of each crop.

```bash
python3 scripts/ocr_card_crops.py
```

Output: `data/extraction/ocr_results.json`.  Runs gracefully and
reports clearly if `tesseract` is missing.

### F. Match OCR to reference

Fuzzy-matches OCR text to the card name list.

```bash
python3 scripts/match_ocr_to_reference.py
```

Output: `data/extraction/match_candidates.json`.

### G. Generate review report

Produces human-readable files listing every crop that needs manual
confirmation.

```bash
python3 scripts/generate_review_report.py
```

Outputs:
- `review/review_needed.md` — grouped by screenshot with top match candidates
- `review/extraction_candidates.csv` — flat table for spreadsheet review

### H. Create batch files

Use the Manual Confirmation Workflow below to confirm card names one
screenshot at a time and generate batch files automatically.

---

## Manual Confirmation Workflow

Process one screenshot at a time. Do not skip ahead.

### Step 1 — Review the contact sheet and OCR suggestions

Open the contact sheet for the screenshot:

```
review/contact_sheets/IMG_1525_contact.png
```

Open the per-screenshot review aid (if it exists):

```
review/screenshot_reviews/IMG_1525_review.md
```

This file contains OCR text and fuzzy match candidates for each crop position.

### Step 2 — Fill in the confirmed CSV

Copy the pre-filled template (if it exists) or the blank template:

```bash
cp review/confirmed/IMG_1525_confirmed_TEMPLATE.csv review/confirmed/IMG_1525_confirmed.csv
# or from blank:
cp review/manual_confirmation_template.csv review/confirmed/IMG_1526_confirmed.csv
```

Fill in `card_name` and `quantity` for every row.
Set `special_type` if clearly identifiable; otherwise use `unknown`.
Add `notes` for anything uncertain.

See `review/manual_confirmation_instructions.md` for the full field reference.

### Step 3 — Convert to batch JSON

```bash
python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1525_confirmed.csv \
  --screenshot IMG_1525.PNG \
  --output batches/cards_batch_002.json
```

Use `--allow-fewer` for the final screenshot if it has fewer than 9 fully
visible cards.

### Step 4 — Validate the batch

```bash
python3 scripts/validate_batch.py batches/cards_batch_002.json
```

Fix any validation errors before proceeding to the next screenshot.

### Batch Numbering

| Screenshot | Batch file |
|---|---|
| IMG_1524.PNG | `batches/cards_batch_001.json` (already complete) |
| IMG_1525.PNG | `batches/cards_batch_002.json` |
| IMG_1526.PNG | `batches/cards_batch_003.json` |
| … | … |
| IMG_1547.PNG | `batches/cards_batch_024.json` |

---

## Automation Improvement / Active Learning

As confirmed batches accumulate, use them to improve automation for the
remaining screenshots. This loop tightens the review burden over time.

### A. Build confirmed lexicon

```bash
python3 scripts/build_confirmed_lexicon.py
```

Reads all `batches/cards_batch_*.json` and produces:
- `data/reference/confirmed_lexicon.json` — full card record with counts
- `data/reference/confirmed_card_names.txt` — plain name list for matching

The confirmed lexicon acts as a known-good mini reference.
Re-run this after each new batch is created.

### B. Evaluate detection accuracy

```bash
python3 scripts/evaluate_detection_against_confirmed.py
```

Compares OCR/fuzzy-match suggestions against confirmed ground truth.
Outputs:
- `data/extraction/detection_validation_report.json`
- `detection_validation_report.md` — top-1/top-3 accuracy, threshold analysis

Re-run after adding new confirmed batches to track accuracy trends.

### C. Rerun matching with lexicon boost

```bash
python3 scripts/match_ocr_to_reference.py
```

If `data/reference/confirmed_card_names.txt` exists, confirmed card names
act as tie-breakers within a 5-point score window. The output now includes
a `match_source` field: `full_reference`, `confirmed_lexicon`, or `both`.

### D. Generate autofill candidates

```bash
python3 scripts/generate_autofill_candidates.py
```

Outputs:
- `review/autofill_candidates.csv` — all unconfirmed crops with autofill decision
- `review/autofill_candidates.md` — human-readable summary

**Autofill rules (conservative):**
- `auto_fill=true` only if score ≥ 95
- `auto_fill=true` if score ≥ 90 AND OCR source contains the suggested name exactly
- `auto_fill=false` otherwise

Autofill candidates are suggestions only — they must still be verified by
the user before being written to confirmed CSV files. **Never auto-write
to `cards.json` without validation.**

### When to re-run this loop

After each new group of confirmed batches, re-run steps A → D to:
1. Expand the lexicon
2. Measure whether accuracy improved
3. Re-score unconfirmed crops with the updated reference
4. Update the autofill candidate list
