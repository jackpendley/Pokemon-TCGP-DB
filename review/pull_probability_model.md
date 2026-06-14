# Pull Probability Model

> **Bulbapedia branch-verified model (v0.5.0, 2026-05-13).**
> Branch selection probabilities verified per-pack from Bulbapedia Offering Rates sections.
> B-series packs corrected to three/four-branch. A-series packs confirmed two-branch.
> Pulsing Aura (B3) is user_in_app_verified_plus_bulbapedia.
> `rarity_probabilities` = exact expected copies of each rarity per pack, summed per pack from Pokémon Zone per-card drop chances (slot-model fallback only when PZ data is absent).
> Bulbapedia is a third-party wiki, NOT official in-app verification.

## Status

| Metric | Value |
|---|---|
| Model version | 0.6.0 |
| Source status | **third_party_verified_with_in_app_anchor** |
| Total packs modeled | 25 |
| Packs user_in_app_verified_plus_bulbapedia | 1 (Pulsing Aura B3) |
| Packs bulbapedia_branch_verified | 12 |
| Packs third_party_verified (two-branch, pattern consistent) | 9 |
| Packs pending_verification | 1 (A4/A4b) |
| rarity_probabilities | **PZ-exact** — expected copies of each rarity per pack from Pokémon Zone drop chances |

## Branch Model by Pack

| Pack | Set | Branch Model | Regular % | Plus-One % | Rare % | Themed % | Confidence |
|---|---|---|---|---|---|---|---|
| Lunala | A3 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Solgaleo | A3 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Crimson Blaze | B1a | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Deluxe Pack: ex | A4b | two_branch | 99.950% | — | 0.050% | — | pending_verification |
| Eevee Grove | A3b | two_branch | 99.950% | — | 0.050% | — | bulbapedia_branch_verified |
| Extradimensional Crisis | A3a | two_branch | 99.950% | — | 0.050% | — | bulbapedia_branch_verified |
| Fantastical Parade | B2 | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Charizard | A1 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Mewtwo | A1 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Pikachu | A1 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Mega Altaria | B1 | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Mega Blaziken | B1 | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Mega Gyarados | B1 | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Mega Shine | B2b | four_branch | 94.706% | 5.238% | 0.050% | 0.005% | bulbapedia_branch_verified |
| Mew | A1a | two_branch | 99.950% | — | 0.050% | — | bulbapedia_branch_verified |
| Paldean Wonders | B2a | three_branch | 94.711% | 5.238% | 0.050% | — | bulbapedia_branch_verified |
| Paradox Drive | B3a | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Pulsing Aura | B3 | three_branch | 94.711% | 5.238% | 0.050% | — | user_in_app_verified_plus_bulbapedia |
| Secluded Springs | A4a | three_branch | 91.620% | 8.330% | 0.050% | — | bulbapedia_branch_verified |
| Shining Revelry | A2b | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Dialga | A2 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Palkia | A2 | two_branch | 99.950% | — | 0.050% | — | third_party_verified |
| Arceus | A2a | two_branch | 99.950% | — | 0.050% | — | bulbapedia_branch_verified |
| Ho-Oh | A4 | three_branch | 91.620% | 8.330% | 0.050% | — | user_in_app_verified |
| Lugia | A4 | three_branch | 91.620% | 8.330% | 0.050% | — | user_in_app_verified |

## Pack Pool Summary

| Pack | Expansion | Set | Pool Total | 1◆ | 2◆ | 3◆ | 4◆ | ☆ | ☆☆ | ☆☆☆ |
|---|---|---|---|---|---|---|---|---|---|---|
| Lunala | Celestial Guardians | A3 | 140 | 44 | 34 | 14 | 5 | 12 | 9 | 1 |
| Solgaleo | Celestial Guardians | A3 | 140 | 44 | 34 | 14 | 5 | 12 | 9 | 1 |
| Crimson Blaze | Crimson Blaze | B1a | 103 | 32 | 24 | 8 | 5 | 6 | 7 | 1 |
| Deluxe Pack: ex | Deluxe Pack: ex | A4b | 379 | 128 | 100 | 50 | 75 | 6 | 18 | 1 |
| Eevee Grove | Eevee Grove | A3b | 107 | 32 | 23 | 8 | 6 | 10 | 8 | 1 |
| Extradimensional Crisis | Extradimensional Crisis | A3a | 103 | 32 | 24 | 8 | 5 | 6 | 8 | 1 |
| Fantastical Parade | Fantastical Parade | B2 | 234 | 66 | 51 | 28 | 10 | 24 | 14 | 2 |
| Charizard | Genetic Apex | A1 | 127 | 50 | 35 | 14 | 5 | 8 | 8 | 2 |
| Mewtwo | Genetic Apex | A1 | 126 | 50 | 35 | 14 | 5 | 8 | 7 | 2 |
| Pikachu | Genetic Apex | A1 | 127 | 50 | 35 | 14 | 5 | 8 | 9 | 2 |
| Mega Altaria | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 8 | 7 | 1 |
| Mega Blaziken | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 8 | 7 | 1 |
| Mega Gyarados | Mega Rising | B1 | 139 | 49 | 33 | 15 | 5 | 8 | 7 | 1 |
| Mega Shine | Mega Shine | B2b | 117 | 33 | 23 | 8 | 5 | 6 | 9 | 2 |
| Mew | Mythical Island | A1a | 86 | 32 | 23 | 8 | 5 | 6 | 8 | 1 |
| Paldean Wonders | Paldean Wonders | B2a | 131 | 43 | 32 | 13 | 5 | 6 | 10 | 1 |
| Paradox Drive | Paradox Drive | B3a | 109 | 32 | 25 | 12 | 5 | 6 | 8 | 1 |
| Pulsing Aura | Pulsing Aura | B3 | 234 | 65 | 51 | 29 | 10 | 24 | 17 | 2 |
| Secluded Springs | Secluded Springs | A4a | 105 | 32 | 23 | 11 | 5 | 6 | 8 | 1 |
| Shining Revelry | Shining Revelry | A2b | 111 | 32 | 22 | 9 | 9 | 6 | 13 | 1 |
| Dialga | Space-Time Smackdown | A2 | 126 | 46 | 34 | 14 | 5 | 12 | 8 | 1 |
| Palkia | Space-Time Smackdown | A2 | 126 | 44 | 36 | 14 | 5 | 12 | 8 | 1 |
| Arceus | Triumphant Light | A2a | 96 | 31 | 26 | 13 | 5 | 6 | 9 | 1 |
| Ho-Oh | Wisdom of Sea and Sky | A4 | 136 | 42 | 31 | 17 | 5 | 12 | 8 | 1 |
| Lugia | Wisdom of Sea and Sky | A4 | 136 | 42 | 31 | 17 | 5 | 12 | 8 | 1 |

## How to Upgrade to Verified

1. Open the Pokémon TCG Pocket app.
2. Navigate to the pack you want to verify.
3. View the **Offering Rates** section (disclosed in-app).
4. Compare branch percentages to `slot_rates` in `data/reference/pull_probability_model.json`.
5. Update `slot_rates`, set `confidence: 'verified'`, bump model_version.
6. Re-run `python3 scripts/validate_pull_probability_model.py`.

## rarity_probabilities Status

`rarity_probabilities[r]` = exact expected number of cards of rarity *r* opened per pack,
summed independently per pack from Pokémon Zone per-card drop chances (`pz_pack_odds.json`)
joined to `card_reference` rarity. A slot-model approximation is used only when a pack
has no PZ data. Values are expected counts (e.g. common ~2.9/pack), not [0,1] probabilities.

