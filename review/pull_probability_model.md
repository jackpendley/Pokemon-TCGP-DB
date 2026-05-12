# Pull Probability Model

> **Scaffold only — pull rates are NOT populated.**
> All `rarity_probabilities` values are `null`.
> Card pool counts (how many cards of each rarity exist per pack) are from `pack_sources.json`.
> Pull rates must come from the official in-app Offering Rates screen.

## Status

| Metric | Value |
|---|---|
| Model version | 0.1.0-scaffold |
| Source status | **scaffold_only** |
| Verified source | None — rates unverified |
| Total packs modeled | 24 |
| Probability values | **all null** |

## How to Populate Pull Rates

1. Open the Pokémon TCG Pocket app.
2. Navigate to the pack you want to record.
3. View the **Offering Rates** / **Card Rates** section (disclosed in-app).
4. Record the per-rarity probability for the pack.
5. Populate `rarity_probabilities` in `data/reference/pull_probability_model.json`.
6. Set `confidence: 'verified'` and `source_name: 'ptcgp_in_app_offering_rates'`.
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

## Probability Rates Status

All rarity probability values are currently `null`.
The following rates are required per pack before pack EV can be computed:

- `one_diamond` — probability that a card slot contains a 1-diamond rarity card
- `two_diamond` — 2-diamond
- `three_diamond` — 3-diamond (rare)
- `four_diamond` — 4-diamond (ex Pokémon)
- `one_star` — full-art / illustration rare
- `double_star` — special-art / shiny
- `triple_star` — immersive / rainbow
- `crown` — crown / gold (if applicable)

> **Do not estimate or infer these rates.** Use only the official in-app Offering Rates.

## Rarity Field Mapping

Rarity names in this model match `pack_sources.json`:

| Field | Meaning |
|---|---|
| `one_diamond` | Common (◆) |
| `two_diamond` | Uncommon (◆◆) |
| `three_diamond` | Rare (◆◆◆) |
| `four_diamond` | EX / Ultra Rare (◆◆◆◆) |
| `one_star` | Full Art / Illustration Rare (☆) |
| `double_star` | Special Art / Shiny (☆☆) |
| `triple_star` | Immersive / Rainbow (☆☆☆) |
| `crown` | Crown / Gold |
| `promo` | Promo card |

