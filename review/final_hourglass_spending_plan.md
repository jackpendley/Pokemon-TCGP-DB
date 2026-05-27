# Final Hourglass Spending Plan

Generated: 2026-05-26  
Model confidence: **PZ VERIFIED**  
Collection total: 747 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Deluxe Pack: ex. Batch 2: continue Deluxe Pack: ex. Batch 3: Ho-Oh. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 7.3⧗ (2× batch-1 baseline of 3.7⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Deluxe Pack: ex** | A4b | 120 ⧗ | 32.7969 | 32.6830 | 3.7 | 0.929 | 251 | — | YES |
| 2 | **Deluxe Pack: ex** | A4b | 120 ⧗ | 32.7969 | 32.6830 | 3.7 | 0.929 | 251 | — | YES |
| 3 | **Ho-Oh** | A4 | 120 ⧗ | 32.6495 | 32.6044 | 3.7 | 0.800 | 102 | YES | YES |

---

### Batch Details

#### Batch 1 — Deluxe Pack: ex (A4b)

- **Pack:** Deluxe Pack: ex (Deluxe Pack: ex)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 32.7969
- **New-card EV (10x):** 32.6830
- **Cost per EV unit (⧗/EV):** 3.7 ⧗
- **DR ratio:** 0.929
- **Missing in pool:** 251
- **Notes:** Open first batch from the top unified-score pack.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Deluxe Pack: ex (A4b)

- **Pack:** Deluxe Pack: ex (Deluxe Pack: ex)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 32.7969
- **New-card EV (10x):** 32.6830
- **Cost per EV unit (⧗/EV):** 3.7 ⧗
- **DR ratio:** 0.929
- **Missing in pool:** 251
- **Notes:** Continue top pack for batch 2.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Ho-Oh (A4)

- **Pack:** Ho-Oh (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 32.6495
- **New-card EV (10x):** 32.6044
- **Cost per EV unit (⧗/EV):** 3.7 ⧗
- **DR ratio:** 0.800 ← near-complete
- **Missing in pool:** 102
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

