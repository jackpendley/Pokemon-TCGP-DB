# Pokemon TCG Pocket Collection Database

Builds and maintains an exact Pokémon TCG Pocket card collection database from app screenshots.

## Current Collection Baseline (Active)

`collection.json` is the **active current collection** as of 2026-05-11.

| File | Cards | Status |
|---|---|---|
| `collection.json` | **380 verified ✅** (224 unique entries) | **Active — use for all recommendations** |
| `deck-recommendations.jsx` | — | Deck recommendation prototype UI |
| `cards.json` | 329 (211 entries) | Historical screenshot-ingestion baseline |
| `screenshots/` | 26 files (IMG_1556–IMG_1581) | Cropped 3×3 grid screenshots, 232 card slots |

Pack-source coverage: **192/224 entries EV-ready** — 35 previously-ambiguous entries resolved; 32 remaining unresolved.

Validate and normalize:

```bash
python3 scripts/validate_current_collection.py --expected-total 380
python3 scripts/normalize_current_collection.py
python3 scripts/current_collection_pack_coverage.py
python3 scripts/create_current_pack_review.py   # generates fallback/debugging report only
python3 scripts/validate_deck_recommendations.py
```

Manual confirmation scripts exist as a fallback when automated confidence falls below threshold:

```bash
python3 scripts/apply_current_pack_confirmations.py --dry-run   # only after filling CSV manually
python3 scripts/apply_current_pack_confirmations.py --apply
```

Screenshot-to-collection alignment (order-only, no OCR): 224/224 entries aligned, 8 surplus slots, max confidence 0.70.

```bash
python3 scripts/build_screenshot_collection_alignment.py
python3 scripts/validate_screenshot_collection_alignment.py
```

Outputs: `data/current/screenshot_collection_alignment.json`, `data/exports/screenshot_collection_alignment.csv`, `review/screenshot_collection_alignment.md`

Pack-source confidence scoring: 108 auto-accept, 49 secondary evidence, 59 low-confidence, 8 unresolved. Avg score 0.82.

```bash
python3 scripts/score_pack_source_confidence.py
python3 scripts/score_pack_source_confidence.py --validate
```

Outputs: `data/current/pack_source_confidence_scores.json`, `data/exports/pack_source_confidence_scores.csv`, `review/pack_source_confidence_scores.md`

Pull probability model: 24 packs, model v0.5.0, source_status=**third_party_verified_with_in_app_anchor**. Bulbapedia offering rate pages confirm branch structure for 12 packs (bulbapedia_branch_verified); Pulsing Aura (B3) user_in_app_verified_plus_bulbapedia; 8 packs third_party_verified (two-branch, pattern-consistent); 3 packs pending_verification (A4/A4b). Secluded Springs (A4a): unique three-branch 91.620%/8.330%/0.050%. Mega Shine (B2b): four-branch (adds themed_rare_pack=0.005%). A-series packs confirmed two-branch; stale_model_warnings removed. `rarity_probabilities` (aggregate rates) still null. See `review/in_app_rate_verification.md`.

```bash
python3 scripts/build_pull_probability_model.py
python3 scripts/validate_pull_probability_model.py
```

Outputs: `data/reference/pull_probability_model.json`, `review/pull_probability_model.md`, `review/pack_ev_readiness.md`, `review/pull_probability_external_lookup.md`, `data/current/pack_ev_readiness.json`, `review/in_app_rate_verification.md`, `data/current/in_app_rate_verification.json`

Pull rate cross-check: rates independently confirmed by ONE Esports (full match) + CGMagazine + ShackNews. Cross-check report: `review/pull_rate_cross_check.md`.

EV status: **READY** — model confidence=third_party_verified_with_in_app_anchor. EV calculator supports two/three/four-branch models; P_combined=P_regular+P_plus_one; themed_rare and card 6 EV=0 (pools not in pack_sources.json).

Pack EV calculator: ranks all 24 packs by expected new-card value. Top pack: **Paldean Wonders** (total EV=4.94, adj=4.20 at third_party_verified_with_in_app_anchor confidence).

```bash
python3 scripts/build_pack_ev.py
python3 scripts/build_pack_ev.py --validate
```

Outputs: `data/current/pack_ev.json`, `data/exports/pack_ev.csv`, `review/pack_ev.md`

Inferred pack recommendation report: ranks all 24 packs across 5 metrics, provides chase-deck pack guide, 3 planning scenarios, blocker table. Top recommendation: **Paldean Wonders** (adj EV=4.20).

```bash
python3 scripts/generate_pack_recommendation_report.py
python3 scripts/generate_pack_recommendation_report.py --validate
```

Outputs: `review/inferred_pack_recommendations.md`, `data/current/inferred_pack_recommendations.json`, `data/exports/inferred_pack_recommendations.csv`

Hourglass spending plan: conservative/moderate/aggressive scenarios in 10-pack-batch format. No hourglass count assumed. Top pack across all scenarios: **Paldean Wonders**.

```bash
python3 scripts/generate_hourglass_spending_plan.py
python3 scripts/generate_hourglass_spending_plan.py --validate
```

Outputs: `review/final_hourglass_spending_plan.md`, `data/current/final_hourglass_spending_plan.json`, `data/exports/final_hourglass_spending_plan.csv`

See `review/final_hourglass_spending_plan.md` for the full spending plan. See `review/inferred_pack_recommendations.md` for the full recommendation report.

Next active phase: verify slot rates in-app (PTCGP app → Pack details → Offering Rates), then re-run EV calculator and recommendation report at verified confidence.

See `docs/current_collection_baseline.md` and `docs/recommendation_readiness.md` for full details.

---

## Historical Screenshot Baseline

`cards.json` currently represents a **provisional 329-card baseline** (211 unique entries).

- The original expected app total was 331. A −2 discrepancy exists and is documented in
  `review/final_ingestion_reconciliation.md` and `review/provisional_baseline.md`.
- All 24 screenshots (IMG_1524–IMG_1547) have been ingested and confirmed.
- **Do not force the total to 331 by adding fake cards.** Quantities are read from the app only.
- Metadata enrichment from Limitless TCG Pocket reference has been applied (179/211 cards enriched).

Validate the current baseline with:

```bash
python3 scripts/validate_cards.py --expected-total 329
```

Informational check (331 is not forced — exit code 1 is expected):

```bash
python3 scripts/validate_cards.py --expected-total 331 || true
```

Canonical database file: `cards.json`

## Analytics and Enrichment Outputs

### Collection analytics

Generated by `python3 scripts/collection_analytics.py`:

| Output | Description |
|---|---|
| `review/collection_analytics.md` | Full analytics report (baseline, metadata completeness, EX/special inventory, type coverage, readiness) |
| `data/exports/collection_analytics.json` | Machine-readable analytics data |

### Metadata enrichment

Generated by `python3 scripts/enrich_metadata.py`:

| Output | Description |
|---|---|
| `review/metadata_enrichment_report.md` | Enrichment summary (cards enriched, fields enriched, ambiguous, sources) |
| `data/exports/metadata_enrichment_report.json` | Machine-readable enrichment report |

Run dry-run first:

```bash
python3 scripts/enrich_metadata.py --dry-run
python3 scripts/enrich_metadata.py
```

### CSV export

Generated by `python3 scripts/export_cards_csv.py`:

| Output | Description |
|---|---|
| `data/exports/cards_collection.csv` | Full card collection export |

### Collection summary

Generated by `python3 scripts/collection_summary.py`:

| Output | Description |
|---|---|
| `review/collection_summary.md` | Overview summary of collection |
| `data/exports/collection_summary.json` | Machine-readable summary |

### Pack source mapping

Generated by `python3 scripts/build_pack_sources.py`:

| Output | Description |
|---|---|
| `data/reference/pack_sources.json` | 3110 card-to-pack mappings from Limitless TCG Pocket (all 17 sets, A1–B3) |
| `data/reference/pack_sources.schema.json` | JSON schema for pack_sources.json |

Validates with: `python3 scripts/validate_pack_sources.py`

Pack name rules:
- A1, A2, A3, A4, B1 (multi-pack): `high` confidence for pack-specific cards; `medium` (shared pool) for cards with no pack label
- All single-pack expansions (A1a, A2a, A2b, A3a, A3b, A4a, A4b, B1a, B2, B2a, B2b, B3): `medium` confidence — expansion name is the pack name
- `pack_name=null` = shared across all packs in that expansion

### Owned pack coverage

Generated by `python3 scripts/owned_pack_coverage.py`:

| Output | Description |
|---|---|
| `review/owned_pack_coverage.md` | Coverage breakdown: exact match, agreed, ambiguous, no match |
| `data/exports/owned_pack_coverage.json` | Machine-readable coverage report |

Coverage summary: 166/211 exact (78.7%), 27 name-agreed, 10 ambiguous, 8 no-match. Broad: 91.5%.

### Ambiguous pack review package

Generated by `python3 scripts/create_ambiguous_review_package.py`:

| Output | Description |
|---|---|
| `review/ambiguous_cards_review.md` | Grouped review with how-to instructions (83 ambiguous cards) |
| `data/exports/ambiguous_cards_review.csv` | Fill in `confirmed_set_code`, `confirmed_card_number`, `confirmed_yes_no` |
| `data/exports/ambiguous_cards_review.json` | Full candidate data per card |
| `review/no_match_cards_review.md` | Review guide for 8 no-match cards |
| `data/exports/no_match_cards_review.csv` | Fill in confirmation columns |
| `data/exports/no_match_cards_review.json` | No-match card details |

After filling in the CSV, apply confirmations:

```bash
python3 scripts/apply_ambiguous_confirmations.py --dry-run  # preview
python3 scripts/apply_ambiguous_confirmations.py --apply    # write to cards.json
```

### Skipped multi-value review package

73 of 83 ambiguous cards were confirmed. 10 were skipped because their filled CSV had
multi-value set codes (e.g. `A1/A4b`) that could not be auto-parsed. This package
provides a focused per-card review for those 10.

Generated by `python3 scripts/create_skipped_multi_value_review.py`:

| Output | Description |
|---|---|
| `review/skipped_multi_value_review.md` | Per-card analysis with candidate table and fill instructions |
| `data/exports/skipped_multi_value_review.csv` | One row per card; fill `confirmed_action` + relevant columns |
| `data/exports/skipped_multi_value_review.json` | Full candidate data (machine-readable) |

After filling the CSV, apply:

```bash
python3 scripts/apply_skipped_multi_value_confirmations.py --dry-run
python3 scripts/apply_skipped_multi_value_confirmations.py --apply
# If owning both versions with qty 1+1 (increases total):
python3 scripts/apply_skipped_multi_value_confirmations.py --apply --allow-quantity-increase
```

Coverage remains 193/211 (91.5%) until these 10 cards are resolved.

### Pack and deck recommendations

**Pack-opening and deck-building recommendations are intentionally deferred.**

Current blockers:
- 91 owned cards have no confirmed pack assignment (83 ambiguous, 8 no-match)
- Pull probability model not yet built
- Meta tier list not integrated

See `docs/recommendation_readiness.md` for the full readiness assessment.

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

## External Reference Sources

External references improve card-name fuzzy matching and provide metadata hints
(is_ex, category, stage) during extraction.  **Quantity always comes from screenshots.**

| Source | Role | URL |
|---|---|---|
| Limitless TCG Pocket | Primary — structured card/set/rarity data | https://pocket.limitlesstcg.com/cards |
| Game8 | Supplemental — all-card, ex-card, special-card lists | https://game8.co/games/Pokemon-TCG-Pocket/ |

### Build external reference (run once, then use `--use-cache`)

```bash
python3 scripts/build_external_reference.py --source limitless
```

### Merge into main reference

```bash
python3 scripts/build_card_reference.py --seed data/reference/manual_card_names_seed.txt --merge-external
```

### Check coverage

```bash
python3 scripts/evaluate_reference_coverage.py
```

External data improves name candidates and metadata hints. It does **not** affect
owned quantities — those are always read from the app screenshot quantity chips.

Recommended workflow remains unchanged:
```
screenshot crops → OCR candidates → user confirmation → batch JSON → merge into cards.json → recommendations
```

See `docs/reference_sources.md` for full details and planned future use (meta deck recommendations).
See `docs/source_strategy.md` for the full external source role matrix.
See `docs/product_roadmap.md` for the complete project roadmap (Phases 1–6).

---

## Recommended Workflow From Here

**Current status:** Batches 001–006 complete (IMG_1524–IMG_1529). Next: IMG_1530.

### Step 1 — Create a review package

```bash
python3 scripts/create_screenshot_review_package.py --screenshot IMG_1530.PNG
```

Outputs:
- `review/screenshot_reviews/IMG_1530_review.md` — OCR candidates, reference hints, per-crop notes
- `review/confirmed/IMG_1530_confirmed_TEMPLATE.csv` — prefilled template (verify before use)

### Step 2 — Confirm the template

```bash
open review/contact_sheets/IMG_1530_contact.png
open review/screenshot_reviews/IMG_1530_review.md
cp review/confirmed/IMG_1530_confirmed_TEMPLATE.csv review/confirmed/IMG_1530_confirmed.csv
# Fill in card_name and quantity for every row
```

### Step 3 — Convert to batch JSON

```bash
python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1530_confirmed.csv \
  --screenshot IMG_1530.PNG \
  --output batches/cards_batch_007.json
python3 scripts/validate_batch.py batches/cards_batch_007.json
```

### Step 4 — Repeat for each remaining screenshot

Repeat Steps 1–3 for IMG_1531 through IMG_1547 (batches 008–024).

### Step 5 — Merge and validate

```bash
python3 scripts/merge_batches.py
python3 scripts/validate_cards.py --expected-total 331
python3 scripts/export_cards_csv.py
```

### Step 6 — Analytics and recommendations

Run collection analytics, pack recommendations, and meta deck recommendations.
See `docs/product_roadmap.md` for details.

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

### Step 3 — Validate card names against reference (catch typos before batch generation)

```bash
python3 scripts/validate_confirmed_csv_against_reference.py \
  --input review/confirmed/IMG_1525_confirmed.csv
```

This catches name spelling errors and typos using the Limitless/reference data
before the batch JSON is created. It shows top-5 fuzzy suggestions for any
unrecognised name and warns when `is_ex` in the CSV is inconsistent with
reference metadata.

Notes:
- Does **not** validate quantity — quantity always comes from reading the app screenshot.
- Does **not** require `special_type` to be known; `unknown` is accepted without error.
- Exits non-zero if any `card_name` is blank, any quantity is non-integer, or any name
  is not found and no high-quality fuzzy suggestion exists.
- Names already present in the confirmed lexicon are always treated as valid, even if
  absent from the external reference.

Fix any errors before proceeding to batch generation.

### Step 4 — Convert to batch JSON

```bash
python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1525_confirmed.csv \
  --screenshot IMG_1525.PNG \
  --output batches/cards_batch_002.json
```

Use `--allow-fewer` for the final screenshot if it has fewer than 9 fully
visible cards.

### Step 5 — Validate the batch

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

## Draft Batch Workflow

When OCR candidates exist but manual confirmation would take too long, use the
draft batch workflow to auto-fill what can be auto-filled and flag the rest for
human review.

### Step 1 — Create draft CSV and batch from template

```bash
python3 scripts/create_draft_batch_from_template.py \
  --screenshot IMG_1538.PNG \
  --template review/confirmed/IMG_1538_confirmed_TEMPLATE.csv \
  --confirmed-output review/confirmed/IMG_1538_confirmed_DRAFT.csv \
  --batch-output batches/cards_batch_015_DRAFT.json \
  --allow-unknown
```

Rules applied automatically:
- **Prefilled** (autofill score ≥ 95): used directly, confidence=medium
- **Candidate** (top match score ≥ 80): used as draft name, confidence=low, flagged for review
- **No match** (score < 80): `UNKNOWN_<stem>_rNcM` placeholder, confidence=low, flagged

All draft entries have `quantity=0` and `needs_review=true`. Output filenames
must end `_DRAFT.csv` / `_DRAFT.json` — the script refuses to write to confirmed paths.

### Step 2 — Summarize all draft batches

```bash
python3 scripts/summarize_draft_batches.py
```

Outputs `review/draft_batch_summary.md` — counts prefilled/candidates/UNKNOWN/qty=0
across all `batches/*_DRAFT.json` files.

### Step 3 — Review and correct the draft CSV

Open the contact sheet and DRAFT CSV side by side:

```bash
open review/contact_sheets/IMG_1538_contact.png
open review/confirmed/IMG_1538_confirmed_DRAFT.csv
```

For each row:
- Replace `UNKNOWN_*` placeholders with the correct card name.
- Replace candidate names you disagree with.
- Fill in the actual quantity from the app.
- Set `special_type` if identifiable.

### Step 4 — Promote draft to confirmed

Once all rows are correct, rename and validate:

```bash
cp review/confirmed/IMG_1538_confirmed_DRAFT.csv review/confirmed/IMG_1538_confirmed.csv
# Edit the copy: remove _DRAFT notes, confirm all fields

python3 scripts/validate_confirmed_csv_against_reference.py \
  --input review/confirmed/IMG_1538_confirmed.csv

python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1538_confirmed.csv \
  --screenshot IMG_1538.PNG \
  --output batches/cards_batch_015.json

python3 scripts/validate_batch.py batches/cards_batch_015.json
```

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

---

## Field Detection Experiments

Confirmed batches serve as ground-truth validation data for evaluating
individual field extraction without touching `cards.json`.

### Evaluate field detection

```bash
python3 scripts/evaluate_field_detection.py
```

Evaluates three fields against confirmed ground truth:

| Field | Method | Notes |
|---|---|---|
| `quantity` | OCR on quantity chip (bottom-left of tile) | Low accuracy on PTCGP chip style; treat as hint only |
| `is_ex` | Name-pattern heuristic (`\bex\b`, `^mega\s`) | ~89% accuracy; 0 false positives; misses unnamed ex cards |
| `card_name` | Fuzzy match from OCR (existing pipeline) | Top-3 accuracy ~33%; useful as review hint |

Outputs `data/extraction/field_detection_report.json` and `field_detection_report.md`.

### Generate a prefilled template for the next screenshot

```bash
python3 scripts/generate_next_review_template.py \
  --screenshot IMG_1530.PNG \
  --output review/confirmed/IMG_1530_confirmed_TEMPLATE.csv
```

Combines autofill candidates, field detection results, and top-3 match
hints to prefill as many fields as can be done conservatively.
Quantity is always left blank — read it from the quantity chip visually.

**User verification is always required** before running
`create_batch_from_confirmation.py` on any template.

---

## Repo Hygiene

Every major development phase includes a cleanup and organization review. The standing policy is in **`CLAUDE.md` section 19 — Repo Hygiene / Cleanup Review**.

Per-pass results are recorded in `review/repo_cleanup_audit.md`.
