# Owned Pack Coverage Report

Generated: 2026-05-11 01:41 UTC

> **Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.**

## Summary

| Metric | Value |
|---|---|
| Total owned entries | 211 |
| Total owned quantity | 329 |
| Exact pack match (set+number) | 166 |
| Name-only match, pack agreed | 27 |
| Name-only match, pack ambiguous | 10 |
| No match in pack_sources | 8 |
| Exact coverage % | 78.7% |
| Broad coverage % (exact + agreed) | 91.5% |

## Notes on Matching

- **Exact match**: card has `set_code` + `card_number` from metadata enrichment phase; matched directly to pack_sources record.
- **Name agree**: no set_code/card_number in owned data; matched by card name only; all name matches agree on the same pack_name. Useful but not authoritative.
- **Ambiguous**: name matches multiple records with different pack_names. Cannot determine which specific set/pack without set_code + card_number.
- **No match**: card name not found in pack_sources at all. May be a trainer/promo card not in our reference, or a name variant.

## Coverage by Set Code (Exact Matches)

| Set Code | Owned Cards Resolved |
|---|---|
| A1 | 8 |
| A4b | 1 |
| B1 | 12 |
| B1a | 49 |
| B2 | 12 |
| B2b | 3 |
| B3 | 81 |

## Coverage by Pack Name (Exact Matches)

| Pack Name | Owned Cards |
|---|---|
| Pulsing Aura | 81 |
| Crimson Blaze | 49 |
| Fantastical Parade | 12 |
| None | 7 |
| Mega Blaziken | 6 |
| Mewtwo | 3 |
| Mega Shine | 3 |
| Mega Gyarados | 2 |
| Pikachu | 1 |
| Mega Altaria | 1 |
| Deluxe Pack: ex | 1 |

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
| Marowak | 1 | Lunala, Mewtwo | A1, A3 |
| Giovanni | 1 | Deluxe Pack: ex, Mewtwo | A1, A4b |
| Sabrina | 1 | Charizard, Deluxe Pack: ex | A1, A4b |
| Leaf | 1 | Deluxe Pack: ex, Mew | A1a, A4b |
| Cyrus | 1 | Deluxe Pack: ex, Palkia | A2, A4b |
| Rare Candy | 1 | Deluxe Pack: ex, None | A3, A4b |
| Lillie | 1 | Deluxe Pack: ex, Solgaleo | A3, A4b |
| Giant Cape | 1 | Deluxe Pack: ex, Dialga | A2, A4b |
| Bulbasaur | 1 | Crimson Blaze, Deluxe Pack: ex, Mewtwo, Solgaleo | A1, A3, A4b, B1a |
| Farfetch'd | 1 | Deluxe Pack: ex, Eevee Grove, Secluded Springs, None | A1, A3b, A4a, A4b |

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

- **18 owned cards** have no definitive pack assignment.
- `set_or_pack` is still unknown for all 211 owned cards in cards.json.
- Pack pull probability tables are not yet modeled.
- Current meta tier list data is not integrated.

Next step: resolve set_code + card_number for the remaining owned cards to improve exact match coverage, then build recommendation engine.

---

> **Reminder:** Pack-opening recommendations are intentionally deferred. This report is coverage analysis only.

