# Current Collection Baseline

## Active Baseline

| Field | Value |
|---|---|
| Source file | `collection.json` |
| Date | 2026-05-11 |
| Meta declared total | 380 |
| Actual verified count | 376 |
| Unique entries | 220 |
| Format | Pokemon TCG Pocket |

> **Count discrepancy: 4 cards.** `collection.json` meta says 380 but the sum of all `count` fields is 376. This was detected by `scripts/validate_current_collection.py`. The file may be missing a few entries. User should audit and update `collection.json` directly before running pack recommendations that depend on exact totals.

## Relationship to Old Baseline

| Baseline | File | Card Count | Status |
|---|---|---|---|
| **Current active** | `collection.json` | 376 verified (380 declared) | Use for all new recommendations |
| Historical/provisional | `cards.json` | 329 | Screenshot ingestion artifact — preserved for provenance |

- `collection.json` is manually authored and represents the user's exact current Pokémon TCG Pocket collection as of 2026-05-11.
- `cards.json` is the result of the screenshot-extraction pipeline (batches → merge → enrichment → pack-source resolution). It is preserved for provenance and future screenshot-driven updates.
- The two files are **not expected to match exactly** in total count. The old 329 count reflects cards captured from app screenshots; the new 380 count reflects the user's full current collection at the time of manual entry.

## Future Recommendations

All deck-building and pack-opening recommendations should be generated from:
- `data/current/collection_normalized.json` — clean machine-readable output (no comments, generated fields added)
- `data/current/collection_summary.json` — aggregated statistics

Do **not** use `cards.json` (the old 329-card baseline) as the input for new recommendation generation.

## Screenshot Ingestion Pipeline

The old ingestion pipeline remains useful for:
- Tracking new cards from fresh screenshots
- Auditing specific cards for set/rarity enrichment
- Provenance: showing exactly which screenshots each card was identified from

Scripts relevant to the old pipeline:
- `scripts/validate_cards.py --expected-total 329`
- `scripts/validate_pack_sources.py`
- `scripts/owned_pack_coverage.py`
- `scripts/apply_ambiguous_confirmations.py`

## Deck Recommendations Prototype

`deck-recommendations.jsx` is a manually authored React prototype UI for deck recommendations, based on the 380-card collection.

- It references 8 decks: 4 buildable, 4 chase.
- Validated by `scripts/validate_deck_recommendations.py`.
- Validation output: `review/deck_recommendation_validation.md`

**All 4 buildable decks are fully buildable** from the current collection.  
**All 4 chase decks are 1 card short** of the key ex Pokémon needed for a second copy.

## New Scripts Added in This Phase

| Script | Purpose |
|---|---|
| `scripts/validate_current_collection.py` | Validate `collection.json` (supports JSONC comments) |
| `scripts/normalize_current_collection.py` | Output clean JSON + summary from `collection.json` |
| `scripts/validate_deck_recommendations.py` | Compare deck card lists against owned collection |

## Generated Outputs

| File | Description |
|---|---|
| `data/current/collection_normalized.json` | Clean JSON with no comments; generated fields added |
| `data/current/collection_summary.json` | Aggregated statistics (by type, stage, ex count, etc.) |
| `review/current_collection_summary.md` | Human-readable collection summary |
| `review/deck_recommendation_validation.md` | Deck-by-deck validation report |
| `data/exports/deck_recommendation_validation.json` | Machine-readable deck validation |
