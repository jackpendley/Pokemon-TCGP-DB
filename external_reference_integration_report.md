# External Reference Integration Report

Generated: 2026-05-10

## Limitless Scrape Status

**Partial — sets B1, B1a, B2, B2a, B2b, B3 complete. A-series (A1–A4b) not yet fetched.**

The scrape was stopped at ~20 minutes to avoid blocking the session. HTML pages
are cached in `data/reference/external/html_cache/` (gitignored). To resume:

```bash
python3 scripts/build_external_reference.py --source limitless
```

This will only fetch uncached pages (A-series), skipping already-downloaded B-series.

## External Reference Summary

| Metric | Value |
|---|---|
| Sets scraped | B1, B1a, B2, B2a, B2b, B3 (6 of 17) |
| Total card entries | 1,171 |
| Unique card names | 771 |
| is_ex cards | 191 |
| Trainer-type cards | 81 |

## Reference Coverage Improvement

| Metric | Before | After |
|---|---|---|
| Seed reference size | 659 | 1,144 (+485 from merge) |
| Confirmed-name coverage | ~85%* | 92.7% (51/55) |
| External ref coverage alone | — | 78.2% (43/55) |
| Missing names | — | Cyrus, Eelektross, Example Card, Urshifu |

*Estimated from prior session. `Example Card` is a test artifact in batch data; not a real card.
`Urshifu` is likely in A-series (not yet scraped). `Eelektross` and `Cyrus` may be in A-series.

## OCR Auto-Match Improvement

| Metric | Before | After |
|---|---|---|
| Auto-matched crops (score ≥ 80) | 31 / 216 | 51 / 216 |
| Improvement | — | +20 crops |

## Autofill Candidates

- Before: 13 auto-fill eligible (score ≥ 95)
- After: 10 auto-fill eligible

Slight reduction is expected — the expanded reference introduced more candidates that
compete against trainer/item names, lowering some scores below threshold.

## Template Improvements (IMG_1530)

- External reference hints now appear in notes for matched candidates
- Example: r3c3 Bouffalant now shows `ext:stage=Basic`
- Top-3 candidates expanded with new names from B-series (Probopass, Mega Steelix ex)
- No names auto-filled (all below 90 threshold for IMG_1530 — confirmed as expected)

## Detection Accuracy (unchanged from prior run)

| Field | Accuracy |
|---|---|
| Quantity OCR | 9% (chip format not readable by Tesseract) |
| is_ex heuristic | 89% (0 false positives, 6 false negatives) |
| Card-name top-1 | 18% |
| Card-name top-3 | 33% |

OCR accuracy did not change — the reference expansion affects fuzzy matching, not OCR quality.

## What Was Intentionally Postponed

| Item | Reason |
|---|---|
| Image matching | Not practical without significant ML tooling |
| Quantity OCR improvement | PTCGP chip style resists Tesseract; would need custom model |
| Complex Game8 scraping | Hub-and-spoke structure requires more engineering; Limitless covers most needs |
| Meta deck recommendations | Requires completed `cards.json` first |
| Complete A-series scrape | Takes ~15 more minutes; easy to resume with `--use-cache` |

## Conclusion

The external reference integration is functional and provides measurable improvement:

- 485 new card names added to reference (659 → 1,144)
- OCR auto-match improved 31 → 51 crops (+65%)
- 92.7% of confirmed card names now covered

**The manual confirmation workflow is unblocked and improved.** Proceed with
creating confirmed CSVs and batch files for remaining screenshots (IMG_1530 onward).

## Recommended Next Step

```
Read CLAUDE.md completely. We are creating the confirmed CSV and batch file for
IMG_1530 only. Use the template at review/confirmed/IMG_1530_confirmed_TEMPLATE.csv.
```
