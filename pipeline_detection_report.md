# Pipeline Detection Report

Generated: 2026-05-10 — after crop override tuning pass 2 (17 overrides applied)

---

## Summary

| Metric | Value |
|---|---|
| Total crops | 216 |
| OCR entries | 216 |
| With non-empty OCR text | 169 (78%) |
| Empty / no OCR text | 47 (22%) |
| Auto-matched (score ≥ 80) | 31 (14%) |
| Needs human review | 185 (86%) |

---

## Improvement vs Previous Run

Previous run (before crop override tuning): **12 auto-matched / 216**
This run (17 overrides applied): **31 auto-matched / 216**

Improvement: **+19 auto-matches (+158%)**, driven by the crop corrections
restoring full name banners in the affected screenshots.
The override tuning clearly helped OCR: trainer/item cards in IMG_1528,
IMG_1529, IMG_1531, IMG_1535, and IMG_1546 now auto-match at 100%.

---

## Left/Right Separator Offset Assessment

The OCR text output does not show systematic name truncation patterns
(e.g., leading/trailing characters missing from names) that would indicate
left/right boundary clipping. The noise is almost entirely from HP values,
stats, and separator artifacts being included in the name band —
not from cropped-off card name characters.

**Conclusion: slight left/right separator misalignment is NOT harming extraction.**
No further left/right boundary tuning is recommended at this stage.

---

## Top 20 Auto-Matches (score ≥ 80, descending)

| Crop ID | Suggested Name | Score |
|---|---|---|
| IMG_1524_r1c1 | Quick-Grow Extract | 100 |
| IMG_1524_r2c2 | Clemont | 100 |
| IMG_1528_r1c1 | Giovanni | 100 |
| IMG_1528_r1c2 | Sabrina | 100 |
| IMG_1528_r1c3 | Leaf | 100 |
| IMG_1528_r2c2 | Rare Candy | 100 |
| IMG_1528_r2c3 | Lillie | 100 |
| IMG_1528_r3c1 | Giant Cape | 100 |
| IMG_1529_r1c3 | May | 100 |
| IMG_1531_r1c3 | Quick-Grow Extract | 100 |
| IMG_1531_r2c1 | Clemont | 100 |
| IMG_1531_r2c2 | Serena | 100 |
| IMG_1535_r1c1 | Cheren | 100 |
| IMG_1546_r2c1 | Potion | 100 |
| IMG_1546_r2c2 | X Speed | 100 |
| IMG_1546_r3c2 | Poké Ball | 94 |
| IMG_1536_r2c2 | Jigglypuff | 87 |
| IMG_1538_r2c3 | Helioptile | 87 |
| IMG_1535_r2c2 | Shellder | 84 |
| IMG_1525_r1c3 | Riolu | 83 |

---

## 20 Representative Near-Miss / Low-Confidence Examples

These crops score just below the auto-match threshold. The correct card name
is often visible in the raw OCR text — the match fails because of HP values,
quantity chips, and stat text included in the name band. Many are likely
correct and will be quickly confirmable in the review report.

| Crop ID | Best Match Candidate | Best Score | Raw OCR (truncated) |
|---|---|---|---|
| IMG_1543_r2c2 | Electrode | 78 | `' Electrode 90 4` |
| IMG_1529_r3c2 | Magneton | 76 | `-- Magneton 80 4` |
| IMG_1529_r2c3 | Wartortle | 75 | `Wartortlelil 90 cae ane 4` |
| IMG_1532_r2c2 | Poliwhirl | 75 | `Poliwhirl Ln 90 Ca ae hr` |
| IMG_1537_r2c1 | Bulbasaur | 75 | `- Bulbasaur w60 a` |
| IMG_1540_r3c3 | Mawile | 75 | `Mawile w80` |
| IMG_1530_r2c1 | Steelix | 73 | `Steelix w150` |
| IMG_1526_r2c3 | Genesect | 73 | `zz E eee se Genesect 110 PY` |
| IMG_1527_r3c2 | Mienshao | 72 | `--Mienshao sw 80` |
| IMG_1531_r3c2 | Doublade | 72 | `- Doublade ee 90 2 SS eet` |
| IMG_1533_r1c1 | Magneton | 72 | `o'Magneton 904 OO` |
| IMG_1539_r2c3 | Mienshao | 72 | `Mienshao 90 BS 4` |
| IMG_1526_r1c2 | Magnezone | 72 | `a - 7 Magnezone2 1807` |
| IMG_1524_r1c3 | Skrelp | 70 | `3 Skrelp 60 2` |
| IMG_1540_r2c1 | Roselia | 70 | `e Roselia w60 Ta a` |
| IMG_1530_r3c1 | Porygon2 | 69 | `soe Porygon2 90` |
| IMG_1532_r3c1 | Quagsire | 69 | `Quagsire 7 w130` |
| IMG_1526_r3c3 | Budew | 67 | `Budew 30 1` |
| IMG_1530_r2c3 | Ditto | 67 | `ws Ditto w6O ie a` |
| IMG_1527_r2c1 | Urshifu | 43 | `D single Strike Urshifu w 1200` |

---

## Analysis

**Why trainer/item cards match best:** Their name bands contain only the card
name and "TRAINER" label in clean, high-contrast text. No HP or type icons
in the name band. This gives OCR clean input.

**Why Pokémon cards are noisier:** The PTCGP card layout puts the Pokémon name
in a colored band that also contains HP, type icons, and (sometimes) stage
labels. These extra characters appear in the OCR output, reducing fuzzy
match scores even when the name itself is correctly read.

**Empty OCR (47 crops):** Likely full-art, special art, or immersive cards
whose name band has dark/gradient backgrounds that defeat OCR. Also includes
the known empty binder slot (IMG_1547_r3c3). These will need visual review.

**Near-misses are real cards:** The near-miss examples above strongly suggest
that many "needs_review" crops are correctly identified at the OCR stage but
score below threshold due to noise. The review workflow (open review_needed.md,
confirm name) is the right next step — not further OCR tuning.

---

## Recommendation

1. Open `review/review_needed.md` and confirm card names for all 185 flagged crops.
2. For the 31 auto-matched crops: spot-check a sample via contact sheets, then
   treat as confirmed unless visually wrong.
3. After confirmation, create batch files (one per screenshot) using the
   confirmed names + crop manifest as the source of truth.
4. Do NOT further tune OCR parameters unless the review reveals systematic
   misreads across many cards.

**Next prompt:**
> "Read CLAUDE.md completely. Open review/review_needed.md. Begin confirming
> card names for IMG_1524 through IMG_1530 (first 7 screenshots, ~63 crops).
> Create batches/cards_batch_001.json through cards_batch_007.json for those
> screenshots only, following the one-screenshot-per-batch extraction rules."
