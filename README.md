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

If the download fails, run with `--local path/to/cards.json` to supply a
local file instead.

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

Open `review/review_needed.md` and confirm card names for all flagged
crops.  Then manually create `batches/cards_batch_XXX.json` files using the
confirmed names, following the canonical schema in `CLAUDE.md`.
