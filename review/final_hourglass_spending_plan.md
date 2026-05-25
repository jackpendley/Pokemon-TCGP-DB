# Final Hourglass Spending Plan

Generated: 2026-05-24  
Model confidence: **PZ VERIFIED**  
Collection total: 699 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Fantastical Parade. Batch 2: switch to Lugia (near-complete). Batch 3: Deluxe Pack: ex. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 7.1⧗ (2× batch-1 baseline of 3.5⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Fantastical Parade** | B2 | 120 ⧗ | 34.2617 | 34.0248 | 3.5 | 0.843 | 182 | YES | YES |
| 2 | **Lugia** | A4 | 120 ⧗ | 34.2559 | 34.2072 | 3.5 | 0.800 | 109 | YES | YES |
| 3 | **Deluxe Pack: ex** | A4b | 120 ⧗ | 34.0222 | 33.9108 | 3.5 | 0.929 | 262 | — | YES |

---

### Batch Details

#### Batch 1 — Fantastical Parade (B2)

- **Pack:** Fantastical Parade (Fantastical Parade)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 34.2617
- **New-card EV (10x):** 34.0248
- **Cost per EV unit (⧗/EV):** 3.5 ⧗
- **DR ratio:** 0.843 ← near-complete
- **Missing in pool:** 182
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.843 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Lugia (A4)

- **Pack:** Lugia (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 34.2559
- **New-card EV (10x):** 34.2072
- **Cost per EV unit (⧗/EV):** 3.5 ⧗
- **DR ratio:** 0.800 ← near-complete
- **Missing in pool:** 109
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Deluxe Pack: ex (A4b)

- **Pack:** Deluxe Pack: ex (Deluxe Pack: ex)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 34.0222
- **New-card EV (10x):** 33.9108
- **Cost per EV unit (⧗/EV):** 3.5 ⧗
- **DR ratio:** 0.929
- **Missing in pool:** 262
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

