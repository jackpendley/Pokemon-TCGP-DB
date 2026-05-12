# Current Collection Pack-Source Coverage

> This is coverage analysis only. No pack-opening recommendation is made in this report.

## Summary

| Field | Value |
|---|---|
| Collection source | `collection.json` |
| Collection total | 380 (224 unique entries) |
| Pack-source DB | `pack_sources.json` (3110 records) |
| Resolved entries | 157/224 (70%) |
| Resolved quantity | 269/380 (70%) |

## Coverage by Match Status

| Status | Entries | Quantity | Meaning |
|---|---|---|---|
| `exact_match` | 108 | 182 | One candidate in pack_sources |
| `unanimous_pack` | 49 | 87 | Multiple candidates, all same pack |
| `unanimous_expansion` | 0 | 0 | Multiple candidates, same expansion (shared pool) |
| `ambiguous_same_set` | 0 | 0 | Multiple packs within same expansion — needs confirmation |
| `ambiguous_cross_set` | 59 | 101 | Candidates across multiple expansions — needs confirmation |
| `no_match` | 3 | 5 | Not found in pack_sources |
| `no_match_known_gap` | 5 | 5 | Common item not indexed in Limitless |

## EX Card Coverage

| Card | Count | Status | Confidence | Expansions |
|---|---|---|---|---|
| Corviknight ex | 1 | `unanimous_pack` | medium | Pulsing Aura |
| Incineroar ex | 1 | `exact_match` | high | Mega Rising |
| Magnezone ex | 1 | `unanimous_pack` | medium | Pulsing Aura |
| Marowak ex | 1 | `ambiguous_cross_set` | low | Celestial Guardians, Deluxe Pack: ex, Genetic Apex |
| Mega Camerupt ex | 1 | `unanimous_pack` | medium | Pulsing Aura |
| Mega Charizard Y ex | 2 | `unanimous_pack` | medium | Crimson Blaze |
| Mega Venusaur ex | 2 | `unanimous_pack` | medium | Crimson Blaze |
| Moltres ex | 1 | `ambiguous_cross_set` | low | Deluxe Pack: ex, Eevee Grove, Genetic Apex |
| Vaporeon ex | 1 | `unanimous_pack` | medium | Pulsing Aura |
| Zygarde ex | 1 | `no_match` | none | — |

## Trainer Card Coverage

| Card | Subtype | Count | Status | Pack/Expansion |
|---|---|---|---|---|
| Clemont's Backpack | Item | 1 | `exact_match` | Crimson Blaze |
| Field Blower | Item | 1 | `exact_match` | Pulsing Aura |
| Flame Patch | Item | 2 | `unanimous_pack` | Mega Blaziken, shared pool |
| Hand Scope | Item | 1 | `no_match_known_gap` | — |
| Poké Ball | Item | 4 | `exact_match` | Shining Revelry |
| Pokédex | Item | 1 | `no_match_known_gap` | — |
| Potion | Item | 1 | `no_match_known_gap` | — |
| Quick-Grow Extract | Item | 4 | `unanimous_pack` | Crimson Blaze |
| Rare Candy | Item | 1 | `unanimous_pack` | Deluxe Pack: ex, shared pool |
| Red Card | Item | 1 | `no_match_known_gap` | — |
| X Speed | Item | 1 | `no_match_known_gap` | — |
| Giant Cape | Pokemon Tool | 2 | `ambiguous_cross_set` | Deluxe Pack: ex, Dialga |
| Arena of Antiquity | Stadium | 1 | `exact_match` | Pulsing Aura |
| Starting Plains | Stadium | 1 | `exact_match` | Fantastical Parade |
| Cheren | Supporter | 2 | `unanimous_pack` | Pulsing Aura |
| Clemont | Supporter | 2 | `unanimous_pack` | Crimson Blaze |
| Copycat | Supporter | 2 | `unanimous_pack` | Mega Gyarados |
| Cyrus | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Palkia |
| Giovanni | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Mewtwo |
| Korrina | Supporter | 2 | `unanimous_pack` | Pulsing Aura |
| Leaf | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Mew |
| Lillie | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Solgaleo |
| May | Supporter | 1 | `unanimous_pack` | Mega Blaziken |
| Professor's Research | Supporter | 4 | `exact_match` | Deluxe Pack: ex |
| Sabrina | Supporter | 1 | `ambiguous_cross_set` | Charizard, Deluxe Pack: ex |
| Serena | Supporter | 1 | `unanimous_pack` | Crimson Blaze |

## Ambiguous Cards (59 entries)

These cards appear in multiple packs/expansions in pack_sources.
Cannot assign a pack without knowing which specific version the user owns.

| Card | Type | Count | Status | Expansions |
|---|---|---|---|---|
| Bewear | Fighting | 2 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Blaziken | Fire | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Bulbasaur | Grass | 1 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| Bulbasaur | Grass | 1 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| Bulbasaur | Grass | 3 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| Charmander | Fire | 4 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| Charmander | Fire | 2 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| Charmeleon | Fire | 2 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| Cherubi | Grass | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Triumphant Light, Wisdom of Sea and Sky |
| Chewtle | Water | 1 | `ambiguous_cross_set` | Fantastical Parade, Mega Rising |
| Cinccino | Colorless | 2 | `ambiguous_cross_set` | Mega Shine, Pulsing Aura |
| Corvisquire | Colorless | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Cyrus | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Space-Time Smackdown |
| Darmanitan | Fire | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Darumaka | Fire | 2 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Doublade | Metal | 1 | `ambiguous_cross_set` | Fantastical Parade, Mega Rising |
| Eelektross | Lightning | 1 | `ambiguous_cross_set` | Genetic Apex, Secluded Springs |
| Eevee | Colorless | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Farfetch'd | Colorless | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Eevee Grove, Genetic Apex |
| Frillish | Water | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Furfrou | Colorless | 1 | `ambiguous_cross_set` | Crimson Blaze, Fantastical Parade, Mega Rising |
| Garbodor | Darkness | 3 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| Giant Cape | Pokemon Tool | 2 | `ambiguous_cross_set` | Deluxe Pack: ex, Space-Time Smackdown |
| Giovanni | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Genetic Apex |
| Grimer | Darkness | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Hariyama | Fighting | 2 | `ambiguous_cross_set` | Crimson Blaze, Mega Rising |
| Herdier | Colorless | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Ivysaur | Grass | 1 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| Leaf | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Mythical Island |
| Lillie | Supporter | 1 | `ambiguous_cross_set` | Celestial Guardians, Deluxe Pack: ex |
| Lillipup | Colorless | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Magnemite | Lightning | 1 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Magnemite | Lightning | 2 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Magneton | Lightning | 1 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Magneton | Lightning | 2 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Makuhita | Fighting | 1 | `ambiguous_cross_set` | Crimson Blaze, Mega Rising |
| Marowak ex | Fighting | 1 | `ambiguous_cross_set` | Celestial Guardians, Deluxe Pack: ex, Genetic Apex |
| Meltan | Metal | 2 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Minccino | Colorless | 4 | `ambiguous_cross_set` | Mega Shine, Pulsing Aura |
| Moltres ex | Fire | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Eevee Grove, Genetic Apex |
| Onix | Fighting | 1 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Onix | Fighting | 2 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Pikachu | Lightning | 1 | `ambiguous_cross_set` | Fantastical Parade, Mega Shine |
| Poliwhirl | Water | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Porygon | Colorless | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Porygon2 | Colorless | 1 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Ralts | Psychic | 1 | `ambiguous_cross_set` | Fantastical Parade, Pulsing Aura |
| Rolycoly | Fighting | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Sabrina | Supporter | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Genetic Apex |
| Sandshrew | Fighting | 2 | `ambiguous_cross_set` | Crimson Blaze, Fantastical Parade, Mega Rising |
| Sandslash | Fighting | 2 | `ambiguous_cross_set` | Crimson Blaze, Fantastical Parade, Mega Rising |
| Skrelp | Darkness | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Steelix | Metal | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| Stoutland | Colorless | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Stufful | Fighting | 1 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| Tangela | Grass | 3 | `ambiguous_cross_set` | Fantastical Parade, Pulsing Aura |
| Trubbish | Darkness | 1 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| Varoom | Metal | 1 | `ambiguous_cross_set` | Mega Shine, Paldean Wonders |
| Zorua | Darkness | 2 | `ambiguous_cross_set` | Mega Shine, Pulsing Aura |

## No-Match Cards (8 entries)

| Card | Type | Count | Status | Notes |
|---|---|---|---|---|
| Hand Scope | Trainer | 1 | `no_match_known_gap` | Common item — not in Limitless DB |
| Pokédex | Trainer | 1 | `no_match_known_gap` | Common item — not in Limitless DB |
| Potion | Trainer | 1 | `no_match_known_gap` | Common item — not in Limitless DB |
| Red Card | Trainer | 1 | `no_match_known_gap` | Common item — not in Limitless DB |
| X Speed | Trainer | 1 | `no_match_known_gap` | Common item — not in Limitless DB |
| Zygarde 10% Forme | Fighting | 1 | `no_match` | Not found in pack_sources |
| Zygarde 50% Forme | Fighting | 3 | `no_match` | Not found in pack_sources |
| Zygarde ex | Fighting | 1 | `no_match` | Not found in pack_sources |

## Priority Cards for Pack EV Resolution

Sorted by: (1) chase deck targets, (2) ex cards, (3) trainer staples, (4) other.

| Priority | Card | Count | Status | Expansions |
|---|---|---|---|---|
| 🎯 Chase target | Moltres ex | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Eevee Grove |
| 🎯 Chase target | Ivysaur | 1 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| 🎯 Chase target | Marowak ex | 1 | `ambiguous_cross_set` | Celestial Guardians, Deluxe Pack: ex |
| 🎯 Chase target | Zygarde ex | 1 | `no_match` | — |
| 🃏 Trainer staple | Giant Cape | 2 | `ambiguous_cross_set` | Deluxe Pack: ex, Space-Time Smackdown |
| 🃏 Trainer staple | Giovanni | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Genetic Apex |
| 🃏 Trainer staple | Sabrina | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Genetic Apex |
| 🃏 Trainer staple | Leaf | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Mythical Island |
| 🃏 Trainer staple | Cyrus | 1 | `ambiguous_cross_set` | Deluxe Pack: ex, Space-Time Smackdown |
| 🃏 Trainer staple | Lillie | 1 | `ambiguous_cross_set` | Celestial Guardians, Deluxe Pack: ex |
| — | Charmander | 4 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| — | Minccino | 4 | `ambiguous_cross_set` | Mega Shine, Pulsing Aura |
| — | Darmanitan | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Bulbasaur | 3 | `ambiguous_cross_set` | Crimson Blaze, Deluxe Pack: ex |
| — | Tangela | 3 | `ambiguous_cross_set` | Fantastical Parade, Pulsing Aura |
| — | Poliwhirl | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Rolycoly | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Zygarde 50% Forme | 3 | `no_match` | — |
| — | Garbodor | 3 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| — | Grimer | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| — | Steelix | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| — | Herdier | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Lillipup | 3 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Porygon | 3 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| — | Charmander | 2 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| — | Charmeleon | 2 | `ambiguous_cross_set` | Crimson Blaze, Mega Shine |
| — | Darumaka | 2 | `ambiguous_cross_set` | Mega Rising, Pulsing Aura |
| — | Magneton | 2 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| — | Magnemite | 2 | `ambiguous_cross_set` | Crimson Blaze, Pulsing Aura |
| — | Sandslash | 2 | `ambiguous_cross_set` | Crimson Blaze, Fantastical Parade |
