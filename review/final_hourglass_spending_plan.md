# Final Hourglass Spending Plan

Generated: 2026-05-31  
Model confidence: **PZ VERIFIED**  
Collection total: 886 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Extradimensional Crisis. Batch 2: switch to Mega Altaria (near-complete). Batch 3: Fantastical Parade. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 5.4⧗ (2× batch-1 baseline of 2.7⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Extradimensional Crisis** | A3a | 120 ⧗ | 44.8652 | 44.8183 | 2.7 | 0.794 | 84 | YES | YES |
| 2 | **Mega Altaria** | B1 | 120 ⧗ | 44.3517 | 44.3005 | 2.7 | 0.853 | 105 | — | YES |
| 3 | **Fantastical Parade** | B2 | 120 ⧗ | 43.7241 | 43.6178 | 2.8 | 0.899 | 172 | — | YES |

---

### Batch Details

#### Batch 1 — Extradimensional Crisis (A3a)

- **Pack:** Extradimensional Crisis (Extradimensional Crisis)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 44.8652
- **New-card EV (10x):** 44.8183
- **Cost per EV unit (⧗/EV):** 2.7 ⧗
- **DR ratio:** 0.794 ← near-complete
- **Missing in pool:** 84
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.794 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Mega Altaria (B1)

- **Pack:** Mega Altaria (Mega Rising)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 44.3517
- **New-card EV (10x):** 44.3005
- **Cost per EV unit (⧗/EV):** 2.7 ⧗
- **DR ratio:** 0.853
- **Missing in pool:** 105
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Fantastical Parade (B2)

- **Pack:** Fantastical Parade (Fantastical Parade)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 43.7241
- **New-card EV (10x):** 43.6178
- **Cost per EV unit (⧗/EV):** 2.8 ⧗
- **DR ratio:** 0.899
- **Missing in pool:** 172
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

