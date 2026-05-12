# Current Collection Pack-Source Review

This package lists cards from `collection.json` that cannot be automatically assigned
to a pack because they appear in multiple expansions or are not in `pack_sources.json`.

**Fill in `data/exports/current_pack_source_review.csv`** to confirm which set/card number
each card belongs to. Then apply with:

```bash
python3 scripts/apply_current_pack_confirmations.py --dry-run
python3 scripts/apply_current_pack_confirmations.py --apply
```

## How to Check Set/Card Number

1. Open the Pokémon TCG Pocket app.
2. Go to your card collection.
3. Tap the card you want to identify.
4. The set code and card number appear at the bottom of the card detail view.
   - Format: `A1/001`, `B3/124`, etc.
5. Enter `confirmed_set_code` (e.g., `A1`) and `confirmed_card_number` (e.g., `1`).
6. Set `confirmed_yes_no` to `yes`.

## Summary

| Status | Count |
|---|---|
| Ambiguous (cross-expansion) | 59 |
| Ambiguous (same expansion, different pack) | 0 |
| No match in pack_sources | 3 |
| Known trainer gap (not in Limitless) | 5 |
| **Total needing review** | **67** |

## Priority 1 — Chase Deck Targets

Resolve these first for pack EV recommendations.

### Marowak ex (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 140
- **Attack:** Bonemerang 80+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 153 | Genetic Apex | Mewtwo | four_diamond | https://pocket.limitlesstcg.com/cards/A1/153 |
| A1 | 264 | Genetic Apex | Mewtwo | double_star | https://pocket.limitlesstcg.com/cards/A1/264 |
| A3 | 236 | Celestial Guardians | Lunala | double_star | https://pocket.limitlesstcg.com/cards/A3/236 |
| A4b | 196 | Deluxe Pack: ex | Deluxe Pack: ex | four_diamond | https://pocket.limitlesstcg.com/cards/A4b/196 |

### Moltres ex (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 140
- **Attack:** Heat Blast 70 / Inferno Dance
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 47 | Genetic Apex | Charizard | four_diamond | https://pocket.limitlesstcg.com/cards/A1/47 |
| A1 | 255 | Genetic Apex | Charizard | double_star | https://pocket.limitlesstcg.com/cards/A1/255 |
| A1 | 274 | Genetic Apex | Charizard | double_star | https://pocket.limitlesstcg.com/cards/A1/274 |
| A3b | 103 | Eevee Grove | Eevee Grove | double_star | https://pocket.limitlesstcg.com/cards/A3b/103 |
| A4b | 67 | Deluxe Pack: ex | Deluxe Pack: ex | four_diamond | https://pocket.limitlesstcg.com/cards/A4b/67 |

### Zygarde ex (×1)

- **Status:** `no_match`
- **Type:** Fighting
- **HP:** 170
- **Attack:** Land Laser 100+
- **Recommended action:** `needs_reference_expansion`

_No candidates found in pack_sources._

### Ivysaur (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 100
- **Attack:** Synthesis
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A4b | 3 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/3 |
| A4b | 4 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/4 |
| B1a | 2 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/2 |


## Priority 2 — EX Cards

None.

## Priority 3 — Trainer/Supporter Staples

### Cyrus (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Supporter
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A2 | 150 | Space-Time Smackdown | Palkia | two_diamond | https://pocket.limitlesstcg.com/cards/A2/150 |
| A2 | 190 | Space-Time Smackdown | Palkia | double_star | https://pocket.limitlesstcg.com/cards/A2/190 |
| A4b | 326 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/326 |
| A4b | 327 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/327 |

### Giant Cape (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Pokemon Tool
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A2 | 147 | Space-Time Smackdown | Dialga | two_diamond | https://pocket.limitlesstcg.com/cards/A2/147 |
| A4b | 320 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/320 |
| A4b | 321 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/321 |

### Giovanni (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Supporter
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 223 | Genetic Apex | Mewtwo | two_diamond | https://pocket.limitlesstcg.com/cards/A1/223 |
| A1 | 270 | Genetic Apex | Mewtwo | double_star | https://pocket.limitlesstcg.com/cards/A1/270 |
| A4b | 334 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/334 |
| A4b | 335 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/335 |

### Leaf (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Supporter
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1a | 68 | Mythical Island | Mew | two_diamond | https://pocket.limitlesstcg.com/cards/A1a/68 |
| A1a | 82 | Mythical Island | Mew | double_star | https://pocket.limitlesstcg.com/cards/A1a/82 |
| A4b | 346 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/346 |
| A4b | 347 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/347 |

### Lillie (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Supporter
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A3 | 155 | Celestial Guardians | Solgaleo | two_diamond | https://pocket.limitlesstcg.com/cards/A3/155 |
| A3 | 197 | Celestial Guardians | Solgaleo | double_star | https://pocket.limitlesstcg.com/cards/A3/197 |
| A3 | 209 | Celestial Guardians | Solgaleo | triple_star | https://pocket.limitlesstcg.com/cards/A3/209 |
| A4b | 348 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/348 |
| A4b | 349 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/349 |
| A4b | 374 | Deluxe Pack: ex | Deluxe Pack: ex | double_star | https://pocket.limitlesstcg.com/cards/A4b/374 |

### Sabrina (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Supporter
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 225 | Genetic Apex | Charizard | two_diamond | https://pocket.limitlesstcg.com/cards/A1/225 |
| A1 | 272 | Genetic Apex | Charizard | double_star | https://pocket.limitlesstcg.com/cards/A1/272 |
| A4b | 338 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/338 |
| A4b | 339 | Deluxe Pack: ex | Deluxe Pack: ex | two_diamond | https://pocket.limitlesstcg.com/cards/A4b/339 |


## Priority 4 — Pokemon Cards

Sorted by name.

### Bewear (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 110
- **Attack:** Triple Smash 50x
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 142 | Mega Rising | Mega Blaziken | two_diamond | https://pocket.limitlesstcg.com/cards/B1/142 |
| B3 | 91 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/91 |

### Blaziken (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 140
- **Attack:** Blaze Kick 100
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 35 | Mega Rising | Mega Blaziken | three_diamond | https://pocket.limitlesstcg.com/cards/B1/35 |
| B3 | 208 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/208 |

### Bulbasaur (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 70
- **Attack:** Vine Whip 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A4b | 1 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/1 |
| A4b | 2 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/2 |
| B1a | 1 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/1 |

### Bulbasaur (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 70
- **Attack:** Vine Whip 40
- **Variant:** alt art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A4b | 1 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/1 |
| A4b | 2 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/2 |
| B1a | 1 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/1 |

### Bulbasaur (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 60
- **Attack:** Tackle 20
- **Variant:** Tackle art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A4b | 1 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/1 |
| A4b | 2 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/2 |
| B1a | 1 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/1 |

### Charmander (×4)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 60
- **Attack:** Bite 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 11 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/11 |
| B2b | 7 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/7 |
| B2b | 91 | Mega Shine | Mega Shine | one_star | https://pocket.limitlesstcg.com/cards/B2b/91 |

### Charmander (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 70
- **Attack:** Flame Tail 30
- **Variant:** Flame Tail art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 11 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/11 |
| B2b | 7 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/7 |
| B2b | 91 | Mega Shine | Mega Shine | one_star | https://pocket.limitlesstcg.com/cards/B2b/91 |

### Charmeleon (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 80
- **Attack:** Slash 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 12 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/12 |
| B2b | 8 | Mega Shine | Mega Shine | two_diamond | https://pocket.limitlesstcg.com/cards/B2b/8 |
| B2b | 92 | Mega Shine | Mega Shine | one_star | https://pocket.limitlesstcg.com/cards/B2b/92 |

### Cherubi (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 50
- **Attack:** Sweets Relay 10+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A2a | 6 | Triumphant Light | Arceus | one_diamond | https://pocket.limitlesstcg.com/cards/A2a/6 |
| A4 | 23 | Wisdom of Sea and Sky | shared pool | one_diamond | https://pocket.limitlesstcg.com/cards/A4/23 |
| A4b | 25 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/25 |
| A4b | 26 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/26 |

### Chewtle (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Water
- **HP:** 80
- **Attack:** Wave Splash 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 76 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/76 |
| B2 | 43 | Fantastical Parade | Fantastical Parade | one_diamond | https://pocket.limitlesstcg.com/cards/B2/43 |

### Cinccino (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 90
- **Attack:** Knock Away 30+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2b | 63 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/63 |
| B3 | 143 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/143 |
| B3 | 179 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/179 |

### Corvisquire (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 80
- **Attack:** Joust 30
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 210 | Mega Rising | Mega Blaziken | two_diamond | https://pocket.limitlesstcg.com/cards/B1/210 |
| B3 | 146 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/146 |

### Darmanitan (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 120
- **Attack:** Double Smash 40+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 40 | Mega Rising | Mega Gyarados | two_diamond | https://pocket.limitlesstcg.com/cards/B1/40 |
| B3 | 30 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/30 |

### Darumaka (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fire
- **HP:** 60
- **Attack:** Headbutt 10
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 39 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/39 |
| B3 | 29 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/29 |

### Doublade (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Metal
- **HP:** 90
- **Attack:** Dual Blades 40+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 171 | Mega Rising | Mega Blaziken | two_diamond | https://pocket.limitlesstcg.com/cards/B1/171 |
| B2 | 119 | Fantastical Parade | Fantastical Parade | two_diamond | https://pocket.limitlesstcg.com/cards/B2/119 |

### Eelektross (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 140
- **Attack:** Thunder Fang 80
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 109 | Genetic Apex | Mewtwo | three_diamond | https://pocket.limitlesstcg.com/cards/A1/109 |
| A4a | 28 | Secluded Springs | Secluded Springs | two_diamond | https://pocket.limitlesstcg.com/cards/A4a/28 |

### Eevee (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 60
- **Attack:** Jumping Kick
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 184 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/184 |
| B3 | 129 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/129 |

### Farfetch'd (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 60
- **Attack:** Leek Slap 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| A1 | 198 | Genetic Apex | shared pool | one_diamond | https://pocket.limitlesstcg.com/cards/A1/198 |
| A3b | 102 | Eevee Grove | Eevee Grove | one_star | https://pocket.limitlesstcg.com/cards/A3b/102 |
| A4a | 56 | Secluded Springs | Secluded Springs | one_diamond | https://pocket.limitlesstcg.com/cards/A4a/56 |
| A4b | 280 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/280 |
| A4b | 281 | Deluxe Pack: ex | Deluxe Pack: ex | one_diamond | https://pocket.limitlesstcg.com/cards/A4b/281 |
| A4b | 359 | Deluxe Pack: ex | Deluxe Pack: ex | one_star | https://pocket.limitlesstcg.com/cards/A4b/359 |

### Frillish (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Water
- **HP:** 60
- **Attack:** Water Gun 20
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 68 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/68 |
| B3 | 209 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/209 |

### Furfrou (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 70
- **Attack:** Tackle 30
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 206 | Mega Rising | Mega Blaziken | two_diamond | https://pocket.limitlesstcg.com/cards/B1/206 |
| B1 | 207 | Mega Rising | Mega Altaria | two_diamond | https://pocket.limitlesstcg.com/cards/B1/207 |
| B1 | 208 | Mega Rising | Mega Gyarados | two_diamond | https://pocket.limitlesstcg.com/cards/B1/208 |
| B1a | 65 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/65 |
| B2 | 141 | Fantastical Parade | Fantastical Parade | two_diamond | https://pocket.limitlesstcg.com/cards/B2/141 |
| B2b | 64 | Mega Shine | Mega Shine | two_diamond | https://pocket.limitlesstcg.com/cards/B2b/64 |
| B3 | 144 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/144 |

### Garbodor (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Darkness
- **HP:** 130
- **Attack:** Acid Spray 70
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 50 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/50 |
| B2b | 42 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/42 |

### Grimer (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Darkness
- **HP:** 80
- **Attack:** Sludge Bomb 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 45 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/45 |
| B3 | 215 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/215 |

### Hariyama (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 120
- **Attack:** Megaton Slap Push 90
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 127 | Mega Rising | Mega Blaziken | two_diamond | https://pocket.limitlesstcg.com/cards/B1/127 |
| B1a | 40 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/40 |

### Herdier (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 90
- **Attack:** Hammer In 50
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 202 | Mega Rising | Mega Altaria | two_diamond | https://pocket.limitlesstcg.com/cards/B1/202 |
| B3 | 138 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/138 |

### Lillipup (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 60
- **Attack:** Puppy Pile 20x
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 201 | Mega Rising | Mega Altaria | one_diamond | https://pocket.limitlesstcg.com/cards/B1/201 |
| B3 | 137 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/137 |

### Magnemite (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 50
- **Attack:** Electro Ball 30
- **Variant:** Electro Ball art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 24 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/24 |
| B3 | 52 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/52 |

### Magnemite (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 60
- **Attack:** Thunder Shock 20
- **Variant:** Thunder Shock art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 24 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/24 |
| B3 | 52 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/52 |

### Magneton (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 80
- **Attack:** Spark 20
- **Variant:** Spark art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 25 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/25 |
| B3 | 53 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/53 |

### Magneton (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 90
- **Attack:** Magnetic Blast 50
- **Variant:** Magnetic Blast art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 25 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/25 |
| B3 | 53 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/53 |

### Makuhita (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 80
- **Attack:** Strength 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 126 | Mega Rising | Mega Blaziken | one_diamond | https://pocket.limitlesstcg.com/cards/B1/126 |
| B1 | 240 | Mega Rising | Mega Blaziken | one_star | https://pocket.limitlesstcg.com/cards/B1/240 |
| B1a | 39 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/39 |

### Meltan (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Metal
- **HP:** 60
- **Attack:** Stampede 10
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 173 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/173 |
| B3 | 122 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/122 |
| B3 | 177 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/177 |

### Minccino (×4)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 50
- **Attack:** Fluffy Tail
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2b | 62 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/62 |
| B3 | 142 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/142 |

### Onix (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 110
- **Attack:** Land Crush 70
- **Variant:** Land Crush art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 38 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/38 |
| B3 | 211 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/211 |

### Onix (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 100
- **Attack:** Dig 30
- **Variant:** Dig art
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 38 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/38 |
| B3 | 211 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/211 |

### Pikachu (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Lightning
- **HP:** 60
- **Attack:** Spark 10
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2 | 49 | Fantastical Parade | Fantastical Parade | one_diamond | https://pocket.limitlesstcg.com/cards/B2/49 |
| B2b | 22 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/22 |
| B2b | 96 | Mega Shine | Mega Shine | one_star | https://pocket.limitlesstcg.com/cards/B2b/96 |

### Poliwhirl (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Water
- **HP:** 90
- **Attack:** Hit Twice 30x
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 296 | Mega Rising | Mega Gyarados | one_star | https://pocket.limitlesstcg.com/cards/B1/296 |
| B3 | 34 | Pulsing Aura | Pulsing Aura | two_diamond | https://pocket.limitlesstcg.com/cards/B3/34 |

### Porygon (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 60
- **Attack:** Stiffen
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 56 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/56 |
| B3 | 222 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/222 |

### Porygon2 (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 90
- **Attack:** Speed Attack 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 57 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/57 |
| B3 | 223 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/223 |

### Ralts (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Psychic
- **HP:** 60
- **Attack:** Confuse Ray
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2 | 63 | Fantastical Parade | Fantastical Parade | one_diamond | https://pocket.limitlesstcg.com/cards/B2/63 |
| B3 | 63 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/63 |

### Rolycoly (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 80
- **Attack:** Rolling Tackle 20
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 145 | Mega Rising | Mega Gyarados | one_diamond | https://pocket.limitlesstcg.com/cards/B1/145 |
| B3 | 92 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/92 |

### Sandshrew (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 70
- **Attack:** Scratch 10
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 122 | Mega Rising | shared pool | one_diamond | https://pocket.limitlesstcg.com/cards/B1/122 |
| B1a | 94 | Crimson Blaze | Crimson Blaze | one_star | https://pocket.limitlesstcg.com/cards/B1a/94 |
| B2 | 77 | Fantastical Parade | Fantastical Parade | one_diamond | https://pocket.limitlesstcg.com/cards/B2/77 |
| B2 | 170 | Fantastical Parade | Fantastical Parade | one_star | https://pocket.limitlesstcg.com/cards/B2/170 |

### Sandslash (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 100
- **Attack:** Slash 70
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 123 | Mega Rising | shared pool | two_diamond | https://pocket.limitlesstcg.com/cards/B1/123 |
| B1a | 95 | Crimson Blaze | Crimson Blaze | one_star | https://pocket.limitlesstcg.com/cards/B1a/95 |
| B2 | 78 | Fantastical Parade | Fantastical Parade | one_diamond | https://pocket.limitlesstcg.com/cards/B2/78 |

### Skrelp (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Darkness
- **HP:** 60
- **Attack:** Razor Fin 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 159 | Mega Rising | Mega Blaziken | one_diamond | https://pocket.limitlesstcg.com/cards/B1/159 |
| B3 | 218 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/218 |

### Steelix (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Metal
- **HP:** 150
- **Attack:** Metal Defender 100
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 51 | Crimson Blaze | Crimson Blaze | two_diamond | https://pocket.limitlesstcg.com/cards/B1a/51 |
| B3 | 219 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/219 |

### Stoutland (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Colorless
- **HP:** 150
- **Attack:** Fighting Fangs 70+
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 203 | Mega Rising | Mega Altaria | three_diamond | https://pocket.limitlesstcg.com/cards/B1/203 |
| B1 | 249 | Mega Rising | Mega Altaria | one_star | https://pocket.limitlesstcg.com/cards/B1/249 |
| B3 | 139 | Pulsing Aura | Pulsing Aura | three_diamond | https://pocket.limitlesstcg.com/cards/B3/139 |

### Stufful (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Fighting
- **HP:** 70
- **Attack:** Tackle 30
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1 | 141 | Mega Rising | Mega Blaziken | one_diamond | https://pocket.limitlesstcg.com/cards/B1/141 |
| B3 | 90 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/90 |

### Tangela (×3)

- **Status:** `ambiguous_cross_set`
- **Type:** Grass
- **HP:** 80
- **Attack:** Bind 20
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2 | 205 | Fantastical Parade | Fantastical Parade | one_star | https://pocket.limitlesstcg.com/cards/B2/205 |
| B3 | 1 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/1 |

### Trubbish (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Darkness
- **HP:** 70
- **Attack:** Drool 30
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B1a | 49 | Crimson Blaze | Crimson Blaze | one_diamond | https://pocket.limitlesstcg.com/cards/B1a/49 |
| B1a | 74 | Crimson Blaze | Crimson Blaze | one_star | https://pocket.limitlesstcg.com/cards/B1a/74 |
| B2b | 41 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/41 |

### Varoom (×1)

- **Status:** `ambiguous_cross_set`
- **Type:** Metal
- **HP:** 70
- **Attack:** Suffocating Gas 40
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2a | 75 | Paldean Wonders | Paldean Wonders | one_diamond | https://pocket.limitlesstcg.com/cards/B2a/75 |
| B2b | 49 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/49 |

### Zorua (×2)

- **Status:** `ambiguous_cross_set`
- **Type:** Darkness
- **HP:** 60
- **Attack:** Ascension
- **Recommended action:** `needs_card_number`

**Candidates:**

| Set | # | Expansion | Pack | Rarity | URL |
|---|---|---|---|---|---|
| B2b | 43 | Mega Shine | Mega Shine | one_diamond | https://pocket.limitlesstcg.com/cards/B2b/43 |
| B2b | 102 | Mega Shine | Mega Shine | one_star | https://pocket.limitlesstcg.com/cards/B2b/102 |
| B3 | 105 | Pulsing Aura | Pulsing Aura | one_diamond | https://pocket.limitlesstcg.com/cards/B3/105 |
| B3 | 174 | Pulsing Aura | Pulsing Aura | one_star | https://pocket.limitlesstcg.com/cards/B3/174 |

### Zygarde 10% Forme (×1)

- **Status:** `no_match`
- **Type:** Fighting
- **HP:** 80
- **Attack:** Bite 30
- **Recommended action:** `needs_reference_expansion`

_No candidates found in pack_sources._

### Zygarde 50% Forme (×3)

- **Status:** `no_match`
- **Type:** Fighting
- **HP:** 120
- **Attack:** Cell Storm 60
- **Recommended action:** `needs_reference_expansion`

_No candidates found in pack_sources._


## Known Trainer Gaps (Not in Limitless DB)

These common trainer items are not indexed in Limitless TCG Pocket.
They cannot be confirmed via pack_sources. Leave blank unless you find a reference.

- **Hand Scope** (×1): Common item, likely multi-set
- **Pokédex** (×1): Common item, likely multi-set
- **Potion** (×1): Common item, likely multi-set
- **Red Card** (×1): Common item, likely multi-set
- **X Speed** (×1): Common item, likely multi-set
