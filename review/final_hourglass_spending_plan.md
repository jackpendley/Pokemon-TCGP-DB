# Final Hourglass Spending Plan

Generated: 2026-06-15  
Model confidence: **THIRD PARTY VERIFIED WITH IN APP ANCHOR**  
Collection total: 1293 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Ho-Oh. Batch 2: switch to Lugia (near-complete). Batch 3: Secluded Springs. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 4.0⧗ (2× batch-1 baseline of 2.0⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Ho-Oh** | A4 | 120 ⧗ | 60.1096 | 60.0855 | 2.0 | 0.841 | 131 | YES | YES |
| 2 | **Lugia** | A4 | 120 ⧗ | 58.7878 | 58.7382 | 2.0 | 0.847 | 126 | YES | YES |
| 3 | **Secluded Springs** | A4a | 120 ⧗ | 58.6307 | 58.6307 | 2.0 | 0.792 | 105 | YES | YES |

---

### Batch Details

#### Batch 1 — Ho-Oh (A4)

- **Pack:** Ho-Oh (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 60.1096
- **New-card EV (10x):** 60.0855
- **Cost per EV unit (⧗/EV):** 2.0 ⧗
- **DR ratio:** 0.841 ← near-complete
- **Missing in pool:** 131
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.841 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Lugia (A4)

- **Pack:** Lugia (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 58.7878
- **New-card EV (10x):** 58.7382
- **Cost per EV unit (⧗/EV):** 2.0 ⧗
- **DR ratio:** 0.847 ← near-complete
- **Missing in pool:** 126
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Secluded Springs (A4a)

- **Pack:** Secluded Springs (Secluded Springs)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 58.6307
- **New-card EV (10x):** 58.6307
- **Cost per EV unit (⧗/EV):** 2.0 ⧗
- **DR ratio:** 0.792 ← near-complete
- **Missing in pool:** 105
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted (ultra_rare=10.0 … uncommon=0.0). deck_target_ev is 0 until deck targets are configured.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

