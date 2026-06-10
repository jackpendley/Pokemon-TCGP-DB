# Final Hourglass Spending Plan

Generated: 2026-06-09  
Model confidence: **THIRD PARTY VERIFIED WITH IN APP ANCHOR**  
Collection total: 1145 cards  
Batch size: 10 packs (120 ⧗ per batch)  

> **DISCLAIMER**
>
> NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from Pokemon Zone (not the official PTCGP in-app Offering Rates screen). EV calculations reflect actual pull probabilities with no confidence haircut applied. Rankings are suitable for planning. Re-run EV after every 20+ packs to account for collection changes.

---

## Optimal Spending Plan

**3-batch plan rotating through top unified-score packs. Batch 1: Lugia. Batch 2: switch to Ho-Oh (near-complete). Batch 3: Solgaleo. Always rerun EV after each batch.**

- Total batches: 3
- Total hourglasses: 360 ⧗
- Rerun EV after batch(es): [1, 2, 3]
- Stopping condition: Stop any batch when cost_per_unique_card_10x exceeds 3.9⧗ (2× batch-1 baseline of 1.9⧗). Re-run EV before committing further.

| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Lugia** | A4 | 120 ⧗ | 61.6441 | 61.6236 | 1.9 | 0.844 | 131 | YES | YES |
| 2 | **Ho-Oh** | A4 | 120 ⧗ | 61.1274 | 61.1144 | 2.0 | 0.839 | 133 | YES | YES |
| 3 | **Solgaleo** | A3 | 120 ⧗ | 59.3978 | 59.3964 | 2.0 | 0.841 | 139 | YES | YES |

---

### Batch Details

#### Batch 1 — Lugia (A4)

- **Pack:** Lugia (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 61.6441
- **New-card EV (10x):** 61.6236
- **Cost per EV unit (⧗/EV):** 1.9 ⧗
- **DR ratio:** 0.844 ← near-complete
- **Missing in pool:** 131
- **Notes:** Open first batch from the top unified-score pack. WARNING: DR ratio=0.844 < 0.85 — this pool is near-complete; switch to #2 after this batch.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 2 — Ho-Oh (A4)

- **Pack:** Ho-Oh (Wisdom of Sea and Sky)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 61.1274
- **New-card EV (10x):** 61.1144
- **Cost per EV unit (⧗/EV):** 2.0 ⧗
- **DR ratio:** 0.839 ← near-complete
- **Missing in pool:** 133
- **Notes:** Switched to #2 pack (near-complete flag on batch 1).
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

#### Batch 3 — Solgaleo (A3)

- **Pack:** Solgaleo (Celestial Guardians)
- **Hourglasses:** 120 ⧗ (10 packs × 12 ⧗)
- **Unified score:** 59.3978
- **New-card EV (10x):** 59.3964
- **Cost per EV unit (⧗/EV):** 2.0 ⧗
- **DR ratio:** 0.841 ← near-complete
- **Missing in pool:** 139
- **Notes:** Re-run EV after this batch; rotate to highest unified-score pack for batch 4.
- **Rerun after:** YES — re-run build_pack_ev.py before next batch

---

## Notes

- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted (ultra_rare=10.0 … uncommon=0.0). deck_target_ev is 0 until deck targets are configured.
- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below 0.85: pool near-complete, diminishing returns significant.
- **⧗/EV** = `120 ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)
- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.

