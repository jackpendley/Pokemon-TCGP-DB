# Final Hourglass Spending Plan

Generated: 2026-05-28  
Model confidence: **PZ VERIFIED**  
Collection total: 784 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Deluxe Pack: ex. Batch 2: continue Deluxe Pack: ex. Batch 3: Mega Altaria. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 7.5⧗ (2× batch-1 baseline of 3.7⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Deluxe Pack: ex** | A4b | 120 ⧗ | 32.1860 | 32.0729 | 3.7 | 0.929 | 246 | — | YES |
| 2 | **Deluxe Pack: ex** | A4b | 120 ⧗ | 32.1860 | 32.0729 | 3.7 | 0.929 | 246 | — | YES |
| 3 | **Mega Altaria** | B1 | 120 ⧗ | 31.8823 | 31.6517 | 3.8 | 0.790 | 106 | YES | YES |

---

### Batch Details

#### Batch 1 — Deluxe Pack: ex (A4b)

- **Pack:** Deluxe Pack: ex (Deluxe Pack: ex)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 32.1860
- **New-card EV (10x):** 32.0729
- **Cost per EV unit (⧗/EV):** 3.7 ⧗
- **DR ratio:** 0.929
- **Missing in pool:** 246
- **Notes:** Open first batch from the top unified-score pack.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Deluxe Pack: ex (A4b)

- **Pack:** Deluxe Pack: ex (Deluxe Pack: ex)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 32.1860
- **New-card EV (10x):** 32.0729
- **Cost per EV unit (⧗/EV):** 3.7 ⧗
- **DR ratio:** 0.929
- **Missing in pool:** 246
- **Notes:** Continue top pack for batch 2.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Mega Altaria (B1)

- **Pack:** Mega Altaria (Mega Rising)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 31.8823
- **New-card EV (10x):** 31.6517
- **Cost per EV unit (⧗/EV):** 3.8 ⧗
- **DR ratio:** 0.790 ← near-complete
- **Missing in pool:** 106
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

