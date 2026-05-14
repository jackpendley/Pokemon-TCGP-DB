# In-App Rate Verification Record

Generated: 2026-05-14  
Source: User-provided in-app Offering Rates screenshots  
Machine-readable: `data/current/in_app_rate_verification.json`

---

## Coverage

| Pack | Set | Status | Date | Source |
|---|---|---|---|---|
| Ho-Oh | A4 | **user_in_app_verified** | 2026-05-14 | In-repo screenshots (`Offering Rates screenshots/IMG_1692–IMG_1722`) |
| Lugia | A4 | **user_in_app_verified** *(inferred)* | 2026-05-14 | Inferred from Ho-Oh — same expansion |
| Pulsing Aura | B3 | **user_in_app_verified** | 2026-05-13 | ChatGPT conversation (not in repo) |

---

## Important Note on Sources

**Ho-Oh / Lugia (A4, 2026-05-14):** In-app Offering Rates screenshots captured directly from the PTCGP app and stored in the repository under `Offering Rates screenshots/` (31 PNG files, IMG_1692–IMG_1722; gitignored, not committed). Ho-Oh verified directly; Lugia rates are inferred from the shared expansion.

**Pulsing Aura (B3, 2026-05-13):** The user manually verified Pulsing Aura's Offering Rates in the app and provided the values in a ChatGPT conversation. **Screenshots are not stored in this repository.** These values are treated as authoritative user-provided in-app evidence.

**A4b (Deluxe Pack: ex):** Pack was unavailable in app ("cannot be obtained right now"). Offering Rates screen is inaccessible. Pack uses 4 cards/pack (non-standard). Remains `pending_verification`.

---

## Ho-Oh / Lugia (A4) — User In-App Verified Rates

### Pack Branch Selection

| Branch | Probability | Display | Screenshot |
|---|---|---|---|
| Regular pack | 91.620% | 91.620% | IMG_1692 2.PNG |
| Rare pack | 0.050% | 0.050% | IMG_1705 2.PNG |
| Regular pack + 1 card | 8.330% | 8.330% | IMG_1709 2.PNG |
| **Sum** | **100.000%** | | |

### Model Correction

The prior placeholder was **two-branch** (regular=99.950%, rare=0.050%). Correct model is **three-branch**. Branch probabilities match Secluded Springs (A4a) exactly.

### Regular Pack — Slot Model

| Slot | Rarity | Probability |
|---|---|---|
| Cards 1–3 | ♦ (one_diamond) | 100.000% each |
| Card 4 | ♦♦ (two_diamond) | 90.000% |
| Card 4 | ♦♦♦ (three_diamond) | 5.000% |
| Card 4 | ♦♦♦♦ (four_diamond) | 1.666% |
| Card 4 | ☆ (one_star) | 2.572% |
| Card 4 | ☆☆ (double_star) | 0.500% |
| Card 4 | ☆☆☆ (triple_star) | 0.222% |
| Card 4 | Crown | 0.040% |
| Card 5 | ♦♦ (two_diamond) | 60.000% |
| Card 5 | ♦♦♦ (three_diamond) | 20.000% |
| Card 5 | ♦♦♦♦ (four_diamond) | 6.664% |
| Card 5 | ☆ (one_star) | 10.288% |
| Card 5 | ☆☆ (double_star) | 2.000% |
| Card 5 | ☆☆☆ (triple_star) | 0.888% |
| Card 5 | Crown | 0.160% |

**Note:** Slots 1–5 rates match the prior third_party_verified standard model.

### Rare Pack Distribution

Standard 40/50/5/5 tier placeholder retained. Screenshots (IMG_1705–1708) show apparent uniform distribution (~2.564% = 1/39 pool cards). Pending explicit confirmation before updating.

### Regular Pack + 1 Card — Card 6 (Standard Rarity — NOT Shiny)

**Key finding: A4 card 6 uses standard rarity, unlike Pulsing Aura (B3) which uses shiny rarity.**

| Rarity | Probability | Example cards | Screenshot |
|---|---|---|---|
| ☆ (one_star) | 12.900% | Magby | IMG_1722 2.PNG |
| ♦♦♦ (three_diamond) | 87.100% | Magby, Smoochum, Tyrogue | IMG_1722 2.PNG |

Card 6 EV contribution is included in model (cards are in pack_sources.json as standard rarities).

---

---

## Pulsing Aura (B3) — User In-App Verified Rates

### Pack Branch Selection

| Branch | Probability | Display |
|---|---|---|
| Regular pack | 94.711% | 94.711% |
| Rare pack | 0.050% | 0.050% |
| Regular pack + 1 card | 5.238% | 5.238% |
| **Sum** | **99.999%** | *(rounding from app display)* |

### Model Correction

The prior model (third_party_verified from Game8/ONE Esports/CGMagazine/ShackNews) modeled only two branches:
- Regular pack: 99.950%
- Rare pack: 0.050%

The correct Pulsing Aura model has **three branches**. The old regular_pack probability of 99.950% was effectively the sum of what should be regular_pack (94.711%) + regular_pack_plus_one (5.238%) = 99.949%.

### Regular Pack — Slot Model

| Slot | Rarity | Probability |
|---|---|---|
| Cards 1–3 | ♦ (one_diamond) | 100.000% each |
| Card 4 | ♦♦ (two_diamond) | 90.000% |
| Card 4 | ♦♦♦ (three_diamond) | 5.000% |
| Card 4 | ♦♦♦♦ (four_diamond) | 1.667% |
| Card 4 | ☆ (one_star) | 2.572% |
| Card 4 | ☆☆ (double_star) | 0.500% |
| Card 4 | ☆☆☆ (triple_star) | 0.222% |
| Card 4 | Crown | 0.040% |
| Card 5 | ♦♦ (two_diamond) | ~60.000% (59.998% displayed) |
| Card 5 | ♦♦♦ (three_diamond) | 20.000% |
| Card 5 | ♦♦♦♦ (four_diamond) | 6.667% |
| Card 5 | ☆ (one_star) | 10.286% |
| Card 5 | ☆☆ (double_star) | 2.000% |
| Card 5 | ☆☆☆ (triple_star) | 0.889% |
| Card 5 | Crown | 0.160% |

**Note:** Slots 1–5 rates match the prior third_party_verified model within display rounding.

### Rare Pack — Corrected Distribution

**Old model (INCORRECT for Pulsing Aura):** ☆=40%, ☆☆=50%, ☆☆☆=5%, Crown=5%

| Rarity | Old | Corrected |
|---|---|---|
| ☆ (one_star) | 40.000% | **47.058%** |
| ☆☆ (double_star) | 50.000% | **45.098%** |
| ☆☆☆ (triple_star) | 5.000% | **3.921%** |
| Crown / highest | 5.000% | **3.921%** |

### Regular Pack + 1 Card — Card 6 (Shiny Only)

| Rarity | Probability | Note |
|---|---|---|
| ☆S (one_shiny) | 68.180% | Shiny Art Rare — separate from standard ☆ |
| ☆☆S (two_shiny) | 31.820% | Shiny Super Rare |

Card 6 rates are distinct from the standard one_star/double_star in slots 4–5. Shiny cards are **not currently in pack_sources.json**, so card 6 EV is pending addition of shiny pool data.

---

## External Source Search Results

A comprehensive search for external sources matching the three-branch model (94.711% / 0.050% / 5.238%) and corrected rare pack rates (47.058% / 45.098% / 3.921%) was conducted on 2026-05-13.

| Source | Match | Notes |
|---|---|---|
| Game8 (game8.co) | ❌ No match | Reports old 40/50/5/5 rare pack; does not mention three-branch model |
| ONE Esports (oneesports.gg) | ❌ No match | No updated rare pack rates found |
| CGMagazine (cgmagonline.com) | ❌ No match | Confirms old universality claim; does not reflect Pulsing Aura correction |
| ShackNews | ❌ No match | Reports old slot rates only |
| Bulbapedia | ❌ No match | Card rarity descriptions only; no rates |
| PTCGPocket.gg | ❌ No match | Reports old 40/50/5/5 explicitly |
| Dexerto | ❌ No match | Per-card rates only; no branch model |
| GamesRadar | ❌ No match | Shiny card list only; no rates |

**Conclusion:** No reputable external source found that documents the three-branch model or corrected Pulsing Aura rates. Per project policy, Pulsing Aura (B3) is corrected using user-provided in-app evidence only. All other packs retain the prior third_party_verified model with a `stale_model_warning` noting the model may be missing the `regular_pack_plus_one` branch.

---

## Decision: Generalization Scope

| Pack group | Action |
|---|---|
| Pulsing Aura (B3) | Full three-branch model applied, `user_in_app_verified` |
| All other packs | Retain prior two-branch model; add `stale_model_warning` |

Generalization to other packs is **not supported** until in-app verification or a matching reputable external source is found for each pack.
