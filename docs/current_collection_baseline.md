# Current Collection Baseline

## Active Baseline

| Field | Value |
|---|---|
| Source file | `collection.json` |
| Date | 2026-05-11 |
| Meta declared total | 380 |
| Actual verified count | **380 ✅** |
| Unique entries | 224 |
| Format | Pokemon TCG Pocket |

`collection.json` validates at exactly 380. No count discrepancy.

## Screenshots

| Field | Value |
|---|---|
| Source directory | `screenshots/` |
| Files | 26 (IMG_1556–IMG_1581) |
| Format | Manually cropped 3×3 card grid |
| Total expected card slots | 232 (25 × 9 standard + 1 × 7 final) |
| Unique collection entries | 224 |
| Structural consistency | ✅ 232 slots ≥ 224 entries |

The screenshots show the app's card collection grid. Each tile is a unique card entry with a quantity chip. The 232 slots exceed the 224 unique entries; extra slots may represent scrolling overlaps or empty positions.

## Relationship to Old Baseline

| Baseline | File | Card Count | Status |
|---|---|---|---|
| **Current active** | `collection.json` | **380 validated** | Use for all new recommendations |
| Historical/provisional | `cards.json` | 329 | Screenshot ingestion artifact — preserved for provenance |

- `collection.json` is manually authored and represents the user's exact current Pokémon TCG Pocket collection as of 2026-05-11.
- `cards.json` is the result of the screenshot-extraction pipeline (batches → merge → enrichment → pack-source resolution). Preserved for provenance.
- The two files are not expected to match. 329 came from screenshots (incomplete); 380 is the full manually entered collection.

## Deck Recommendations Status

`deck-recommendations.jsx` is a manually authored React prototype UI.

- 4 buildable decks: all fully buildable from current collection ✅
- 4 chase decks: each exactly 1 ex Pokémon short (need 2, have 1)

Chase cards needed:
- Ivysaur (×1 more) — for Mega Venusaur ex deck
- Incineroar ex (×1 more)
- Zygarde ex (×1 more)
- Magnezone ex (×1 more)

## Scripts

| Script | Purpose |
|---|---|
| `scripts/validate_current_collection.py` | Validate `collection.json` (JSONC-aware) |
| `scripts/normalize_current_collection.py` | Generate clean JSON + summary from `collection.json` |
| `scripts/validate_deck_recommendations.py` | Compare deck card lists against owned collection |
| `scripts/inventory_screenshots.py` | Inventory new cropped grid screenshots |
| `scripts/reconcile_current_collection_sources.py` | Structural reconciliation of collection vs screenshots |
| `scripts/current_collection_pack_coverage.py` | Pack-source coverage for 380-card collection |
| `scripts/create_current_pack_review.py` | Review package for unresolved pack mappings (fallback report) |
| `scripts/apply_current_pack_confirmations.py` | Apply user-filled pack confirmations (fallback, dry-run default) |
| `scripts/build_screenshot_collection_alignment.py` | Order-based screenshot-to-collection alignment (no OCR) |
| `scripts/validate_screenshot_collection_alignment.py` | Validate alignment output |
| `scripts/score_pack_source_confidence.py` | Per-entry pack-source confidence scoring |

## Pack-Source Coverage

| Metric | Value |
|---|---|
| Entries resolved | 157/224 (70%) |
| Exact match | 108 entries |
| Unanimous pack | 49 entries |
| Ambiguous (cross-expansion) | 59 entries |
| No match | 3 (Zygarde forms) |
| Known trainer gap | 5 (common items) |

The 67 unresolved entries are the target set for automated confidence scoring. Manual CSV review (`data/exports/current_pack_source_review.csv`) is a fallback tool for below-threshold cases, not the primary next step.

## Screenshot-to-Collection Alignment

| Metric | Value |
|---|---|
| Method | Order-only sequential (no OCR) |
| Aligned | 224/224 entries |
| Surplus slots | 8 (likely IMG_1581 scroll-overlap) |
| Confidence (aligned) | low (0.50–0.799) — max 0.70 without OCR |
| Validation | PASS |

## Pack-Source Confidence Scoring

| Metric | Value |
|---|---|
| Entries scored | 224 |
| Average score | 0.8204 |
| Auto-accept (≥ 0.95) | **108** |
| Secondary evidence (0.80–0.949) | **49** |
| Low confidence (0.50–0.799) | **59** (ambiguous cross-set) |
| Unresolved (< 0.50) | **8** (Zygarde + trainer gaps) |
| Validation | PASS |

## Generated Outputs

| File | Description |
|---|---|
| `data/current/collection_normalized.json` | Clean JSON, no comments, generated fields |
| `data/current/collection_summary.json` | Aggregated statistics |
| `data/current/screenshot_inventory.json` | Screenshot file list and slot counts |
| `data/current/screenshot_manifest.json` | Slot-level manifest (card_name/quantity blank) |
| `data/current/current_collection_reconciliation.json` | Structural reconciliation result |
| `data/current/screenshot_collection_alignment.json` | Order-based slot→entry alignment with confidence scores |
| `data/current/pack_source_confidence_scores.json` | Per-entry pack-source confidence scores and best candidates |
| `review/current_collection_summary.md` | Human-readable collection summary |
| `review/screenshot_inventory.md` | Screenshot inventory table |
| `review/screenshot_manifest.md` | Per-slot manifest (blank for future OCR or manual fill) |
| `review/current_collection_reconciliation.md` | Reconciliation report |
| `review/screenshot_collection_alignment.md` | Alignment report with confidence distribution |
| `review/pack_source_confidence_scores.md` | Per-entry pack-source confidence report |
| `review/deck_recommendation_validation.md` | Deck-by-deck validation |
| `data/exports/screenshot_collection_alignment.csv` | Full alignment table (one row per screenshot slot) |
| `data/exports/pack_source_confidence_scores.csv` | Per-entry confidence scores, best candidates, next actions |
| `data/exports/deck_recommendation_validation.json` | Machine-readable deck validation |

## Old Screenshot Ingestion Pipeline (Historical)

The pipeline scripts remain for screenshot-driven updates and provenance:
- `scripts/validate_cards.py --expected-total 329`
- `scripts/validate_pack_sources.py`
- `scripts/owned_pack_coverage.py`
- `scripts/apply_ambiguous_confirmations.py`

Do **not** use `cards.json` (329-card baseline) for new recommendation generation.
