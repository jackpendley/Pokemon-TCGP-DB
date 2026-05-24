# Final Hourglass Spending Plan

Generated: 2026-05-23  
Model confidence: **PZ VERIFIED**  
Collection total: 682 cards  
Batch size: 10 packs per batch  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Summary Table

| Scenario | Batches | Total packs | Top pack |
|---|---|---|---|
| Conservative | 1 | 10 | Extradimensional Crisis |
| Moderate | 3 | 30 | Extradimensional Crisis |
| Aggressive | 4 | 40 | Extradimensional Crisis |
| Deck_priority | 1 | 10 | Extradimensional Crisis |

---

## Conservative Scenario

**Description:** Open 1 batch (10 packs) from the highest adj-EV pack only. Stop immediately after. Verify slot rates in-app before any further resource commitment.

**Rationale:** Rates are pz_verified — per-card drop chances sourced directly from Pokemon Zone for all packs. One batch at the top adj-EV pack captures maximum expected value per 10 packs. Re-run after the batch to account for collection changes.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | STOP after this batch regardless of results. Do not open fur… | ✅ |

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 87
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

**Rationale:** Rates are pz_verified — no confidence haircut applied. Prioritizes collection expansion at the highest expected value. Re-run after 20 packs prevents over-committing to a pack whose EV has dropped as new cards were pulled. Switching to #2 after re-run hedges against pool depletion.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | Pause after this batch. Count new unique cards acquired from… | — |
| 2 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | STOP after this batch. Re-run EV calculator — 20 packs opene… | ✅ |
| 3 | Mega Altaria | B1 | 10 | 4.1339 | 41.34 | 115 | Stop after batch 3 and re-assess. If a deck target was pulle… | ✅ |

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 87
- **Stopping condition:** Pause after this batch. Count new unique cards acquired from this pool.

#### Batch 2 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _EV per pack is lower than batch 1 — cards already acquired reduce the effective pool. Actual expected value for this batch is less than the static estimate._
- **Missing cards in pool:** 87
- **Stopping condition:** STOP after this batch. Re-run EV calculator — 20 packs opened from this pool.
- **Re-run required:** 20 packs from same pool. EV will have dropped. Re-run before continuing.

#### Batch 3 — Mega Altaria (B1)

- **Pack:** Mega Altaria (Mega Rising)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1339
- **Estimated batch value:** 41.34  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 115
- **Stopping condition:** Stop after batch 3 and re-assess. If a deck target was pulled, re-run EV. If top pack changed after re-run, adjust batch 4 accordingly.
- **Re-run required:** Switching packs after re-run. Re-run EV to confirm rankings after collection update.

### Re-run checklist

- [ ] After batch 2: re-run python3 scripts/build_pack_ev.py.
- [ ] Check if top1 pack is still the highest adj-EV. If not, update batch 3 target.
- [ ] After batch 3: re-run python3 scripts/generate_hourglass_spending_plan.py to update this plan.
- [ ] If a deck target is completed after any batch: re-run python3 scripts/build_pack_ev.py.

---

## Aggressive Scenario

**Description:** Open 4 batches across the top 3 adj-EV packs . Re-run EV after every 20+ packs from the same pool. Rates are pz_verified — no confidence haircut applied. Maximum resource commitment.

**Rationale:** Maximizes collection expansion rate by rotating across the top EV packs, avoiding diminishing returns on a single pool. A deck-target batch is included for chase deck progress. Higher resource commitment — verify in-app rates as early as possible to lock in confidence.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | Pause after batch 1. Count new cards from this pool. | — |
| 2 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | STOP after batch 2 and re-run EV calculator. 20 packs opened… | ✅ |
| 3 | Mega Altaria | B1 | 10 | 4.1339 | 41.34 | 115 | Pause after switching to pack #2. First batch from new pool. | — |
| 4 | Lugia | A4 | 10 | 4.1167 | 41.17 | 109 | Pause after switching to pack #3. First batch from new pool. | — |

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 87
- **Stopping condition:** Pause after batch 1. Count new cards from this pool.

#### Batch 2 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _EV lower than batch 1 — cards already acquired reduce the pool._
- **Missing cards in pool:** 87
- **Stopping condition:** STOP after batch 2 and re-run EV calculator. 20 packs opened from this pool.
- **Re-run required:** 20 packs from same pool. Re-run EV before committing further.

#### Batch 3 — Mega Altaria (B1)

- **Pack:** Mega Altaria (Mega Rising)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1339
- **Estimated batch value:** 41.34  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 115
- **Stopping condition:** Pause after switching to pack #2. First batch from new pool.

#### Batch 4 — Lugia (A4)

- **Pack:** Lugia (Wisdom of Sea and Sky)
- **Packs to open:** 10
- **Adj EV per pack:** 4.1167
- **Estimated batch value:** 41.17  
  _First batch from this pool — estimate is at current collection state. Actual EV decreases as new cards are acquired._
- **Missing cards in pool:** 109
- **Stopping condition:** Pause after switching to pack #3. First batch from new pool.

### Re-run checklist

- [ ] After batch 2 (20 packs from top1 pool): re-run python3 scripts/build_pack_ev.py.
- [ ] After completing any deck target: re-run python3 scripts/build_pack_ev.py.
- [ ] After verifying in-app rates: upgrade confidence and re-run both EV scripts.
- [ ] After resolving 59 ambiguous collection entries: re-run for more accurate coverage.

---

## Deck_priority Scenario

**Description:** Open 1 batch from the pack with the highest deck_weighted_score (Extradimensional Crisis). Prioritizes completing a chase deck over raw collection expansion.

**Rationale:** deck_weighted_score = adj_ev + 10 × deck_target_ev. The 10× multiplier gives chase-card pull probability significant weight, so a pack with a lower overall EV can outrank a pure collection-expansion pack when it contains an urgently needed chase card. Stop after 1 batch and re-run — completing a chase deck changes the score immediately.

### Batches

| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |
|---|---|---|---|---|---|---|---|---|
| 1 | Extradimensional Crisis | A3a | 10 | 4.2043 | 42.04 | 87 | STOP after this batch. Check if any chase deck card was pull… | ✅ |

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Packs to open:** 10
- **Adj EV per pack:** 4.2043
- **Estimated batch value:** 42.04  
  _deck_weighted_score=4.2043 (adj_ev=4.2043 + 10× deck_target_ev=0.0000). Overall adj_ev may be lower than pure collection-expansion packs._
- **Missing cards in pool:** 87
- **Stopping condition:** STOP after this batch. Check if any chase deck card was pulled. Re-run EV calculator before deciding on batch 2.
- **Re-run required:** Chase deck target may have been acquired — re-run EV to update deck_weighted_score.

### Re-run checklist

- [ ] After batch 1: check if any chase deck card was pulled.
- [ ] Re-run python3 scripts/build_pack_ev.py to update deck_target_ev and deck_weighted_score.
- [ ] Re-run python3 scripts/generate_hourglass_spending_plan.py to refresh this plan.
- [ ] If Incineroar ex pulled: Incineroar ex deck becomes buildable — remove from chase targets.
- [ ] If Ivysaur pulled (2nd copy): Mega Venusaur ex deck may now be buildable.
- [ ] If Magnezone ex pulled: Magnezone ex deck becomes buildable — remove from chase targets.
- [ ] Note: Zygarde ex is PROMO-B only — cannot be obtained from packs.

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
- **adj_ev** = pack_total_ev × confidence_weight (1.0 for pz_verified — no haircut). At verified confidence the weight becomes 1.0 and all adj_ev values will increase.
- **Deck-target EV** is included in adj_ev for packs containing chase deck cards. Crimson Blaze has the highest deck_target_ev per pack.
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.
