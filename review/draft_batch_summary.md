# Draft Batch Summary

Generated: 2026-05-10T19:28:47Z
Draft files: 3

## Totals

| Metric | Count |
|---|---|
| Total draft entries | 27 |
| Prefilled names (autofill) | 1 |
| Candidate names (score ≥ 80) | 5 |
| UNKNOWN names (need ID) | 21 |
| Quantity placeholders (qty=0) | 27 |
| Entries needing review | 27 |

## Action Required

- **21 rows** have UNKNOWN card names — open the contact sheet and identify visually.
- **5 rows** have candidate names (score ≥ 80) — verify against the contact sheet.
- **27 rows** have quantity=0 — read the actual quantity from the app.
- Once all rows in a draft CSV are confirmed, save as a non-DRAFT confirmed CSV and run:
  ```bash
  python3 scripts/validate_confirmed_csv_against_reference.py --input review/confirmed/IMG_XXXX_confirmed.csv
  python3 scripts/create_batch_from_confirmation.py --input ... --screenshot ... --output batches/cards_batch_NNN.json
  python3 scripts/validate_batch.py batches/cards_batch_NNN.json
  ```

## Per-Screenshot Draft Summary

| File | Screenshot | Entries | Prefilled | Candidates | UNKNOWN | Qty=0 | Needs Review |
|---|---|---|---|---|---|---|---|
| cards_batch_015_DRAFT.json | IMG_1538.PNG | 9 | 0 | 3 | 6 | 9 | 9 |
| cards_batch_016_DRAFT.json | IMG_1539.PNG | 9 | 1 | 2 | 6 | 9 | 9 |
| cards_batch_017_DRAFT.json | IMG_1540.PNG | 9 | 0 | 0 | 9 | 9 | 9 |
