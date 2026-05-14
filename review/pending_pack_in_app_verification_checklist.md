# Pending Pack In-App Verification Checklist

**Model version:** 0.6.0  
**Date updated:** 2026-05-14  
**Status:** 1 pack remaining at `pending_verification` — A4b (Deluxe Pack: ex) pack unavailable  
**Ho-Oh / Lugia (A4): VERIFIED 2026-05-14** ✅  
**Goal:** Record the branch probabilities and slot rarity tables from the PTCGP app Offering Rates screen, then report them to update the model.

---

## How to Verify In-App

1. Open **Pokémon TCG Pocket** on your device.
2. Tap the **pack** you want to verify (from the pack selection screen).
3. Tap **Pack details** (bottom of screen or info icon).
4. Tap **Offering Rates**.
5. You will see a screen with:
   - **Pack type probabilities** at the top (e.g. "Regular Pack: X%", "Rare Pack: X%", and possibly "Regular Pack +1 Card: X%")
   - **Card slot rarity tables** for each pack type below
6. Screenshot the full screen, or write down every percentage shown.
7. Report the numbers here (or pass them to Claude) to update `pull_probability_model.json`.

**What to look for specifically:**
- Does it show **2 pack types** (Regular + Rare) or **3 pack types** (Regular + Rare + Regular +1 Card)?
- If 3 types, what is the percentage for each?
- In the Regular Pack section: what are the slot 4 and slot 5 rarity percentages?
- In the Rare Pack section: what are all 5 slot rarity percentages?
- If a bonus card / card 6 section appears: what rarities and percentages?

---

## ✅ Pack 1 of 3 — Ho-Oh — VERIFIED 2026-05-14

| Field | Value |
|---|---|
| **Pack name** | Ho-Oh |
| **Expansion** | Wisdom of Sea and Sky |
| **Set code** | A4 |
| **Confidence** | `user_in_app_verified` ✅ |
| **Branch model** | `three_branch` (regular=91.620%, rare=0.050%, regular+1=8.330%) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Wisdom_of_Sea_and_Sky_(TCG_Pocket) |
| **Source** | In-repo screenshots: `Offering Rates screenshots/IMG_1692 2.PNG` – `IMG_1722 2.PNG` |

### Verified rates:

**Branch probabilities:**
| Pack type | Verified rate |
|---|---|
| Regular Pack | **91.620%** ✅ |
| Rare Pack (god pack) | **0.050%** ✅ |
| Regular Pack +1 Card | **8.330%** ✅ |

**Card 6 (Regular Pack +1 Card only) — standard rarity, NOT shiny:**
| Rarity | Verified rate |
|---|---|
| ☆ (one_star) | **12.900%** ✅ |
| 3◆ (three_diamond) | **87.100%** ✅ |

**Slots 1–5:** Match standard third_party_verified rates (unchanged).

---

## ✅ Pack 2 of 3 — Lugia — VERIFIED 2026-05-14 (inferred)

| Field | Value |
|---|---|
| **Pack name** | Lugia |
| **Expansion** | Wisdom of Sea and Sky |
| **Set code** | A4 |
| **Confidence** | `user_in_app_verified` ✅ *(inferred from Ho-Oh — same expansion)* |
| **Branch model** | `three_branch` (regular=91.620%, rare=0.050%, regular+1=8.330%) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Wisdom_of_Sea_and_Sky_(TCG_Pocket) |

> **Note:** Lugia rates are inferred from Ho-Oh (A4) screenshots. No direct Lugia Offering Rates screenshot was captured. To fully confirm independently, open the Lugia pack in-app and verify the rates match Ho-Oh.

---

## ⏳ Pack 3 of 3 — Deluxe Pack: ex — STILL PENDING

| Field | Value |
|---|---|
| **Pack name** | Deluxe Pack: ex |
| **Expansion** | Deluxe Pack: ex |
| **Set code** | A4b |
| **Current confidence** | `pending_verification` — pack UNAVAILABLE in app |
| **Current branch model** | `two_branch` (placeholder — UNCONFIRMED) |
| **Card pool** | 379 cards (no shared pool — pack-specific only) |
| **Cards per pack** | **4 cards** (non-standard; confirmed from IMG_1723) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Deluxe_Pack:_ex_(TCG_Pocket) |
| **Status** | Pack shows "This booster pack cannot be obtained right now." Offering Rates screen inaccessible. |

> **Action required when pack becomes available:** Open PTCGP → Deluxe Pack: ex → Pack details → Offering Rates. Record all branch type rows shown (this pack may have a non-standard model). Note that this pack uses 4 cards/pack, not the standard 5.

---

## What Happens After You Report the Rates

Once you provide the numbers from the app:

1. The model will be updated in `data/reference/pull_probability_model.json`:
   - `slot_rates.confidence` → `user_in_app_verified` (or `user_in_app_verified_plus_bulbapedia` if Bulbapedia now accessible)
   - `slot_model.branch_model` → correct branch type
   - Rates corrected if they differ from placeholder
   - `stale_model_warning` removed

2. All downstream scripts will be re-run:
   ```bash
   python3 scripts/build_pull_probability_model.py
   python3 scripts/validate_pull_probability_model.py
   python3 scripts/build_pack_ev.py
   python3 scripts/generate_pack_recommendation_report.py
   python3 scripts/generate_hourglass_spending_plan.py
   ```

3. EV rankings may shift — especially for Wisdom of Sea and Sky packs (Ho-Oh/Lugia) if they turn out to be three-branch like B-series.

4. `review/in_app_rate_verification.md` and `data/current/in_app_rate_verification.json` will be updated.

---

## Quick Reference — Known Confirmed Rates

For comparison when reading the app screen:

| Expansion type | Branch model | Regular % | Rare % | +1 Card % |
|---|---|---|---|---|
| A-series (confirmed) | two_branch | 99.950% | 0.050% | — |
| B-series standard | three_branch | 94.711% | 0.050% | 5.238% |
| Secluded Springs (A4a) | three_branch | 91.620% | 0.050% | 8.330% |
| Mega Shine (B2b) | four_branch | 94.706% | 0.050% | 5.238% | + Themed Rare 0.005% |

If A4 shows **99.950% / 0.050%** → two_branch (matches A-series pattern, placeholder is correct).  
If A4 shows **94.711% / 0.050% / 5.238%** → three_branch (matches B-series, placeholder is wrong).  
If A4 shows different numbers entirely → unique case, record exactly.

---

*Generated by Pokemon-TCGP-DB project. Do not edit manually — re-run if packs are verified.*
