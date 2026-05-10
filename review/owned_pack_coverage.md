# Owned Pack Coverage Report

Generated: 2026-05-10 22:56 UTC

> **Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.**

## Summary

| Metric | Value |
|---|---|
| Total owned entries | 211 |
| Total owned quantity | 329 |
| Exact pack match (set+number) | 93 |
| Name-only match, pack agreed | 36 |
| Name-only match, pack ambiguous | 62 |
| No match in pack_sources | 20 |
| Exact coverage % | 44.1% |
| Broad coverage % (exact + agreed) | 61.1% |

## Notes on Matching

- **Exact match**: card has `set_code` + `card_number` from metadata enrichment phase; matched directly to pack_sources record.
- **Name agree**: no set_code/card_number in owned data; matched by card name only; all name matches agree on the same pack_name. Useful but not authoritative.
- **Ambiguous**: name matches multiple records with different pack_names. Cannot determine which specific set/pack without set_code + card_number.
- **No match**: card name not found in pack_sources at all. May be a trainer/promo card not in our reference, or a name variant.

## Coverage by Set Code (Exact Matches)

| Set Code | Owned Cards Resolved |
|---|---|
| B1 | 11 |
| B1a | 28 |
| B2 | 11 |
| B2b | 1 |
| B3 | 42 |

## Coverage by Pack Name (Exact Matches)

| Pack Name | Owned Cards |
|---|---|
| Pulsing Aura | 42 |
| Crimson Blaze | 28 |
| Fantastical Parade | 11 |
| Mega Blaziken | 5 |
| None | 3 |
| Mega Gyarados | 2 |
| Mega Shine | 1 |
| Mega Altaria | 1 |

## Name-Agreed Pack Assignments (Medium Confidence, up to 30)

_These cards have a unique pack assignment from name matching, but not confirmed by set_code+card_number._

| Card Name | Qty | Pack(s) | Expansion(s) |
|---|---|---|---|
| Quick-Grow Extract | 1 | Crimson Blaze | Crimson Blaze |
| Sobble | 1 | Pulsing Aura | Pulsing Aura |
| Clemont | 1 | Crimson Blaze | Crimson Blaze |
| Tepig | 1 | Pulsing Aura | Pulsing Aura |
| Zekrom | 1 | Pulsing Aura | Pulsing Aura |
| Bonsly | 1 | Pulsing Aura | Pulsing Aura |
| Mega Venusaur ex | 2 | Crimson Blaze | Crimson Blaze |
| Mega Charizard Y ex | 2 | Crimson Blaze | Crimson Blaze |
| Vaporeon | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| Corviknight | 1 | Mega Blaziken | Mega Rising |
| Charizard | 1 | Crimson Blaze | Crimson Blaze |
| Yveltal | 1 | Fantastical Parade | Fantastical Parade |
| Budew | 1 | Pulsing Aura | Pulsing Aura |
| Cyrus | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| Rare Candy | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| Giant Cape | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| May | 1 | Mega Blaziken | Mega Rising |
| Copycat | 1 | Mega Gyarados | Mega Rising |
| Quick-Grow Extract | 3 | Crimson Blaze | Crimson Blaze |
| Clemont | 1 | Crimson Blaze | Crimson Blaze |
| Serena | 1 | Crimson Blaze | Crimson Blaze |
| Quagsire | 1 | Pulsing Aura | Pulsing Aura |
| Malamar | 1 | Pulsing Aura | Pulsing Aura |
| Bisharp | 1 | Pulsing Aura | Pulsing Aura |
| Korrina | 1 | Pulsing Aura | Pulsing Aura |
| Cheren | 1 | Pulsing Aura | Pulsing Aura |
| Farfetch'd | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| Cherubi | 1 | Deluxe Pack: ex | Deluxe Pack: ex |
| Buneary | 2 | Crimson Blaze | Crimson Blaze |
| Treecko | 2 | Pulsing Aura | Pulsing Aura |

_...and 6 more_

## Ambiguous Pack Assignments (up to 30)

_These cards match multiple records in pack_sources with different pack names. Cannot resolve without set_code + card_number._

| Card Name | Qty | Possible Packs | Sets |
|---|---|---|---|
| Blaziken | 1 | Mega Blaziken, Pulsing Aura | B1, B3 |
| Skrelp | 1 | Mega Blaziken, Pulsing Aura | B1, B3 |
| Bulbasaur | 1 | Crimson Blaze, Deluxe Pack: ex | A4b, B1a |
| Shroomish | 1 | Pulsing Aura, None | B1, B3 |
| Morpeko | 1 | Mega Shine, Pulsing Aura | B2b, B3 |
| Riolu | 1 | Deluxe Pack: ex, Pulsing Aura | A4b, B3 |
| Meltan | 1 | Mega Gyarados, Pulsing Aura | B1, B3 |
| Meloetta | 3 | Fantastical Parade, Pulsing Aura | B2, B3 |
| Crobat | 1 | Deluxe Pack: ex, Pulsing Aura | A4b, B3 |
| Stoutland | 1 | Mega Altaria, Pulsing Aura | B1, B3 |
| Sandslash | 2 | Crimson Blaze, Fantastical Parade, None | B1, B1a, B2 |
| Onix | 1 | Crimson Blaze, Pulsing Aura | B1a, B3 |
| Flame Patch | 2 | Mega Blaziken, None | B1 |
| Ivysaur | 1 | Crimson Blaze, Deluxe Pack: ex | A4b, B1a |
| Magneton | 1 | Crimson Blaze, Deluxe Pack: ex, Pulsing Aura | A4b, B1a, B3 |
| Mismagius | 2 | Crimson Blaze, None | B1, B1a |
| Hariyama | 2 | Crimson Blaze, Mega Blaziken | B1, B1a |
| Garbodor | 3 | Crimson Blaze, Mega Shine | B1a, B2b |
| Steelix | 3 | Crimson Blaze, Pulsing Aura | B1a, B3 |
| Porygon2 | 1 | Crimson Blaze, Pulsing Aura | B1a, B3 |
| Furfrou | 1 | Crimson Blaze, Fantastical Parade, Mega Altaria, Mega Blaziken, Mega Gyarados, Mega Shine, Pulsing Aura | B1, B1a, B2, B2b, B3 |
| Doublade | 1 | Fantastical Parade, Mega Blaziken | B1, B2 |
| Charmeleon | 2 | Crimson Blaze, Deluxe Pack: ex, Mega Shine | A4b, B1a, B2b |
| Breloom | 1 | Pulsing Aura, None | B1, B3 |
| Darmanitan | 3 | Mega Gyarados, Pulsing Aura | B1, B3 |
| Poliwhirl | 2 | Mega Gyarados, Pulsing Aura | B1, B3 |
| Paldean Tauros | 2 | Mega Shine, Paldean Wonders, Pulsing Aura | B2a, B2b, B3 |
| Magneton | 2 | Crimson Blaze, Deluxe Pack: ex, Pulsing Aura | A4b, B1a, B3 |
| Bewear | 2 | Mega Blaziken, Pulsing Aura | B1, B3 |
| Golbat | 1 | Deluxe Pack: ex, Pulsing Aura | A4b, B3 |

_...and 32 more_

## Unresolved Cards (No Match in pack_sources, up to 30)

| Card Name | Qty | Screenshot |
|---|---|---|
| Marowak | 1 | IMG_1525.PNG |
| Incineroar | 1 | IMG_1525.PNG |
| Eelektross | 1 | IMG_1526.PNG |
| Urshifu | 1 | IMG_1527.PNG |
| Giovanni | 1 | IMG_1528.PNG |
| Sabrina | 1 | IMG_1528.PNG |
| Leaf | 1 | IMG_1528.PNG |
| Lillie | 1 | IMG_1528.PNG |
| Venonat | 1 | IMG_1535.PNG |
| Rattata | 2 | IMG_1536.PNG |
| Raticate | 1 | IMG_1536.PNG |
| Potion | 1 | IMG_1546.PNG |
| X Speed | 1 | IMG_1546.PNG |
| Hand Scope | 1 | IMG_1546.PNG |
| Pokédex | 1 | IMG_1546.PNG |
| Poké Ball | 4 | IMG_1546.PNG |
| Red Card | 1 | IMG_1546.PNG |
| Professor's Research | 4 | IMG_1547.PNG |
| Zygarde | 1 | IMG_1547.PNG |
| Zygarde | 3 | IMG_1547.PNG |

## Why Pack Recommendations Are Still Deferred

- **82 owned cards** have no definitive pack assignment.
- `set_or_pack` is still unknown for all 211 owned cards in cards.json.
- Pack pull probability tables are not yet modeled.
- Current meta tier list data is not integrated.

Next step: resolve set_code + card_number for the remaining owned cards to improve exact match coverage, then build recommendation engine.

---

> **Reminder:** Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.

