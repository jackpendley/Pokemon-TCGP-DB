# Resolved Ambiguous Pack Sources

Generated: 2026-05-15  
Script: `scripts/resolve_ambiguous_pack_sources.py`

---

## Summary

| Metric | Value |
|---|---|
| Low-confidence input | 59 |
| PASS 0 — user_confirmation | 38 |
| PASS 1 — hp_match | 4 |
| PASS 2 — evo_chain | 0 |
| PASS 3 — rarity_count | 4 |
| **Total new resolved** | **46** |
| Still unresolved | 13 |
| EV-ready before | 157/224 (70%) |
| EV-ready after  | 203/224 (91%) |

---

## PASS 0: User Confirmations

| Entry | Set | Pack | Evidence |
|---|---|---|---|
| bewear | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 91) |
| bulbasaur_tackle_art | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 1) |
| charmander | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 11) |
| charmander_flame_tail_art | B2b | Mega Shine | user confirmed via apply_current_pack_confirmations.py: (B2b, 7) |
| charmeleon | B2b | Mega Shine | user confirmed via apply_current_pack_confirmations.py: (B2b, 8) |
| cherubi | A4 | None | user confirmed via apply_current_pack_confirmations.py: (A4, 23) |
| chewtle | B1 | Mega Gyarados | user confirmed via apply_current_pack_confirmations.py: (B1, 76) |
| cinccino | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 143) |
| corvisquire | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 146) |
| darmanitan | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 30) |
| darumaka | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 29) |
| doublade | B2 | Fantastical Parade | user confirmed via apply_current_pack_confirmations.py: (B2, 119) |
| eelektross | A1 | Mewtwo | user confirmed via apply_current_pack_confirmations.py: (A1, 109) |
| eevee | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 129) |
| garbodor | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 50) |
| hariyama | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 40) |
| herdier | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 138) |
| ivysaur | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 2) |
| lillipup | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 137) |
| magnemite_electro_ball_art | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 24) |
| magnemite_thunder_shock_art | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 52) |
| magneton_magnetic_blast_art | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 53) |
| magneton_spark_art | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 25) |
| makuhita | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 39) |
| meltan | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 122) |
| minccino | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 142) |
| onix_land_crush_art | A1 | Pikachu | user confirmed via apply_current_pack_confirmations.py: (A1, 150) |
| poliwhirl | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 34) |
| ralts | B2 | Fantastical Parade | user confirmed via apply_current_pack_confirmations.py: (B2, 63) |
| rolycoly | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 92) |
| sandshrew | A1 | None | user confirmed via apply_current_pack_confirmations.py: (A1, 137) |
| sandslash | A1 | None | user confirmed via apply_current_pack_confirmations.py: (A1, 138) |
| stoutland | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 139) |
| stufful | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 90) |
| tangela | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 1) |
| trubbish | B1a | Crimson Blaze | user confirmed via apply_current_pack_confirmations.py: (B1a, 49) |
| varoom | B2b | Mega Shine | user confirmed via apply_current_pack_confirmations.py: (B2b, 49) |
| zorua | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 105) |

## PASS 1: HP Match

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|
| bulbasaur | A4b | Deluxe Pack: ex | 0.88 | collection hp=70 uniquely matches A4b in external reference |
| bulbasaur_alt_art | A4b | Deluxe Pack: ex | 0.88 | collection hp=70 uniquely matches A4b in external reference |
| furfrou | B1a | Crimson Blaze | 0.88 | collection hp=70 uniquely matches B1a in external reference |
| pikachu | B2 | Fantastical Parade | 0.88 | collection hp=60 uniquely matches B2 in external reference |

## PASS 2: Evolution Chain

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|

## PASS 3: Rarity / Count Inference

| Entry | Set | Pack | Count | Confidence | Evidence |
|---|---|---|---|---|---|
| grimer | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| onix_dig_art | B1a | Crimson Blaze | — | 0.85 | count=2 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| porygon | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| steelix | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=two_diamond; one_star candidate(s) B3=one_star implausible at this count |

## Unresolved (manual review or leave as ambiguous)

| Entry | Candidates | Reason |
|---|---|---|
| blaziken | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| cyrus | A2, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| farfetch_d | A1, A3b, A4a, A4b | A-series card — not in external_card_reference.json |
| frillish | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| giant_cape | A2, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| giovanni | A1, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| leaf | A1a, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| lillie | A3, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| marowak_ex | A1, A3, A4b | A-series card — not in external_card_reference.json |
| moltres_ex | A1, A3b, A4b | A-series card — not in external_card_reference.json |
| porygon2 | B1a, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| sabrina | A1, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| skrelp | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |

---

## Confidence Tier Summary

Entries resolved at confidence ≥ 0.80 are EV-ready (auto-accept or secondary tier).

| Method | Confidence | Tier |
|---|---|---|
| user_confirmation | 0.99 | auto_accept |
| hp_match | 0.88 | secondary |
| evo_chain | 0.82 | secondary |
| rarity_count (count≥3) | 0.90 | secondary |
| rarity_count (count=2) | 0.85 | secondary |

All new resolutions are at secondary tier (0.80–0.94). None reach auto-accept (≥0.95) — downstream use must weight accordingly.
