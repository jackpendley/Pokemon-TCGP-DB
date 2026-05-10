# Claude Code Project Instructions

## Project Goal

This project builds and maintains an exact Pokémon TCG Pocket card collection database from app screenshots.

The database must track cards the way the Pokémon TCG Pocket app does. This means visually distinct cards, special variants, alternate art cards, ex cards, promo cards, shiny cards, immersive cards, crown/gold cards, and other special versions must be tracked as separate entries when the app treats them as separate collection cards.

The user's current collection total is expected to equal exactly 331 cards.

The user currently has 383 pack hourglasses and wants to save 240, meaning they can spend 143. Since a 10-pack costs 120, they can open one 10-pack and still have 263 saved.

## Ultimate Product Goal

Build a practical collection database that enables:
1. Tracking owned cards and quantities
2. Set/variant/collection progress tracking
3. Precise pack-opening recommendations (which pack to open, when, and why)
4. Meta deck recommendations (which current decks can be built or pursued)
5. Easy future updates via screenshot uploads

Everything added to this project must serve one of these goals.

## Anti-Overengineering Principle

Do not add infrastructure that does not measurably reduce manual confirmation work
or improve recommendation quality.

Specifically:
- Do not build image matching or ML training pipelines.
- Do not chase perfect quantity OCR — users read quantity chips from the app.
- Do not build complex Game8 or Pokémon.com scrapers unless trivially available.
- Do not add automation layers that require more debugging than manual work saves.
- External references are name/metadata hints only; they never write to cards.json.
- User verification is always required before any batch file is created.
- Stop before any step that is harder than "copy template → fill names+quantities → run one script".

The shortest path to a validated collection DB and recommendation engine is always preferred.

## Operating Principle

Act like a senior engineer maintaining a clean, durable repo.

Do not blindly follow narrow task wording if there is an obvious best-practice repo hygiene issue that should be addressed before moving forward. If a cleanup, validation, or organization step is clearly necessary to achieve the project goal safely, propose or perform it within the current phase if it does not violate hard constraints.

Examples of expected proactive behavior:

- Remove redundant local artifacts once they are proven unnecessary.
- Keep only the optimal working source files.
- Avoid committing large binaries, screenshots, caches, zip files, generated temp files, or local IDE metadata.
- Keep scripts modular and reusable.
- Prefer deterministic, auditable workflows over ad hoc manual edits.
- Validate before and after meaningful changes.
- Stop before high-risk or scope-expanding work.

## Critical Workflow Rule

Work in small phases.

Do not attempt to complete the entire project in one run.

Never process more than one screenshot per prompt unless the user explicitly instructs otherwise.

Never do card extraction, database merging, validation, and deck recommendations in the same prompt.

Always stop after completing the exact requested phase.

If the user asks for general improvement, optimization, organization, or best practices, proactively inspect the current phase for obvious repo hygiene issues and address them if safe.

## Hard Stop Behavior

At the end of every response, stop and report only:

1. Files created or edited
2. What was completed
3. Any uncertainties or blockers
4. Validation results
5. Git status
6. The exact next recommended prompt

Do not continue into the next phase unless explicitly instructed.

## Git and Repository Best Practices

Use git carefully and consistently.

Before each phase:

1. Run `git status`.
2. Confirm the current branch.
3. Confirm whether the working tree is clean.
4. Do not start new work on a dirty tree unless the dirty changes are intentional and understood.

During each phase:

1. Make focused, minimal changes.
2. Commit only logically related changes.
3. Do not mix unrelated work into one commit.
4. Do not commit screenshots, zip files, caches, temporary files, virtual environments, local Claude config, or IDE metadata.
5. Do not force push.
6. Do not rewrite commit history unless the user explicitly asks.
7. Use descriptive commit messages.
8. Prefer text/code artifacts that can be diffed and reviewed.

After each phase:

1. Run relevant validation commands.
2. Run `git status`.
3. Commit if appropriate.
4. Push only when explicitly instructed or when the user has established that pushes should happen after commits.
5. If push fails due to authentication, clearly explain the blocker and do not attempt unsafe credential changes.

The intended remote is:

git@github.com:jackpendley/Pokemon-TCGP-DB.git

If SSH authentication fails:

1. Check whether a public key exists.
2. Check whether the key is loaded in the SSH agent.
3. Test `ssh -T git@github.com`.
4. If GitHub rejects the key, stop and tell the user to add the public key to GitHub.
5. Do not switch to HTTPS unless the user explicitly chooses that option.

## Local File Hygiene

The repo should stay clean and modular.

Allowed tracked files include:

- Markdown documentation
- JSON database files
- JSON schema files
- CSV exports generated from tracked JSON
- Python scripts
- Batch JSON files after they are intentionally created
- Manifest and audit reports

Do not track:

- Raw screenshot image files
- Zip archives
- macOS metadata folders such as `__MACOSX`
- `.DS_Store`
- Python caches
- virtual environments
- local `.env` files
- Claude local config
- temporary logs
- crop images unless the user explicitly requests they be tracked

The active local screenshot source should be:

screenshots/IMG_1524.PNG through screenshots/IMG_1547.PNG

These screenshots are used for local extraction but are gitignored.

Redundant files such as `Archive.zip` and `screenshots/__MACOSX/` should be removed after verifying that the 24 real PNG screenshots are intact.

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

## Screenshot Extraction Scope

For each screenshot, extract only the completely visible cards in the main 3×3 grid (3 columns × 3 rows = 9 cards) that have visible quantity chips.

Rules:

- For normal screenshots, extract only the 9 completely visible cards in the main 3×3 grid.
- A card counts as extractable only if the full card tile and its quantity chip are visible.
- Do not create entries for partial cards at the top or bottom edge of the screenshot.
- Do not create placeholder entries for cards that will be fully visible in a later screenshot.
- Do not guess names from unclear artwork.
- If a fully visible card has a visible quantity but an unclear name, create an unknown entry with `needs_review: true`.
- If a card is not fully visible or its quantity chip is not visible, skip it entirely.
- The final screenshot may contain fewer than 9 fully visible cards; extract only those fully visible cards.

## Primary and Secondary Extraction Fields

Primary fields must be populated for every entry:

- `card_name`
- `quantity`
- `special_type`
- `is_ex`
- `variant_notes`
- `source_screenshot`
- `source_row`
- `source_column`
- `confidence`
- `needs_review`
- `review_reason`

Secondary fields may use `"unknown"`, `"Unknown"`, `"None"`, `false`, or `null` when not clearly visible:

- `card_category`
- `pokemon_type`
- `stage`
- `hp`
- `rarity`
- `set_or_pack`

## One-Screenshot Extraction Workflow

For each screenshot:

1. Read `CLAUDE.md`.
2. Read `extraction_checklist.md`.
3. Process exactly one screenshot.
4. Create exactly one batch file.
5. Do not edit `cards.json`.
6. Run `python3 scripts/validate_batch.py <batch_file>`.
7. Update `ambiguous_cards.md` only for uncertain cards.
8. Stop and report results.

Never process the next screenshot automatically.

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

python3 scripts/validate_cards.py --expected-total 331

## CSV Export

`cards.csv` should mirror `cards.json`.

Do not manually maintain `cards.csv`.

Create a script that exports `cards.json` to `cards.csv`.

Run CSV export with:

python3 scripts/export_cards_csv.py

## Files to Maintain

Expected project files:

CLAUDE.md
README.md
cards.schema.json
cards.json
cards.csv
ambiguous_cards.md
screenshots_manifest.md
screenshots_inventory.json
extraction_checklist.md
merge_report.md
deck_recommendations.md
batches/
scripts/validate_cards.py
scripts/validate_batch.py
scripts/export_cards_csv.py
scripts/merge_batches.py
scripts/inventory_screenshots.py

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

## Proactive Quality Checks

Before suggesting the next phase, check whether any of these should happen first:

- Is the git working tree clean?
- Are generated files up to date?
- Are ignored local artifacts cluttering the working directory?
- Are there redundant source files?
- Are validation scripts still passing/failing only for expected reasons?
- Is the next step too broad?
- Would the next step risk burning excessive context?
- Should the next step be split smaller?

If the next step is too broad, propose a smaller safer prompt.

## Forbidden Behaviors

Do not:

- Process all screenshots at once.
- Edit `cards.json` during individual screenshot extraction.
- Guess unknown cards or include speculative names in card_name or review_reason.
- Merge same-name variants carelessly.
- Create deck recommendations before validation.
- Run long exploratory loops.
- Reprocess previous screenshots unless asked.
- Continue to the next phase without instruction.
- Claim the database is exact unless the total validates to 331 and all ambiguous cards are resolved or clearly flagged.
- Commit large binaries or image files.
- Force push.
- Switch remote authentication methods without user approval.