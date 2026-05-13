# Resolved Ambiguous Pack Sources

Generated: 2026-05-13  
Script: `scripts/resolve_ambiguous_pack_sources.py`

---

## Summary

| Metric | Value |
|---|---|
| Low-confidence input | 59 |
| PASS 1 — hp_match | 23 |
| PASS 2 — evo_chain | 4 |
| PASS 3 — rarity_count | 8 |
| **Total new resolved** | **35** |
| Still unresolved | 24 |
| EV-ready before | 157/224 (70%) |
| EV-ready after  | 192/224 (86%) |

---

## PASS 1: HP Match

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|
| bewear | B3 | Pulsing Aura | 0.88 | collection hp=110 uniquely matches B3 in external reference |
| bulbasaur | A4b | Deluxe Pack: ex | 0.88 | collection hp=70 uniquely matches A4b in external reference |
| bulbasaur_alt_art | A4b | Deluxe Pack: ex | 0.88 | collection hp=70 uniquely matches A4b in external reference |
| bulbasaur_tackle_art | B1a | Crimson Blaze | 0.88 | collection hp=60 uniquely matches B1a in external reference |
| charmander | B1a | Crimson Blaze | 0.88 | collection hp=60 uniquely matches B1a in external reference |
| charmander_flame_tail_art | B2b | Mega Shine | 0.88 | collection hp=70 uniquely matches B2b in external reference |
| darmanitan | B3 | Pulsing Aura | 0.88 | collection hp=120 uniquely matches B3 in external reference |
| darumaka | B3 | Pulsing Aura | 0.88 | collection hp=60 uniquely matches B3 in external reference |
| eevee | B3 | Pulsing Aura | 0.88 | collection hp=60 uniquely matches B3 in external reference |
| furfrou | B1a | Crimson Blaze | 0.88 | collection hp=70 uniquely matches B1a in external reference |
| garbodor | B1a | Crimson Blaze | 0.88 | collection hp=130 uniquely matches B1a in external reference |
| hariyama | B1a | Crimson Blaze | 0.88 | collection hp=120 uniquely matches B1a in external reference |
| ivysaur | B1a | Crimson Blaze | 0.88 | collection hp=100 uniquely matches B1a in external reference |
| magnemite_electro_ball_art | B1a | Crimson Blaze | 0.88 | collection hp=50 uniquely matches B1a in external reference |
| magnemite_thunder_shock_art | B3 | Pulsing Aura | 0.88 | collection hp=60 uniquely matches B3 in external reference |
| magneton_magnetic_blast_art | B3 | Pulsing Aura | 0.88 | collection hp=90 uniquely matches B3 in external reference |
| magneton_spark_art | B1a | Crimson Blaze | 0.88 | collection hp=80 uniquely matches B1a in external reference |
| meltan | B3 | Pulsing Aura | 0.88 | collection hp=60 uniquely matches B3 in external reference |
| minccino | B3 | Pulsing Aura | 0.88 | collection hp=50 uniquely matches B3 in external reference |
| pikachu | B2 | Fantastical Parade | 0.88 | collection hp=60 uniquely matches B2 in external reference |
| ralts | B2 | Fantastical Parade | 0.88 | collection hp=60 uniquely matches B2 in external reference |
| rolycoly | B3 | Pulsing Aura | 0.88 | collection hp=80 uniquely matches B3 in external reference |
| varoom | B2b | Mega Shine | 0.88 | collection hp=70 uniquely matches B2b in external reference |

## PASS 2: Evolution Chain

| Entry | Set | Pack | Confidence | Evidence |
|---|---|---|---|---|
| cinccino | B3 | Pulsing Aura | 0.82 | evolution partner 'minccino' confirmed in B3 |
| makuhita | B1a | Crimson Blaze | 0.82 | evolution partner 'hariyama' confirmed in B1a |
| stufful | B3 | Pulsing Aura | 0.82 | evolution partner 'bewear' confirmed in B3 |
| trubbish | B1a | Crimson Blaze | 0.82 | evolution partner 'garbodor' confirmed in B1a |

## PASS 3: Rarity / Count Inference

| Entry | Set | Pack | Count | Confidence | Evidence |
|---|---|---|---|---|---|
| charmeleon | B1a | Crimson Blaze | — | 0.85 | count=2 with B1a=two_diamond; one_star candidate(s) B2b=one_star implausible at this count |
| grimer | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| onix_dig_art | B1a | Crimson Blaze | — | 0.85 | count=2 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| poliwhirl | B3 | Pulsing Aura | — | 0.9 | count=3 with B3=two_diamond; one_star candidate(s) B1=one_star implausible at this count |
| porygon | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=one_diamond; one_star candidate(s) B3=one_star implausible at this count |
| sandshrew | B1 | None | — | 0.85 | count=2 with B1=one_diamond; one_star candidate(s) B1a=one_star, B2=one_star implausible at this count |
| steelix | B1a | Crimson Blaze | — | 0.9 | count=3 with B1a=two_diamond; one_star candidate(s) B3=one_star implausible at this count |
| tangela | B3 | Pulsing Aura | — | 0.9 | count=3 with B3=one_diamond; one_star candidate(s) B2=one_star implausible at this count |

## Unresolved (manual review or leave as ambiguous)

| Entry | Candidates | Reason |
|---|---|---|
| blaziken | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| cherubi | A2a, A4, A4b | A-series card — not in external_card_reference.json |
| chewtle | B1, B2 | HP matches same value across all candidate sets — no unique disambiguation |
| corvisquire | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| cyrus | A2, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| doublade | B1, B2 | HP matches same value across all candidate sets — no unique disambiguation |
| eelektross | A1, A4a | A-series card — not in external_card_reference.json |
| farfetch_d | A1, A3b, A4a, A4b | A-series card — not in external_card_reference.json |
| frillish | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| giant_cape | A2, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| giovanni | A1, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| herdier | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| leaf | A1a, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| lillie | A3, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| lillipup | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| marowak_ex | A1, A3, A4b | A-series card — not in external_card_reference.json |
| moltres_ex | A1, A3b, A4b | A-series card — not in external_card_reference.json |
| onix_land_crush_art | B1a, B3 | collection HP not found in external reference (possible data discrepancy) |
| porygon2 | B1a, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| sabrina | A1, A4b | trainer — no HP field, candidates span A1/A4b reprint |
| sandslash | B1, B1a, B2 | collection HP not found in external reference (possible data discrepancy) |
| skrelp | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| stoutland | B1, B3 | HP matches same value across all candidate sets — no unique disambiguation |
| zorua | B2b, B3 | HP matches same value across all candidate sets — no unique disambiguation |

---

## Confidence Tier Summary

Entries resolved at confidence ≥ 0.80 are EV-ready (auto-accept or secondary tier).

| Method | Confidence | Tier |
|---|---|---|
| hp_match | 0.88 | secondary |
| evo_chain | 0.82 | secondary |
| rarity_count (count≥3) | 0.90 | secondary |
| rarity_count (count=2) | 0.85 | secondary |

All new resolutions are at secondary tier (0.80–0.94). None reach auto-accept (≥0.95) — downstream use must weight accordingly.
