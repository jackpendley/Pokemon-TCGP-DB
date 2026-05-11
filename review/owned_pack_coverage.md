# Owned Pack Coverage Report

Generated: 2026-05-11 00:15 UTC

> **Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.**

## Summary

| Metric | Value |
|---|---|
| Total owned entries | 211 |
| Total owned quantity | 329 |
| Exact pack match (set+number) | 93 |
| Name-only match, pack agreed | 27 |
| Name-only match, pack ambiguous | 83 |
| No match in pack_sources | 8 |
| Exact coverage % | 44.1% |
| Broad coverage % (exact + agreed) | 56.9% |

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
| Incineroar | 1 | Eevee Grove | Eevee Grove |
| Mega Venusaur ex | 2 | Crimson Blaze | Crimson Blaze |
| Mega Charizard Y ex | 2 | Crimson Blaze | Crimson Blaze |
| Corviknight | 1 | Mega Blaziken | Mega Rising |
| Yveltal | 1 | Fantastical Parade | Fantastical Parade |
| Budew | 1 | Pulsing Aura | Pulsing Aura |
| May | 1 | Mega Blaziken | Mega Rising |
| Copycat | 1 | Mega Gyarados | Mega Rising |
| Quick-Grow Extract | 3 | Crimson Blaze | Crimson Blaze |
| Clemont | 1 | Crimson Blaze | Crimson Blaze |
| Serena | 1 | Crimson Blaze | Crimson Blaze |
| Korrina | 1 | Pulsing Aura | Pulsing Aura |
| Cheren | 1 | Pulsing Aura | Pulsing Aura |
| Venonat | 1 | Mewtwo | Genetic Apex |
| Treecko | 2 | Pulsing Aura | Pulsing Aura |
| Tepig | 1 | Pulsing Aura | Pulsing Aura |
| Sobble | 2 | Pulsing Aura | Pulsing Aura |
| Kubfu | 1 | Pulsing Aura | Pulsing Aura |
| Castform | 2 | Pulsing Aura | Pulsing Aura |
| Poké Ball | 4 | Shining Revelry | Shining Revelry |
| Professor's Research | 4 | Deluxe Pack: ex | Deluxe Pack: ex |

## Ambiguous Pack Assignments (up to 30)

_These cards match multiple records in pack_sources with different pack names. Cannot resolve without set_code + card_number._

| Card Name | Qty | Possible Packs | Sets |
|---|---|---|---|
| Blaziken | 1 | Mega Blaziken, Pulsing Aura | B1, B3 |
| Skrelp | 1 | Mega Blaziken, Pulsing Aura, Secluded Springs | A4a, B1, B3 |
| Bulbasaur | 1 | Crimson Blaze, Deluxe Pack: ex, Mewtwo, Solgaleo | A1, A3, A4b, B1a |
| Shroomish | 1 | Pulsing Aura, None | B1, B3 |
| Morpeko | 1 | Mega Shine, Pulsing Aura | B2b, B3 |
| Riolu | 1 | Deluxe Pack: ex, Dialga, Pulsing Aura, Shining Revelry | A2, A2b, A4b, B3 |
| Meltan | 1 | Charizard, Eevee Grove, Mega Gyarados, Pulsing Aura | A1, A3b, B1, B3 |
| Marowak | 1 | Lunala, Mewtwo | A1, A3 |
| Vaporeon | 1 | Deluxe Pack: ex, Eevee Grove, Lugia, Mew, Mewtwo | A1, A1a, A3b, A4, A4b |
| Eelektross | 1 | Mewtwo, Secluded Springs | A1, A4a |
| Charizard | 1 | Charizard, Crimson Blaze | A1, B1a |
| Meloetta | 3 | Fantastical Parade, Pulsing Aura | B2, B3 |
| Crobat | 1 | Arceus, Deluxe Pack: ex, Pulsing Aura | A2a, A4b, B3 |
| Stoutland | 1 | Extradimensional Crisis, Mega Altaria, Pulsing Aura | A3a, B1, B3 |
| Sandslash | 2 | Crimson Blaze, Fantastical Parade, None | A1, B1, B1a, B2 |
| Onix | 1 | Crimson Blaze, Ho-Oh, Pikachu, Pulsing Aura | A1, A4, B1a, B3 |
| Giovanni | 1 | Deluxe Pack: ex, Mewtwo | A1, A4b |
| Sabrina | 1 | Charizard, Deluxe Pack: ex | A1, A4b |
| Leaf | 1 | Deluxe Pack: ex, Mew | A1a, A4b |
| Cyrus | 1 | Deluxe Pack: ex, Palkia | A2, A4b |
| Rare Candy | 1 | Deluxe Pack: ex, None | A3, A4b |
| Lillie | 1 | Deluxe Pack: ex, Solgaleo | A3, A4b |
| Giant Cape | 1 | Deluxe Pack: ex, Dialga | A2, A4b |
| Flame Patch | 2 | Mega Blaziken, None | B1 |
| Ivysaur | 1 | Crimson Blaze, Deluxe Pack: ex, Mewtwo, Solgaleo | A1, A3, A4b, B1a |
| Magneton | 1 | Arceus, Crimson Blaze, Deluxe Pack: ex, Lugia, Pikachu, Pulsing Aura, None | A1, A2, A2a, A4, A4b, B1a, B3 |
| Mismagius | 2 | Crimson Blaze, Secluded Springs, None | A4a, B1, B1a |
| Hariyama | 2 | Crimson Blaze, Mega Blaziken, None | A3, B1, B1a |
| Garbodor | 3 | Crimson Blaze, Mega Shine, None | A3, B1a, B2b |
| Steelix | 3 | Crimson Blaze, Ho-Oh, Pulsing Aura | A4, B1a, B3 |

_...and 53 more_

## Unresolved Cards (No Match in pack_sources, up to 30)

| Card Name | Qty | Screenshot |
|---|---|---|
| Urshifu | 1 | IMG_1527.PNG |
| Potion | 1 | IMG_1546.PNG |
| X Speed | 1 | IMG_1546.PNG |
| Hand Scope | 1 | IMG_1546.PNG |
| Pokédex | 1 | IMG_1546.PNG |
| Red Card | 1 | IMG_1546.PNG |
| Zygarde | 1 | IMG_1547.PNG |
| Zygarde | 3 | IMG_1547.PNG |

## Why Pack Recommendations Are Still Deferred

- **91 owned cards** have no definitive pack assignment.
- `set_or_pack` is still unknown for all 211 owned cards in cards.json.
- Pack pull probability tables are not yet modeled.
- Current meta tier list data is not integrated.

Next step: resolve set_code + card_number for the remaining owned cards to improve exact match coverage, then build recommendation engine.

---

> **Reminder:** Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.

