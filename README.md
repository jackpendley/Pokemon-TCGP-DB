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
