# Pull Probability Model

> **Scaffold only — pull rates are NOT populated.**
> All `rarity_probabilities` values are `null`.
> Card pool counts (how many cards of each rarity exist per pack) are from `pack_sources.json`.
> Pull rates must come from the official in-app Offering Rates screen.

## Status

| Metric | Value |
|---|---|
| Model version | 0.4.0 |
| Source status | **in_app_verified_partial** |
| Inferred source | None |
| Verified source | None |
| Third-party verified sources | game8_co, one_esports_gg, cgmagonline_com, shacknews_com |
| Total packs modeled | 24 |
| Packs with third_party_verified rates | 23 |
| Packs with inferred slot rates | 0 |
| Packs with verified rates | 0 |
| rarity_probabilities values | **all null** (aggregate rates not yet verified) |

## How to Upgrade to Verified

1. Open the Pokémon TCG Pocket app.
2. Navigate to the pack you want to verify.
3. View the **Offering Rates** / **Card Rates** section (disclosed in-app).
4. Compare the in-app rates to `slot_rates` in `data/reference/pull_probability_model.json`.
5. If they match, set `confidence: 'verified'` and populate `rarity_probabilities`.
6. If they differ, update `slot_rates` with the correct values and set `confidence: 'verified'`.
7. Re-run `python3 scripts/validate_pull_probability_model.py`.

## Pack Pool Summary

| Pack | Expansion | Set | Pool Total | 1◆ | 2◆ | 3◆ | 4◆ | ☆ | ☆☆ | ☆☆☆ |
|---|---|---|---|---|---|---|---|---|---|---|
| Lunala | Celestial Guardians | A3 | 140 | 44 | 34 | 14 | 5 | 22 | 18 | 1 |
| Solgaleo | Celestial Guardians | A3 | 140 | 44 | 34 | 14 | 5 | 22 | 18 | 1 |
| Crimson Blaze | Crimson Blaze | B1a | 103 | 32 | 24 | 8 | 5 | 16 | 15 | 1 |
| Deluxe Pack: ex | Deluxe Pack: ex | A4b | 379 | 128 | 100 | 50 | 75 | 6 | 18 | 1 |
| Eevee Grove | Eevee Grove | A3b | 107 | 32 | 23 | 8 | 6 | 19 | 17 | 1 |
| Extradimensional Crisis | Extradimensional Crisis | A3a | 103 | 32 | 24 | 8 | 5 | 16 | 16 | 1 |
| Fantastical Parade | Fantastical Parade | B2 | 234 | 66 | 51 | 28 | 10 | 44 | 31 | 2 |
| Charizard | Genetic Apex | A1 | 127 | 50 | 35 | 14 | 5 | 8 | 10 | 2 |
| Mewtwo | Genetic Apex | A1 | 126 | 50 | 35 | 14 | 5 | 8 | 9 | 2 |
| Pikachu | Genetic Apex | A1 | 127 | 50 | 35 | 14 | 5 | 8 | 10 | 2 |
| Mega Altaria | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 18 | 15 | 1 |
| Mega Blaziken | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 18 | 15 | 1 |
| Mega Gyarados | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 18 | 15 | 1 |
| Mega Shine | Mega Shine | B2b | 117 | 33 | 23 | 8 | 5 | 30 | 14 | 2 |
| Mew | Mythical Island | A1a | 86 | 32 | 23 | 8 | 5 | 6 | 10 | 1 |
| Paldean Wonders | Paldean Wonders | B2a | 131 | 43 | 33 | 12 | 5 | 16 | 19 | 1 |
| Pulsing Aura | Pulsing Aura | B3 | 234 | 65 | 51 | 29 | 10 | 44 | 31 | 2 |
| Secluded Springs | Secluded Springs | A4a | 105 | 32 | 23 | 11 | 5 | 16 | 16 | 1 |
| Shining Revelry | Shining Revelry | A2b | 111 | 32 | 22 | 9 | 9 | 16 | 21 | 1 |
| Dialga | Space-Time Smackdown | A2 | 126 | 46 | 34 | 14 | 5 | 12 | 12 | 1 |
| Palkia | Space-Time Smackdown | A2 | 126 | 44 | 36 | 14 | 5 | 12 | 12 | 1 |
| Arceus | Triumphant Light | A2a | 96 | 31 | 26 | 13 | 5 | 6 | 13 | 1 |
| Ho-Oh | Wisdom of Sea and Sky | A4 | 136 | 42 | 31 | 17 | 5 | 22 | 16 | 1 |
| Lugia | Wisdom of Sea and Sky | A4 | 136 | 42 | 31 | 17 | 5 | 22 | 16 | 1 |

## rarity_probabilities Status

All aggregate `rarity_probabilities` values are currently `null`.
These represent P(at least one card of this rarity in a 5-card pack).
They will be computed once slot_rates are verified from in-app Offering Rates.

## Rarity Field Mapping

| Field | Meaning |
|---|---|
| `one_diamond` | Common (◆) |
| `two_diamond` | Uncommon (◆◆) |
| `three_diamond` | Rare (◆◆◆) |
| `four_diamond` | EX / Ultra Rare (◆◆◆◆) |
| `one_star` | Full Art / Illustration Rare (☆) |
| `double_star` | Special Art (☆☆) |
| `triple_star` | Immersive / Rainbow (☆☆☆) |
| `crown` | Crown / Gold |
| `promo` | Promo card |

