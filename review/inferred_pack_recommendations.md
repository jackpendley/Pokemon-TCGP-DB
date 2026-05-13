# Inferred Pack Recommendation Report

> ## ⚠ INFERRED CONFIDENCE — NOT VERIFIED
>
> Slot rates sourced from Game8 PTCGP guide and corroborating sites.
> These rates have **NOT been verified** against the in-app Offering Rates screen.
> All EV values are adjusted by ×0.85 to reflect this uncertainty.
>
> **Do not treat this as a final pack-opening recommendation.**
> Verify slot rates in the PTCGP app first:
> App → any pack → Pack details → Offering Rates
>
> This report is decision-support for planning purposes only.

---

## Status

| Metric | Value |
|---|---|
| Report generated | 2026-05-13T03:10:56+00:00 |
| Model confidence | **in_app_verified_partial** (not official in-app verified) |
| Collection total | 380 cards (380 validated) |
| EV-ready entries | 157/224 (108 auto-accept + 49 secondary evidence) |
| Excluded from EV | 67/224 (59 low-confidence + 8 unresolved) |
| Packs ranked | 24 |
| Packs blocked | 0 |

---

## Top 5 Packs — All Metrics

| Rank | Pack | Expansion | Adj. EV | Total EV | New EV | Deck EV | EX EV | Missing |
|---|---|---|---|---|---|---|---|---|
| 1 | **Paldean Wonders** | Paldean Wonders | 4.2019 | 4.9435 | 4.9156 | 0.0000 | 0.2052 | 128 |
| 2 | **Fantastical Parade** | Fantastical Parade | 3.8206 | 4.4948 | 4.2512 | 0.0000 | 0.2234 | 205 |
| 3 | **Mew** | Mythical Island | 3.7835 | 4.4512 | 4.2741 | 0.0000 | 0.0000 | 77 |
| 4 | **Extradimensional Crisis** | Extradimensional Crisis | 3.7062 | 4.3602 | 4.1071 | 0.0000 | 0.0000 | 90 |
| 5 | **Mega Altaria** | Mega Rising | 3.6754 | 4.3240 | 4.1928 | 0.0000 | 0.2344 | 119 |

---

## Recommendation Buckets

### Best Overall Inferred EV

These packs have the highest expected number of new unique cards per pull,
adjusted for inferred-rate uncertainty.

| Rank | Pack | Adj. EV | Why |
|---|---|---|---|
| 1 | Paldean Wonders | 4.2019 | Large pool, very few owned (3/131). Almost every pull is new. |
| 2 | Fantastical Parade | 3.8206 | Largest pool (234 cards), 205 missing. Highest raw volume of new cards. |
| 3 | Mew | 3.7835 | Small dense pool (86 cards), 77 missing — high hit rate per pull. |
| 4 | Extradimensional Crisis | 3.7062 | Medium pool, low ownership (13/103). Consistent new-card rate. |
| 5 | Mega Altaria | 3.6754 | Large pool (139), 119 missing. Strong EX cards present. |

### Best for Collection Completion

Ranked by new_card_ev — these packs return the most new unique cards per pull.

| Rank | Pack | New Card EV | Missing in Pool |
|---|---|---|---|
| 1 | Paldean Wonders | 4.9156 | 128 |
| 2 | Mew | 4.2741 | 77 |
| 3 | Fantastical Parade | 4.2512 | 205 |
| 4 | Mega Altaria | 4.1928 | 119 |
| 5 | Extradimensional Crisis | 4.1071 | 90 |

### Best for Deck Targets

Ranked by deck_target_ev — these packs contain the highest-value missing deck cards.
Only Ivysaur (two_diamond) is in the top deck-target packs.
Incineroar ex is in Solgaleo. Magnezone ex is in Pulsing Aura.
Zygarde ex has **no known pack** — not in pack_sources.json.

| Rank | Pack | Deck Target EV | Notes |
|---|---|---|---|
| 1 | Crimson Blaze | 0.1499 | Contains Ivysaur (two_diamond) — best for Mega Venusaur ex |
| 2 | Mewtwo | 0.1028 | Contains Ivysaur (two_diamond) — alternative Mega Venusaur ex route |
| 3 | Deluxe Pack: ex | 0.0746 | Contains Ivysaur but low per-card rate (large pool, 379 cards) |
| 4 | Solgaleo | 0.0611 | Contains Incineroar ex (four_diamond) — best for Incineroar ex chase deck |
| 5 | Pulsing Aura | 0.0340 | Contains Magnezone ex — best for Magnezone ex chase deck |

### Best for EX / Card Power

Ranked by ex_card_ev — these packs contain the most missing EX cards.

| Rank | Pack | EX Card EV |
|---|---|---|
| 1 | Mega Gyarados | 0.2369 |
| 2 | Mega Altaria | 0.2344 |
| 3 | Mega Blaziken | 0.2344 |
| 4 | Fantastical Parade | 0.2234 |
| 5 | Mega Shine | 0.2115 |

### Packs to Deprioritize

These packs have the lowest adjusted EV — most cards in the pool are already owned.

| Rank | Pack | Adj. EV | Owned/Pool | Notes |
|---|---|---|---|---|
| 1 | Crimson Blaze | 1.5145 | 64/103 | High deck-target value offsets low general EV — open only if chasing Ivysaur |
| 2 | Pulsing Aura | 1.7232 | 141/234 | Contains Magnezone ex — open only if chasing that deck |
| 3 | Arceus | 3.0068 | 25/96 | Mid-range owned ratio |
| 4 | Mewtwo | 3.1995 | 38/126 | Higher EV than Crimson Blaze/Pulsing Aura; only deprioritized vs top packs |
| 5 | Pikachu | 3.3306 | 28/127 | Low new-card return relative to pool |

---

## Pack Detail — Top 5 by Adjusted EV

**Paldean Wonders** (Paldean Wonders)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **4.2019** |
| Total EV (raw) | 4.9435 |
| New-card EV | 4.9156 |
| EX-card EV | 0.2052 |
| Deck target EV | 0.0000 |
| Pool size | 131 cards |
| Already owned in pool | 3 |
| Missing from pool | **128** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Sprigatito | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Floragato | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Tarountula | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Nymble | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Smoliv | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |

---

**Fantastical Parade** (Fantastical Parade)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.8206** |
| Total EV (raw) | 4.4948 |
| New-card EV | 4.2512 |
| EX-card EV | 0.2234 |
| Deck target EV | 0.0000 |
| Pool size | 234 cards |
| Already owned in pool | 29 |
| Missing from pool | **205** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Ledyba | one_diamond | 0 | 0.04543 | 1.00 | 0.04543 |
| Ledian | one_diamond | 0 | 0.04543 | 1.00 | 0.04543 |
| Shuckle | one_diamond | 0 | 0.04543 | 1.00 | 0.04543 |
| Cacnea | one_diamond | 0 | 0.04543 | 1.00 | 0.04543 |
| Chespin | one_diamond | 0 | 0.04543 | 1.00 | 0.04543 |

---

**Mew** (Mythical Island)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.7835** |
| Total EV (raw) | 4.4512 |
| New-card EV | 4.2741 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0000 |
| Pool size | 86 cards |
| Already owned in pool | 9 |
| Missing from pool | **77** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Exeggcute | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Snivy | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Morelull | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Ponyta | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Salandit | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |

---

**Extradimensional Crisis** (Extradimensional Crisis)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.7062** |
| Total EV (raw) | 4.3602 |
| New-card EV | 4.1071 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0000 |
| Pool size | 103 cards |
| Already owned in pool | 13 |
| Missing from pool | **90** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Petilil | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Lilligant | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Rowlet | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Kartana | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Mantine | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |

---

**Mega Altaria** (Mega Rising)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.6754** |
| Total EV (raw) | 4.3240 |
| New-card EV | 4.1928 |
| EX-card EV | 0.2344 |
| Deck target EV | 0.0000 |
| Pool size | 139 cards |
| Already owned in pool | 20 |
| Missing from pool | **119** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Cottonee | one_diamond | 0 | 0.06119 | 1.00 | 0.06119 |
| Petilil | one_diamond | 0 | 0.06119 | 1.00 | 0.06119 |
| Skiddo | one_diamond | 0 | 0.06119 | 1.00 | 0.06119 |
| Gogoat | one_diamond | 0 | 0.06119 | 1.00 | 0.06119 |
| Grookey | one_diamond | 0 | 0.06119 | 1.00 | 0.06119 |

---

## Chase Deck Pack Guide

| Chase Deck | Missing Card | Short By | Best Pack | Pack EV | Pull Prob | Notes |
|---|---|---|---|---|---|---|
| Mega Venusaur ex | Ivysaur | 1 | Crimson Blaze | 0.14993 | 0.06247 |  |
| Incineroar ex | Incineroar ex | 1 | **UNKNOWN** | N/A | N/A | card not found in pack_sources — pack unknown |
| Zygarde ex Fighting | Zygarde ex | 1 | **UNKNOWN** | N/A | N/A | card not found in pack_sources — pack unknown |
| Magnezone ex (Clemont Engine) | Magnezone ex | 1 | **UNKNOWN** | N/A | N/A | card not found in pack_sources — pack unknown |

---

## Planning Scenarios

> These are scenarios for your consideration — not instructions.
> All scenarios assume inferred-confidence slot rates.

### Scenario A — Conservative: Wait for In-App Verification

**Action:** No pack opens until slot rates are verified in PTCGP app.

**How:** Open PTCGP → any pack → Pack details → Offering Rates.
Compare the displayed percentages against `slot_rates` in
`data/reference/pull_probability_model.json`.

If rates match: set `confidence=verified` in the model, re-run
`python3 scripts/build_pack_ev.py`, then return to this report for final rankings.

**Tradeoff:** Delays pack decisions but eliminates rate uncertainty.

### Scenario B — Moderate: Limited Opens at Inferred Confidence

**Action:** Open up to ~10 pulls from one pack, accepting the ~15% rate uncertainty.

**Suggested pack:** Paldean Wonders (adj EV=4.20) for general collection growth.
**Alternate:** Crimson Blaze if the Mega Venusaur ex chase deck is the priority.
**Alternate:** Solgaleo if the Incineroar ex chase deck is the priority.

**Tradeoff:** Some risk of suboptimal pulls if inferred rates are wrong, but EV
rankings are broadly stable — a pack ranked #1 at inferred confidence is very
unlikely to be worst at verified confidence.

### Scenario C — Aggressive: Maximize EV at Inferred Confidence

**Action:** Focus all pack opens on the top 2–3 adjusted-EV packs.

**Suggested priority order:**
1. Paldean Wonders (adj EV=4.20) — most missing cards relative to pool
2. Fantastical Parade (adj EV=3.82) — highest absolute missing count (205)
3. Mew (adj EV=3.78) — small focused pool, very high completion rate

**Important:** EV rankings change as the collection grows. After every 20+ pulls,
re-run `python3 scripts/build_pack_ev.py` and regenerate this report.

**Tradeoff:** Optimizes collection growth but ignores deck-target priority.
If completing a specific chase deck matters more, see Scenario B.

---

## Complete Pack Ranking

| Rank | Pack | Expansion | Adj. EV | Total EV | New EV | Missing | Deck EV | EX EV |
|---|---|---|---|---|---|---|---|---|
| 1 | Paldean Wonders | Paldean Wonders | 4.2019 | 4.9435 | 4.9156 | 128 | 0.0000 | 0.2052 |
| 2 | Fantastical Parade | Fantastical Parade | 3.8206 | 4.4948 | 4.2512 | 205 | 0.0000 | 0.2234 |
| 3 | Mew | Mythical Island | 3.7835 | 4.4512 | 4.2741 | 77 | 0.0000 | 0.0000 |
| 4 | Extradimensional Crisis | Extradimensional Crisis | 3.7062 | 4.3602 | 4.1071 | 90 | 0.0000 | 0.0000 |
| 5 | Mega Altaria | Mega Rising | 3.6754 | 4.3240 | 4.1928 | 119 | 0.0000 | 0.2344 |
| 6 | Lugia | Wisdom of Sea and Sky | 3.6491 | 4.2931 | 4.0705 | 118 | 0.0000 | 0.0000 |
| 7 | Solgaleo | Celestial Guardians | 3.6400 | 4.2823 | 3.9192 | 106 | 0.0611 | 0.0000 |
| 8 | Lunala | Celestial Guardians | 3.6341 | 4.2755 | 4.0833 | 118 | 0.0000 | 0.0000 |
| 9 | Secluded Springs | Secluded Springs | 3.5598 | 4.1880 | 3.9223 | 92 | 0.0000 | 0.0000 |
| 10 | Eevee Grove | Eevee Grove | 3.5594 | 4.1875 | 3.9885 | 90 | 0.0000 | 0.0000 |
| 11 | Palkia | Space-Time Smackdown | 3.5457 | 4.1714 | 4.0011 | 106 | 0.0000 | 0.0000 |
| 12 | Ho-Oh | Wisdom of Sea and Sky | 3.5295 | 4.1523 | 3.8611 | 114 | 0.0000 | 0.0000 |
| 13 | Deluxe Pack: ex | Deluxe Pack: ex | 3.4818 | 4.0962 | 3.7134 | 304 | 0.0746 | 0.0067 |
| 14 | Mega Shine | Mega Shine | 3.4580 | 4.0682 | 3.8570 | 97 | 0.0000 | 0.2115 |
| 15 | Dialga | Space-Time Smackdown | 3.4275 | 4.0323 | 3.8751 | 106 | 0.0000 | 0.0000 |
| 16 | Shining Revelry | Shining Revelry | 3.4215 | 4.0253 | 3.7963 | 92 | 0.0000 | 0.0000 |
| 17 | Mega Blaziken | Mega Rising | 3.4201 | 4.0236 | 3.7119 | 108 | 0.0000 | 0.2344 |
| 18 | Mega Gyarados | Mega Rising | 3.4120 | 4.0142 | 3.8218 | 109 | 0.0059 | 0.2369 |
| 19 | Charizard | Genetic Apex | 3.3401 | 3.9295 | 3.6621 | 97 | 0.0000 | 0.0000 |
| 20 | Pikachu | Genetic Apex | 3.3306 | 3.9184 | 3.6447 | 99 | 0.0000 | 0.0000 |
| 21 | Mewtwo | Genetic Apex | 3.1995 | 3.7641 | 3.3167 | 88 | 0.1028 | 0.0000 |
| 22 | Arceus | Triumphant Light | 3.0068 | 3.5374 | 3.0803 | 71 | 0.0000 | 0.0000 |
| 23 | Pulsing Aura | Pulsing Aura | 1.7232 | 2.0273 | 1.3672 | 93 | 0.0340 | 0.1892 |
| 24 | Crimson Blaze | Crimson Blaze | 1.5145 | 1.7817 | 1.1217 | 39 | 0.1499 | 0.1349 |

---

## Blockers Before Verified Recommendations

| Blocker | Severity | Fix |
|---|---|---|
| Slot rates not verified in-app | **HIGH** | PTCGP app → Pack details → Offering Rates |
| 59 ambiguous collection entries excluded from EV | MEDIUM | Fill data/exports/current_pack_source_review.csv |
| Zygarde ex not in pack_sources (unknown pack) | MEDIUM | Identify Zygarde ex set from external reference |
| Deck completion probability not integrated | LOW | Future: build automated deck scorer |

---

## Next Actions

1. **Verify slot rates in-app** (highest impact) — PTCGP → Pack details → Offering Rates.
   Compare to `slot_rates` in `data/reference/pull_probability_model.json`.
   If they match, set `confidence=verified`, re-run `build_pack_ev.py`, re-run this report.

2. **OR accept inferred confidence** and use Scenario B or C above.

3. **Resolve ambiguous entries** — fill `data/exports/current_pack_source_review.csv`
   to expand EV-ready coverage from 157 to ~216/224 entries.

4. **Identify Zygarde ex pack source** — enables Zygarde ex Fighting deck targeting.

> Rankings are for **informational/planning purposes only** at inferred confidence.
> Verify in-app before treating these as actionable spend decisions.

