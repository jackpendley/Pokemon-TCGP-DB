# Claude Code Project Instructions

## Project Goal

This project builds and maintains an exact Pokémon TCG Pocket card collection database from app screenshots.

The database must track cards the way the Pokémon TCG Pocket app does. This means visually distinct cards, special variants, alternate art cards, ex cards, promo cards, shiny cards, immersive cards, crown/gold cards, and other special versions must be tracked as separate entries when the app treats them as separate collection cards.

The user's current collection total is expected to equal exactly 331 cards.

The user currently has 383 pack hourglasses and wants to save 240, meaning they can spend 143. Since a 10-pack costs 120, they can open one 10-pack and still have 263 saved.

## Critical Workflow Rule

Work in small phases.

Do not attempt to complete the entire project in one run.

Never process more than one screenshot per prompt unless the user explicitly instructs otherwise.

Never do card extraction, database merging, validation, and deck recommendations in the same prompt.

Always stop after completing the exact requested phase.

## Hard Stop Behavior

At the end of every response, stop and report only:

1. Files created or edited
2. What was completed
3. Any uncertainties
4. The exact next recommended prompt

Do not continue into the next phase unless explicitly instructed.

## Database Philosophy

Accuracy matters more than speed.

Do not guess.

If a card is uncertain, mark it as needing review rather than pretending it is known.

If two cards have the same name but different artwork, rarity, special treatment, border, set, or collector entry, they must be separate database entries.

Do not merge same-name cards unless you are confident they are the exact same app card.

## Canonical Database File

`cards.json` is the canonical database.

It should contain an array of card objects.

Each card entry must use this schema:

{
  "id": "unique_stable_id",
  "card_name": "",
  "quantity": 0,
  "card_category": "Pokemon | Trainer | Item | Supporter | Tool | Stadium | Fossil | Unknown",
  "pokemon_type": "Grass | Fire | Water | Lightning | Psychic | Fighting | Darkness | Metal | Dragon | Colorless | None | Unknown",
  "stage": "Basic | Stage 1 | Stage 2 | None | Unknown",
  "hp": null,
  "is_ex": false,
  "special_type": "normal | full_art | illustration_rare | special_art | immersive | crown_gold | shiny | rainbow | promo | special_trainer | alternate_art | unknown",
  "rarity": "visible rarity if known, otherwise unknown",
  "set_or_pack": "visible set/pack if known, otherwise unknown",
  "variant_notes": "",
  "source_screenshot": "",
  "source_row": null,
  "source_column": null,
  "confidence": "high | medium | low",
  "needs_review": false,
  "review_reason": ""
}

## Stable ID Rules

Use deterministic IDs.

Format:

normalized_card_name + "_" + normalized_special_type + "_" + normalized_set_or_pack + "_vN

Examples:

bulbasaur_normal_unknown_v1
bulbasaur_special_art_unknown_v1
mega_charizard_y_ex_normal_crimson_blaze_b1a_v1
quick_grow_extract_special_trainer_unknown_v1

Rules:

- Use lowercase.
- Replace spaces and punctuation with underscores.
- Remove duplicate underscores.
- Use `unknown` if set/pack is not visible.
- Use `v1`, `v2`, etc. only when needed to distinguish variants.

## Extraction Rules

When extracting from screenshots:

1. Process only the screenshot requested.
2. Do not edit `cards.json` during extraction.
3. Save extracted cards into `batches/cards_batch_XXX.json`.
4. Include `source_screenshot`, `source_row`, and `source_column`.
5. Use the visible quantity shown in the app grid.
6. If quantity is unclear, set quantity to 0, confidence to low, and needs_review to true.
7. If card name is unclear, use `card_name: "unknown"`.
8. If special type is unclear, use `special_type: "unknown"`.
9. If the card appears special but exact category is unclear, use `needs_review: true`.
10. Do not infer set, rarity, HP, type, or stage unless visible or confidently known from the card image.

## Special Type Categories

Each card must have one of these `special_type` values:

- `normal`
- `full_art`
- `illustration_rare`
- `special_art`
- `immersive`
- `crown_gold`
- `shiny`
- `rainbow`
- `promo`
- `special_trainer`
- `alternate_art`
- `unknown`

If uncertain, use `unknown` and mark `needs_review: true`.

## Card Category Values

Use one of:

- `Pokemon`
- `Trainer`
- `Item`
- `Supporter`
- `Tool`
- `Stadium`
- `Fossil`
- `Unknown`

If unsure, use `Unknown`.

## Pokémon Type Values

Use one of:

- `Grass`
- `Fire`
- `Water`
- `Lightning`
- `Psychic`
- `Fighting`
- `Darkness`
- `Metal`
- `Dragon`
- `Colorless`
- `None`
- `Unknown`

Trainer cards should use `None`.

## Confidence Rules

Use `high` only when the card name, quantity, and variant/special type are clear.

Use `medium` when the card name and quantity are clear but some metadata is uncertain.

Use `low` when the card name, quantity, or variant identity is uncertain.

Every `low` confidence card must have `needs_review: true`.

## Review Rules

Every card with `needs_review: true` must include a clear `review_reason`.

Also add the card to `ambiguous_cards.md` with:

- source screenshot filename
- approximate row and column
- suspected card name
- suspected quantity
- why it is ambiguous
- what crop or screenshot the user should provide to confirm it

## Batch Files

Use batch files during extraction.

Example:

batches/cards_batch_001.json
batches/cards_batch_002.json
batches/cards_batch_003.json

Each batch should be a JSON array of card objects using the canonical schema.

Do not merge batches into `cards.json` until explicitly asked.

## Merging Rules

When merging batches:

Deduplicate only when all of these match or are confidently equivalent:

- `card_name`
- `special_type`
- `set_or_pack`
- `variant_notes`
- visual identity
- app-style card identity

If unsure, keep entries separate and mark both as needing review.

During merge, sum quantities for confirmed duplicate entries.

Create or update `merge_report.md`.

## Validation Requirements

The validation script should check:

1. `cards.json` exists.
2. `cards.json` is valid JSON.
3. Top-level value is an array.
4. Every card has required fields.
5. Every ID is unique.
6. Every quantity is a non-negative integer.
7. Every card has a valid `special_type`.
8. Every card has valid `confidence`.
9. Every card has valid `needs_review`.
10. Every `needs_review: true` card has a non-empty `review_reason`.
11. Every low-confidence card has `needs_review: true`.
12. Total quantity equals the expected total passed as an argument.
13. No blank card names unless marked `"unknown"`.
14. Every low-confidence or review-needed card appears in `ambiguous_cards.md`.

Run validation with:

python scripts/validate_cards.py --expected-total 331

## CSV Export

`cards.csv` should mirror `cards.json`.

Do not manually maintain `cards.csv`.

Create a script that exports `cards.json` to `cards.csv`.

## Files to Maintain

Expected project files:

CLAUDE.md
README.md
cards.schema.json
cards.json
cards.csv
ambiguous_cards.md
screenshots_manifest.md
merge_report.md
deck_recommendations.md
batches/
scripts/validate_cards.py
scripts/export_cards_csv.py
scripts/merge_batches.py

## Deck Recommendation Rules

Do not make deck recommendations until the database has been extracted, merged, and validated.

Deck recommendations must be based on `cards.json`.

When creating deck recommendations, include:

1. Best immediate deck from the user's collection
2. Why that deck is closest
3. Missing cards
4. Best next 10-pack to open
5. Whether spending exactly 120 hourglasses is justified
6. Whether saving all hourglasses is better
7. Alternative deck paths
8. Cards that should be prioritized because they support meta archetypes

Current deck candidates to consider include:

- Fire / Mega Charizard Y ex
- Mega Charizard X ex
- Suicune ex / Greninja
- Mega Sceptile ex
- Mega Lucario ex
- Mega Altaria ex
- Mega Absol ex
- Any stronger archetype clearly supported by `cards.json`

If current meta information is required but unavailable locally, state what external data should be checked rather than guessing.

## Forbidden Behaviors

Do not:

- Process all screenshots at once.
- Edit `cards.json` during individual screenshot extraction.
- Guess unknown cards.
- Merge same-name variants carelessly.
- Create deck recommendations before validation.
- Run long exploratory loops.
- Reprocess previous screenshots unless asked.
- Continue to the next phase without instruction.
- Claim the database is exact unless the total validates to 331 and all ambiguous cards are resolved or clearly flagged.