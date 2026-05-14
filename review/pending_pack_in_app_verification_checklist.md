# Pending Pack In-App Verification Checklist

**Model version:** 0.5.0  
**Date generated:** 2026-05-13  
**Status:** 3 packs at `pending_verification` — branch model unconfirmed  
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

## Pack 1 of 3 — Ho-Oh

| Field | Value |
|---|---|
| **Pack name** | Ho-Oh |
| **Expansion** | Wisdom of Sea and Sky |
| **Set code** | A4 |
| **Current confidence** | `pending_verification` |
| **Current branch model** | `two_branch` (placeholder — UNCONFIRMED) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Wisdom_of_Sea_and_Sky_(TCG_Pocket) |
| **Bulbapedia status** | `truncated_pending` — page was inaccessible during 2026-05-13 verification pass |

### Current placeholder rates in model (NOT confirmed):

**Branch probabilities:**
| Pack type | Current placeholder |
|---|---|
| Regular Pack | 99.950% |
| Rare Pack (god pack) | 0.050% |
| Regular Pack +1 Card | _(not modeled — two-branch placeholder)_ |

**Slots 1–3 (both pack types):**
| Rarity | Rate |
|---|---|
| 1◆ (one_diamond) | 100.000% |

**Slot 4 (Regular Pack):**
| Rarity | Current placeholder |
|---|---|
| 2◆ (two_diamond) | 90.000% |
| 3◆ (three_diamond) | 5.000% |
| 4◆ (four_diamond) | 1.666% |
| ☆ (one_star) | 2.572% |
| ☆☆ (double_star) | 0.500% |
| ☆☆☆ (triple_star) | 0.222% |
| ♛ (crown) | 0.040% |

**Slot 5 (Regular Pack):**
| Rarity | Current placeholder |
|---|---|
| 2◆ (two_diamond) | 60.000% |
| 3◆ (three_diamond) | 20.000% |
| 4◆ (four_diamond) | 6.664% |
| ☆ (one_star) | 10.288% |
| ☆☆ (double_star) | 2.000% |
| ☆☆☆ (triple_star) | 0.888% |
| ♛ (crown) | 0.160% |

**All 5 slots (Rare Pack / God Pack):**
| Rarity | Current placeholder |
|---|---|
| ☆ (one_star) | 40.000% |
| ☆☆ (double_star) | 50.000% |
| ☆☆☆ (triple_star) | 5.000% |
| ♛ (crown) | 5.000% |

### What to record from app:

```
Ho-Oh pack — Offering Rates screen:

Branch probabilities:
  Regular Pack:             _______ %
  Rare Pack:                _______ %
  Regular Pack +1 Card:     _______ %  (write "not shown" if absent)

Slot 4 rarity table (Regular Pack):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Slot 5 rarity table (Regular Pack):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Rare Pack all-slot table:
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Bonus card / Card 6 section:
  Shown? (yes/no): _______
  If yes — rarity and rates:
  ______________________
```

---

## Pack 2 of 3 — Lugia

| Field | Value |
|---|---|
| **Pack name** | Lugia |
| **Expansion** | Wisdom of Sea and Sky |
| **Set code** | A4 |
| **Current confidence** | `pending_verification` |
| **Current branch model** | `two_branch` (placeholder — UNCONFIRMED) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Wisdom_of_Sea_and_Sky_(TCG_Pocket) |
| **Bulbapedia status** | `truncated_pending` — same page as Ho-Oh, inaccessible during verification pass |

> **Note:** Ho-Oh and Lugia are both A4 packs from the same expansion. They likely share the same branch model and slot rarity tables, only differing in card pool. You only need to record the rates once from either pack — but verifying both is ideal to confirm they match.

### Current placeholder rates in model (NOT confirmed):

Same as Ho-Oh above — identical placeholder rates.

### What to record from app:

```
Lugia pack — Offering Rates screen:

Branch probabilities:
  Regular Pack:             _______ %
  Rare Pack:                _______ %
  Regular Pack +1 Card:     _______ %  (write "not shown" if absent)

Slot 4 rarity table (Regular Pack):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Slot 5 rarity table (Regular Pack):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Rare Pack all-slot table:
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Bonus card / Card 6 section:
  Shown? (yes/no): _______
  If yes — rarity and rates:
  ______________________

Do rates match Ho-Oh? (yes/no): _______
```

---

## Pack 3 of 3 — Deluxe Pack: ex

| Field | Value |
|---|---|
| **Pack name** | Deluxe Pack: ex |
| **Expansion** | Deluxe Pack: ex |
| **Set code** | A4b |
| **Current confidence** | `pending_verification` |
| **Current branch model** | `two_branch` (placeholder — UNCONFIRMED) |
| **Card pool** | 379 cards (no shared pool — pack-specific only) |
| **Bulbapedia page** | https://bulbapedia.bulbagarden.net/wiki/Deluxe_Pack:_ex_(TCG_Pocket) |
| **Bulbapedia status** | `truncated_pending` — page was inaccessible during 2026-05-13 verification pass |
| **Special note** | "Deluxe Pack" is a different product type — may have a non-standard branch model or different rarity table. Verify carefully. |

### Current placeholder rates in model (NOT confirmed):

Same placeholder rates as A4 packs above (copied from two-branch standard scaffold).

### What to record from app:

> **Pay special attention:** The Deluxe Pack: ex may show a different structure from normal expansion packs. If it shows additional pack type rows (e.g. a "Themed Pack" or numbered card bonus), record all of them.

```
Deluxe Pack: ex — Offering Rates screen:

Branch probabilities (record ALL rows shown):
  Row 1 name:    _________________  _______ %
  Row 2 name:    _________________  _______ %
  Row 3 name:    _________________  _______ %  (if present)
  Row 4 name:    _________________  _______ %  (if present)

Slot 4 rarity table (Regular Pack or equivalent):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Slot 5 rarity table (Regular Pack or equivalent):
  2◆:   _______ %
  3◆:   _______ %
  4◆:   _______ %
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Rare Pack / God Pack all-slot table:
  ☆:    _______ %
  ☆☆:   _______ %
  ☆☆☆:  _______ %
  ♛:    _______ %

Bonus card / Card 6 section (or any additional slot tables):
  Shown? (yes/no): _______
  If yes — rarity and rates:
  ______________________

Any other section not listed above?
  ______________________
```

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
