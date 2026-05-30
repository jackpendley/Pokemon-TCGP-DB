# Final Hourglass Spending Plan

Generated: 2026-05-29  
Model confidence: **PZ VERIFIED**  
Collection total: 859 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Extradimensional Crisis. Batch 2: switch to Mega Altaria (near-complete). Batch 3: Lunala. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 7.6⧗ (2× batch-1 baseline of 3.8⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Extradimensional Crisis** | A3a | 120 ⧗ | 31.5625 | 31.5156 | 3.8 | 0.749 | 84 | YES | YES |
| 2 | **Mega Altaria** | B1 | 120 ⧗ | 31.4215 | 31.1909 | 3.9 | 0.790 | 105 | YES | YES |
| 3 | **Lunala** | A3 | 120 ⧗ | 31.3025 | 31.2576 | 3.8 | 0.809 | 107 | YES | YES |

---

### Batch Details

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 31.5625
- **New-card EV (10x):** 31.5156
- **Cost per EV unit (⧗/EV):** 3.8 ⧗
- **DR ratio:** 0.749 ← near-complete
- **Missing in pool:** 84
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.749 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Mega Altaria (B1)

- **Pack:** Mega Altaria (Mega Rising)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 31.4215
- **New-card EV (10x):** 31.1909
- **Cost per EV unit (⧗/EV):** 3.9 ⧗
- **DR ratio:** 0.790 ← near-complete
- **Missing in pool:** 105
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Lunala (A3)

- **Pack:** Lunala (Celestial Guardians)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 31.3025
- **New-card EV (10x):** 31.2576
- **Cost per EV unit (⧗/EV):** 3.8 ⧗
- **DR ratio:** 0.809 ← near-complete
- **Missing in pool:** 107
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

