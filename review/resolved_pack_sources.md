# Resolved Ambiguous Pack Sources

Generated: 2026-05-21  
Script: `scripts/resolve_ambiguous_pack_sources.py`

---

## Summary

| Metric | Value |
|---|---|
| Low-confidence input | 70 |
| PASS 0 — user_confirmation | 41 |
| PASS 1 — hp_match | 6 |
| PASS 2 — evo_chain | 0 |
| PASS 3 — rarity_count | 6 |
| PASS 2B — evo_chain (post-P3) | 1 |
| PASS 4 — pz_set_code | 16 |
| **Total new resolved** | **70** |
| Still unresolved | 0 |
| EV-ready before | 202/272 (74%) |
| EV-ready after  | 272/272 (100%) |

---

## PASS 0: User Confirmations

| Entry | Set | Pack | Evidence |
|---|---|---|---|
| bewear | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 91) |
| blaziken | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 208) |
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
| frillish | B1 | Mega Gyarados | user confirmed via apply_current_pack_confirmations.py: (B1, 68) |
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
| skrelp | B3 | Pulsing Aura | user confirmed via apply_current_pack_confirmations.py: (B3, 218) |
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
| meowth | B2 | Fantastical Parade | 0.88 | collection hp=50 uniquely matches B2 in external reference |
| pikachu | B2 | Fantastical Parade | 0.88 | collection hp=60 uniquely matches B2 in external reference |
| tandemaus | B2 | Fantastical Parade | 0.88 | collection hp=40 uniquely matches B2 in external reference |

## PASS 2: Evolution Chain

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|

## PASS 3: Rarity / Count Inference

| Entry | Set | Pack | Count | Confidence | Evidence |
|---|---|---|---|---|---|
| farfetch_d | A1 | None | — | 0.85 | count=2 with A1=one_diamond; one_star candidate(s) A4b=one_star implausible at this count |
| grimer | B1a | Crimson Blaze | — | 0.9 | count=4 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| onix_dig_art | B1a | Crimson Blaze | — | 0.85 | count=2 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| porygon | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| steelix | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=two_diamond; one_star candidate(s) B3=one_star implausible at this count |
| toxel | B3 | Pulsing Aura | — | 0.9 | count=4 with B3=one_diamond; one_star candidate(s) B2=one_star implausible at this count |

## PASS 2B: Evolution Chain (post-PASS 3)

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|
| porygon2 | B1a | Crimson Blaze | 0.82 | evolution partner 'porygon' confirmed in B1a |

## PASS 4: Pokemon Zone Set Code

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|
| crobat_ex | A4b | Deluxe Pack: ex | 0.97 | Pokemon Zone reports setCode=A4b for owned copy |
| cyrus | A2 | Palkia | 0.97 | Pokemon Zone reports setCode=A2 for owned copy |
| giant_cape | A2 | Dialga | 0.97 | Pokemon Zone reports setCode=A2 for owned copy |
| giovanni | A1 | Mewtwo | 0.97 | Pokemon Zone reports setCode=A1 for owned copy |
| hypno | B2b | Mega Shine | 0.97 | Pokemon Zone reports setCode=B2b for owned copy |
| kirlia | B3 | Pulsing Aura | 0.97 | Pokemon Zone reports setCode=B3 for owned copy |
| leaf | A1a | Mew | 0.97 | Pokemon Zone reports setCode=A1a for owned copy |
| lillie | A3 | Solgaleo | 0.97 | Pokemon Zone reports setCode=A3 for owned copy |
| lyra | A4b | Deluxe Pack: ex | 0.97 | Pokemon Zone reports setCode=A4b for owned copy |
| marowak_ex | A1 | Mewtwo | 0.97 | Pokemon Zone reports setCode=A1 for owned copy |
| moltres_ex | A1 | Charizard | 0.97 | Pokemon Zone reports setCode=A1 for owned copy |
| sabrina | A1 | Charizard | 0.97 | Pokemon Zone reports setCode=A1 for owned copy |
| shaymin | A4b | Deluxe Pack: ex | 0.97 | Pokemon Zone reports setCode=A4b for owned copy |
| sneasel | A4b | Deluxe Pack: ex | 0.97 | Pokemon Zone reports setCode=A4b for owned copy |
| snorlax_ex | A4b | Deluxe Pack: ex | 0.97 | Pokemon Zone reports setCode=A4b for owned copy |
| spinda | B2 | Fantastical Parade | 0.97 | Pokemon Zone reports setCode=B2 for owned copy |

## Unresolved (manual review or leave as ambiguous)

| Entry | Candidates | Reason |
|---|---|---|

---

## Confidence Tier Summary

Entries resolved at confidence ≥ 0.80 are EV-ready (auto-accept or secondary tier).

| Method | Confidence | Tier |
|---|---|---|
| user_confirmation | 0.99 | auto_accept |
| pz_set_code | 0.97 | auto_accept |
| hp_match | 0.88 | secondary |
| evo_chain | 0.82 | secondary |
| rarity_count (count≥3) | 0.90 | secondary |
| rarity_count (count=2) | 0.85 | secondary |

All new resolutions are at secondary tier (0.80–0.94). None reach auto-accept (≥0.95) — downstream use must weight accordingly.
