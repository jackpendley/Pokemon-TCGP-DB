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

**3-batch plan rotating through top unified-score packs. Batch 1: Fantastical Parade. Batch 2: switch to Lugia (near-complete). Batch 3: Palkia. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 7.9⧗ (2× batch-1 baseline of 3.9⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/card | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Fantastical Parade** | B2 | 120 ⧗ | 30.7320 | 30.4951 | 3.9 | 0.756 | 182 | YES | YES |
| 2 | **Lugia** | A4 | 120 ⧗ | 30.5900 | 30.5413 | 3.9 | 0.714 | 109 | YES | YES |
| 3 | **Palkia** | A2 | 120 ⧗ | 30.5367 | 30.5065 | 3.9 | 0.727 | 104 | YES | YES |

---

### Batch Details

#### Batch 1 — Fantastical Parade (B2)

- **Pack:** Fantastical Parade (Fantastical Parade)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 30.7320
- **New-card EV (10x):** 30.4951
- **Cost per unique card:** 3.9 ⧗
- **DR ratio:** 0.756 ← near-complete
- **Missing in pool:** 182
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.756 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Lugia (A4)

- **Pack:** Lugia (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 30.5900
- **New-card EV (10x):** 30.5413
- **Cost per unique card:** 3.9 ⧗
- **DR ratio:** 0.714 ← near-complete
- **Missing in pool:** 109
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Palkia (A2)

- **Pack:** Palkia (Space-Time Smackdown)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 30.5367
- **New-card EV (10x):** 30.5065
- **Cost per unique card:** 3.9 ⧗
- **DR ratio:** 0.727 ← near-complete
- **Missing in pool:** 104
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/card** = `120 ⧗ / new_card_ev_10x`. Lower is better.
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

