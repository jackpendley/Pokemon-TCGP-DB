# Final Hourglass Spending Plan

Generated: 2026-05-12  
Model confidence: **THIRD PARTY VERIFIED WITH IN APP ANCHOR**  
Collection total: 584 cards  
Batch size: 10 packs per batch  

> **DISCLAIMER**
>
> IMPORTANT — NOT OFFICIAL: Slot rates are third_party_verified (confirmed by 4 independent sources: Game8, ONE Esports, CGMagazine, ShackNews) but NOT officially verified from the in-app Offering Rates screen. EV calculations are for planning purposes only. Do not treat these as guaranteed outcomes. Verify slot rates in PTCGP app (any pack → Pack details → Offering Rates) before committing large resources.

---

## Summary Table

| Scenario | Batches | Total packs | Top pack |
|---|---|---|---|
| Conservative | 1 | 10 | Paldean Wonders |
| Moderate | 3 | 30 | Paldean Wonders |
| Aggressive | 5 | 50 | Paldean Wonders |

---

## Conservative Scenario

**Description:** Open 1 batch (10 packs) from the highest adj-EV pack only. Stop immediately after. Verify slot rates in-app before any further resource commitment.

**Rationale:** Rates are third_party_verified — confirmed across 4 independent sources but not from the official in-app Offering Rates screen. One batch at the top adj-EV pack captures maximum expected value per 10 packs while keeping total exposure minimal. In-app verification takes ~5 minutes and could confirm or revise rankings.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Paldean Wonders | B2a | 10 | 4.1663 | 41.66 | 127 | STOP after this batch regardless of results. Do not open fur… | ✅ |

#### Batch 1 — Paldean Wonders (B2a)

- **Pack:** Paldean Wonders (Paldean Wonders)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1663
- **Estimated batch value:** 41.66  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 127
- **Stopping condition:** STOP after this batch regardless of results. Do not open further packs until slot rates are verified in PTCGP app.
- **Re-run required:** Mandatory post-conservative check: open PTCGP app → any pack → Pack details → Offering Rates. If rates match model, upgrade to verified confidence.

### Re-run checklist

- [ ] After batch 1: open PTCGP app → any pack → Pack details → Offering Rates.
- [ ] Compare displayed percentages to slot_rates in data/reference/pull_probability_model.json.
- [ ] If they match: update confidence=verified in the model JSON, then re-run python3 scripts/build_pack_ev.py.
- [ ] Re-run python3 scripts/generate_hourglass_spending_plan.py to refresh this plan at verified confidence.

---

## Moderate Scenario

**Description:** Open 3 batches: 2 from the top adj-EV pack, then 1 from the #2 adj-EV pack. Re-run the EV calculator after batch 2 (20 packs from same pool). Stop after each batch to check progress.

**Rationale:** Accepts third_party_verified confidence risk (~15% adjustment applied to all EVs). Prioritizes collection expansion at the highest expected value. Re-run after 20 packs prevents over-committing to a pack whose EV has dropped as new cards were pulled. Switching to #2 after re-run hedges against pool depletion.

**Deck-target variant:** Deck-target variant: if completing a specific chase deck is the priority goal, replace batch 3 with Mewtwo (Genetic Apex, adj_ev=3.1501, deck_target_ev=0.2856). This pack has the highest deck_target_ev per 10 packs. Note: overall adj_ev is lower than the top collection-expansion packs.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Paldean Wonders | B2a | 10 | 4.1663 | 41.66 | 127 | Pause after this batch. Count new unique cards acquired from… | — |
| 2 | Paldean Wonders | B2a | 10 | 4.1663 | 41.66 | 127 | STOP after this batch. Re-run EV calculator — 20 packs opene… | ✅ |
| 3 | Lunala | A3 | 10 | 3.6588 | 36.59 | 114 | Stop after batch 3 and re-assess. If a deck target was pulle… | ✅ |

#### Batch 1 — Paldean Wonders (B2a)

- **Pack:** Paldean Wonders (Paldean Wonders)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1663
- **Estimated batch value:** 41.66  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 127
- **Stopping condition:** Pause after this batch. Count new unique cards acquired from this pool.

#### Batch 2 — Paldean Wonders (B2a)

- **Pack:** Paldean Wonders (Paldean Wonders)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1663
- **Estimated batch value:** 41.66  
  _EV per pack is lower than batch 1 — cards already acquired reduce the effective pool. Actual expected value for this batch is less than the static estimate._
- **Missing cards in pool:** 127
- **Stopping condition:** STOP after this batch. Re-run EV calculator — 20 packs opened from this pool.
- **Re-run required:** 20 packs from same pool. EV will have dropped. Re-run before continuing.

#### Batch 3 — Lunala (A3)

- **Pack:** Lunala (Celestial Guardians)
- **Packs to open:** 10
- **Adj EV per pack:** 3.6588
- **Estimated batch value:** 36.59  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 114
- **Stopping condition:** Stop after batch 3 and re-assess. If a deck target was pulled, re-run EV. If top pack changed after re-run, adjust batch 4 accordingly.
- **Re-run required:** Switching packs after re-run. Re-run EV to confirm rankings after collection update.

### Re-run checklist

- [ ] After batch 2: re-run python3 scripts/build_pack_ev.py.
- [ ] Check if top1 pack is still the highest adj-EV. If not, update batch 3 target.
- [ ] After batch 3: re-run python3 scripts/generate_hourglass_spending_plan.py to update this plan.
- [ ] If a deck target is completed after any batch: re-run python3 scripts/build_pack_ev.py.

---

## Aggressive Scenario

**Description:** Open 5 batches across the top 3 adj-EV packs plus the top deck-target pack (Mewtwo). Re-run EV after every 20+ packs from the same pool. Accept third_party_verified confidence risk on all decisions.

**Rationale:** Maximizes collection expansion rate by rotating across the top EV packs, avoiding diminishing returns on a single pool. A deck-target batch is included for chase deck progress. Higher resource commitment — verify in-app rates as early as possible to lock in confidence.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Paldean Wonders | B2a | 10 | 4.1663 | 41.66 | 127 | Pause after batch 1. Count new cards from this pool. | — |
| 2 | Paldean Wonders | B2a | 10 | 4.1663 | 41.66 | 127 | STOP after batch 2 and re-run EV calculator. 20 packs opened… | ✅ |
| 3 | Lunala | A3 | 10 | 3.6588 | 36.59 | 114 | Pause after switching to pack #2. First batch from new pool. | — |
| 4 | Extradimensional Crisis | A3a | 10 | 3.6448 | 36.45 | 88 | Pause after switching to pack #3. First batch from new pool. | — |
| 5 | Mewtwo | A1 | 10 | 3.1501 | 31.50 | 79 | Deck-target batch: Mewtwo has highest deck_target_ev per pac… | ✅ |

#### Batch 1 — Paldean Wonders (B2a)

- **Pack:** Paldean Wonders (Paldean Wonders)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1663
- **Estimated batch value:** 41.66  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 127
- **Stopping condition:** Pause after batch 1. Count new cards from this pool.

#### Batch 2 — Paldean Wonders (B2a)

- **Pack:** Paldean Wonders (Paldean Wonders)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1663
- **Estimated batch value:** 41.66  
  _EV lower than batch 1 — cards already acquired reduce the pool._
- **Missing cards in pool:** 127
- **Stopping condition:** STOP after batch 2 and re-run EV calculator. 20 packs opened from this pool.
- **Re-run required:** 20 packs from same pool. Re-run EV before committing further.

#### Batch 3 — Lunala (A3)

- **Pack:** Lunala (Celestial Guardians)
- **Packs to open:** 10
- **Adj EV per pack:** 3.6588
- **Estimated batch value:** 36.59  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 114
- **Stopping condition:** Pause after switching to pack #2. First batch from new pool.

#### Batch 4 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 3.6448
- **Estimated batch value:** 36.45  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 88
- **Stopping condition:** Pause after switching to pack #3. First batch from new pool.

#### Batch 5 — Mewtwo (A1)

- **Pack:** Mewtwo (Genetic Apex)
- **Packs to open:** 10
- **Adj EV per pack:** 3.1501
- **Estimated batch value:** 31.50  
  _deck_target_ev=0.2856 — per-pack deck completion value._
- **Missing cards in pool:** 79
- **Stopping condition:** Deck-target batch: Mewtwo has highest deck_target_ev per pack. Stop immediately if chase deck card is pulled.
- **Re-run required:** Final aggressive batch. Re-run EV for updated plan after deck-target batch.

### Re-run checklist

- [ ] After batch 2 (20 packs from top1 pool): re-run python3 scripts/build_pack_ev.py.
- [ ] After completing any deck target: re-run python3 scripts/build_pack_ev.py.
- [ ] After verifying in-app rates: upgrade confidence and re-run both EV scripts.
- [ ] After resolving 59 ambiguous collection entries: re-run for more accurate coverage.

---

## Global Re-run Checklist

Run these at any time they apply, regardless of scenario:

- [ ] After every 20+ pack opens from the same pool: re-run python3 scripts/build_pack_ev.py
- [ ] After completing any deck target: re-run python3 scripts/build_pack_ev.py (deck_target_ev drops to zero)
- [ ] After official in-app rate verification: set confidence=verified and re-run python3 scripts/build_pack_ev.py
- [ ] After resolving 59 ambiguous collection entries: re-run python3 scripts/build_pack_ev.py for more accurate coverage
- [ ] After any new expansion releases: re-run python3 scripts/build_pull_probability_model.py then python3 scripts/build_pack_ev.py
- [ ] After updating collection.json with new cards: re-run python3 scripts/normalize_current_collection.py then python3 scripts/build_pack_ev.py

---

## Notes

- **Expected value per batch** is a rough estimate at current collection state. Actual EV decreases as you acquire cards from the same pool.
- **No hourglass cost is assumed.** Hourglasses are a resource you manage in-game; this plan specifies which packs and how many, not how many hourglasses to spend.
- **adj_ev** = pack_total_ev × confidence_weight (0.85 for third_party_verified). At verified confidence the weight becomes 1.0 and all adj_ev values will increase.
- **Deck-target EV** is included in adj_ev for packs containing chase deck cards. Crimson Blaze has the highest deck_target_ev per pack.
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.
