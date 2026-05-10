# Final Ingestion Reconciliation

Generated: 2026-05-10

## Summary

| Metric | Value |
|---|---|
| Expected app total | 331 |
| Confirmed batch total (batches 001–024) | 329 |
| Discrepancy | **−2 cards** |

## Batch Totals

| Batch | Screenshot | Entries | Qty |
|---|---|---|---|
| 001 | IMG_1524.PNG | 9 | 9 |
| 002 | IMG_1525.PNG | 9 | 11 |
| 003 | IMG_1526.PNG | 9 | 9 |
| 004 | IMG_1527.PNG | 9 | 13 |
| 005 | IMG_1528.PNG | 9 | 10 |
| 006 | IMG_1529.PNG | 9 | 11 |
| 007 | IMG_1530.PNG | 9 | 20 |
| 008 | IMG_1531.PNG | 9 | 12 |
| 009 | IMG_1532.PNG | 9 | 16 |
| 010 | IMG_1533.PNG | 9 | 13 |
| 011 | IMG_1534.PNG | 9 | 9 |
| 012 | IMG_1535.PNG | 9 | 12 |
| 013 | IMG_1536.PNG | 9 | 11 |
| 014 | IMG_1537.PNG | 9 | 17 |
| 015 | IMG_1538.PNG | 9 | 20 |
| 016 | IMG_1539.PNG | 9 | 21 |
| 017 | IMG_1540.PNG | 9 | 11 |
| 018 | IMG_1541.PNG | 9 | 14 |
| 019 | IMG_1542.PNG | 9 | 19 |
| 020 | IMG_1543.PNG | 9 | 15 |
| 021 | IMG_1544.PNG | 9 | 14 |
| 022 | IMG_1545.PNG | 9 | 16 |
| 023 | IMG_1546.PNG | 9 | 17 |
| 024 | IMG_1547.PNG | 4 | 9 |
| **Total** | | **212 entries** | **329** |

## IMG_1547 Overlap Handling

IMG_1547 partially overlaps IMG_1546. The following rows were deliberately omitted
from batch 024 to avoid double-counting:

| Row | Card | Reason |
|---|---|---|
| r1c1 | Pokédex | Duplicates IMG_1546 r3c1 |
| r1c2 | Poké Ball | Duplicates IMG_1546 r3c2 |
| r1c3 | Red Card | Duplicates IMG_1546 r3c3 |
| r3c2 | (empty) | End-of-collection empty slot |
| r3c3 | (empty) | End-of-collection empty slot |

Batch 024 contains only 4 rows: r2c1 Professor's Research (4), r2c2 Victini (1),
r2c3 Zygarde (1), r3c1 Zygarde (3).

## Reference Coverage Gaps

Four card names passed user confirmation but were absent from the main and external
reference databases. These are valid PTCGP cards with reference coverage gaps:

| Card | Found in batch | Status |
|---|---|---|
| Hand Scope | 023 (IMG_1546 r2c3) | Valid PTCGP Item — reference gap |
| Pokédex | 023 (IMG_1546 r3c1) | Valid PTCGP Item — reference gap |
| Red Card | 023 (IMG_1546 r3c3) | Valid PTCGP Item — reference gap |
| Zygarde | 024 (IMG_1547 r2c3, r3c1) | Valid PTCGP Pokémon — reference gap |

These names should be added to the confirmed lexicon after batch creation.

## Discrepancy Analysis

Confirmed batch total is **329**, expected app total is **331**.

### Possible causes

**a) One quantity misread by 2**
A single card's quantity chip was read as N but is actually N+2.
High likelihood — quantity chips on crowded screenshots can be hard to read.

**b) Two quantities each misread by 1**
Two different cards each have quantities underread by 1.
Also plausible — small chips in row 3 positions are hardest to read.

**c) One omitted visible card**
A fully visible card with a quantity chip was skipped in one screenshot.
Less likely — each screenshot was processed with a 3×3 grid structure.

**d) IMG_1547 overlap adjustment caused a net loss**
If the 3 overlapping cards (Pokédex, Poké Ball, Red Card) in IMG_1546 r3
were each counted only once (in batch 023) but the app's 331 total counted
them twice due to how the collection scrolls, removing the duplicates would
account for −3. However this would mean the true base total minus overlap
should be 329, not 331. More likely the 331 is accurate and the gap is
elsewhere.

**e) The stated 331 total included cards that were later exchanged, evolved,
or added after screenshots were taken**
If the collection changed between the screenshots and the stated total, the
discrepancy would be structural.

### Recommendation

Before merging into `cards.json`, the user should:

1. Re-check quantity chips for any batch where a card has qty=1 or qty=2
   (most likely to have misreads by 1).
2. Confirm the app's current displayed total is still 331.
3. If the discrepancy cannot be resolved, a provisional merge with a known
   −2 discrepancy is acceptable as long as `needs_review=true` entries are
   tracked for future reconciliation.

Do NOT force quantity fields to make the total reach 331 — accuracy requires
reading from the app, not arithmetic adjustment.

## Next Steps

Once the 2-card discrepancy is resolved or accepted:

```bash
python3 scripts/merge_batches.py
python3 scripts/validate_cards.py --expected-total 331
python3 scripts/export_cards_csv.py
```
