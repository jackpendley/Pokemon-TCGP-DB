# In-App Rate Verification Record

Generated: 2026-05-13  
Source: User-provided in-app Offering Rates screenshots  
Machine-readable: `data/current/in_app_rate_verification.json`

---

## Coverage

| Pack | Set | Status | Date | Source |
|---|---|---|---|---|
| Pulsing Aura | B3 | **user_in_app_verified** | 2026-05-13 | ChatGPT conversation (not in repo) |

---

## Important Note on Source

The user manually verified Pulsing Aura's Offering Rates directly in the Pokémon TCG Pocket app and provided the values in a ChatGPT conversation. **Screenshots are not stored in this repository.** These values are treated as authoritative user-provided in-app evidence.

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
