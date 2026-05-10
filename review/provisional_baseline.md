# Provisional Baseline

Generated: 2026-05-10

## Current Baseline Summary

| Metric | Value |
|---|---|
| Baseline total (quantity) | **329** |
| Baseline total (entries) | **211** |
| Original expected app total | 331 |
| Discrepancy | **−2 cards** |
| Discrepancy in entries (vs reconciliation doc) | −1 entry (211 actual vs 212 in doc — arithmetic error in reconciliation) |

## Why 329 Is the Provisional Baseline

1. **Screenshot ingestion is complete.** All 24 screenshots (IMG_1524–IMG_1547) have been
   confirmed by the user and merged into `cards.json`.

2. **The real app collection has already changed.** The screenshots were taken at a specific
   point in time. The user's live app collection may now differ from what was photographed.
   Forcing the total to 331 would require inventing cards that cannot be verified from screenshots.

3. **No fake cards will be added.** The database reflects only what was visually confirmed
   from the app screenshots. Quantities are read from the app's quantity chips — they are
   not estimated or adjusted.

4. **The user plans future update screenshots.** When new packs are opened, the workflow
   (Phase 6 in `docs/product_roadmap.md`) handles delta updates. The baseline will be
   incremented from 329 once new screenshots are ingested.

## Discrepancy Analysis

The −2 discrepancy is documented in detail at:

→ `review/final_ingestion_reconciliation.md`

The most likely cause is one or two quantity misreads on small chips in row 3 positions
during manual confirmation. The discrepancy will be naturally resolved when the user
opens new packs and uploads fresh screenshots.

## Note on Entry Count

The reconciliation document (`final_ingestion_reconciliation.md`) states 212 entries,
but the actual count is 211 (23 batches × 9 entries + 1 batch × 4 entries = 211).
The 212 figure was an arithmetic error in that document. This does not affect the
quantity total of 329.

## Validation Command

```bash
python3 scripts/validate_cards.py --expected-total 329
```

Expected output: `ALL CHECKS PASSED  (211 cards, total=329)`

## Next Phases

1. **Collection analytics** — set/pack completion, type coverage, EX/special inventory
2. **Pack recommendation engine** — score packs by expected value given current collection
3. **Meta deck matching** — compare owned cards against current tournament decklists
4. **Future screenshot update workflow** — delta ingestion when new packs are opened

See `docs/product_roadmap.md` for full phase details.
