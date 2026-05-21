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
| Report generated | 2026-05-21T04:14:22+00:00 |
| Model confidence | **third_party_verified_with_in_app_anchor** (not official in-app verified) |
| Collection total | 578 cards (380 validated) |
| EV-ready entries | 157/224 (108 auto-accept + 49 secondary evidence) |
| Excluded from EV | 67/224 (59 low-confidence + 8 unresolved) |
| Packs ranked | 24 |
| Packs blocked | 0 |

---

## Top 5 Packs — All Metrics

| Rank | Pack | Expansion | Adj. EV | Total EV | New EV | Deck EV | EX EV | Missing |
|---|---|---|---|---|---|---|---|---|
| 1 | **Paldean Wonders** | Paldean Wonders | 4.1663 | 4.9016 | 4.8458 | 0.0000 | 0.2052 | 127 |
| 2 | **Extradimensional Crisis** | Extradimensional Crisis | 3.6448 | 4.2881 | 4.0909 | 0.0000 | 0.0000 | 88 |
| 3 | **Solgaleo** | Celestial Guardians | 3.5752 | 4.2062 | 3.8511 | 0.0611 | 0.0000 | 105 |
| 4 | **Mew** | Mythical Island | 3.5644 | 4.1934 | 3.9903 | 0.0000 | 0.0000 | 73 |
| 5 | **Lugia** | Wisdom of Sea and Sky | 3.5579 | 4.1858 | 3.9532 | 0.0000 | 0.0000 | 113 |

---

## Recommendation Buckets

### Best Overall Inferred EV

These packs have the highest expected number of new unique cards per pull,
adjusted for inferred-rate uncertainty.

| Rank | Pack | Adj. EV | Why |
|---|---|---|---|
| 1 | Paldean Wonders | 4.1663 | Large pool, very few owned (3/131). Almost every pull is new. |
| 2 | Extradimensional Crisis | 3.6448 | Medium pool, low ownership (13/103). Consistent new-card rate. |
| 3 | Solgaleo | 3.5752 | High new-card EV relative to pool size. |
| 4 | Mew | 3.5644 | Small dense pool (86 cards), 77 missing — high hit rate per pull. |
| 5 | Lugia | 3.5579 | High new-card EV relative to pool size. |

### Best for Collection Completion

Ranked by new_card_ev — these packs return the most new unique cards per pull.

| Rank | Pack | New Card EV | Missing in Pool |
|---|---|---|---|
| 1 | Paldean Wonders | 4.8458 | 127 |
| 2 | Extradimensional Crisis | 4.0909 | 88 |
| 3 | Mega Altaria | 4.0020 | 115 |
| 4 | Mew | 3.9903 | 73 |
| 5 | Lugia | 3.9532 | 113 |

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
| 4 | Mega Shine | 0.2115 |
| 5 | Fantastical Parade | 0.2061 |

### Packs to Deprioritize

These packs have the lowest adjusted EV — most cards in the pool are already owned.

| Rank | Pack | Adj. EV | Owned/Pool | Notes |
|---|---|---|---|---|
| 1 | Pulsing Aura | 0.9321 | 169/234 | Contains Magnezone ex — open only if chasing that deck |
| 2 | Crimson Blaze | 1.4932 | 64/103 | High deck-target value offsets low general EV — open only if chasing Ivysaur |
| 3 | Arceus | 2.8383 | 28/96 | Mid-range owned ratio |
| 4 | Mewtwo | 3.0077 | 42/126 | Higher EV than Crimson Blaze/Pulsing Aura; only deprioritized vs top packs |
| 5 | Charizard | 3.1789 | 34/127 | Low new-card return relative to pool |

---

## Pack Detail — Top 5 by Adjusted EV

**Paldean Wonders** (Paldean Wonders)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **4.1663** |
| Total EV (raw) | 4.9016 |
| New-card EV | 4.8458 |
| EX-card EV | 0.2052 |
| Deck target EV | 0.0000 |
| Pool size | 131 cards |
| Already owned in pool | 4 |
| Missing from pool | **127** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Sprigatito | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Floragato | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Tarountula | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Nymble | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |
| Smoliv | one_diamond | 0 | 0.06973 | 1.00 | 0.06973 |

---

**Extradimensional Crisis** (Extradimensional Crisis)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.6448** |
| Total EV (raw) | 4.2881 |
| New-card EV | 4.0909 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0000 |
| Pool size | 103 cards |
| Already owned in pool | 15 |
| Missing from pool | **88** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Petilil | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Lilligant | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Rowlet | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Kartana | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Mantine | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |

---

**Solgaleo** (Celestial Guardians)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.5752** |
| Total EV (raw) | 4.2062 |
| New-card EV | 3.8511 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0611 |
| Pool size | 140 cards |
| Already owned in pool | 35 |
| Missing from pool | **105** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Phantump | one_diamond | 0 | 0.06815 | 1.00 | 0.06815 |
| Rowlet | one_diamond | 0 | 0.06815 | 1.00 | 0.06815 |
| Bounsweet | one_diamond | 0 | 0.06815 | 1.00 | 0.06815 |
| Wimpod | one_diamond | 0 | 0.06815 | 1.00 | 0.06815 |
| Fletchinder | one_diamond | 0 | 0.06815 | 1.00 | 0.06815 |

---

**Mew** (Mythical Island)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.5644** |
| Total EV (raw) | 4.1934 |
| New-card EV | 3.9903 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0000 |
| Pool size | 86 cards |
| Already owned in pool | 13 |
| Missing from pool | **73** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Snivy | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Morelull | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Ponyta | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Salandit | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |
| Salazzle | one_diamond | 0 | 0.09370 | 1.00 | 0.09370 |

---

**Lugia** (Wisdom of Sea and Sky)

| Metric | Value |
|---|---|
| Adjusted EV (×0.85) | **3.5579** |
| Total EV (raw) | 4.1858 |
| New-card EV | 3.9532 |
| EX-card EV | 0.0000 |
| Deck target EV | 0.0000 |
| Pool size | 136 cards |
| Already owned in pool | 23 |
| Missing from pool | **113** |

Top EV cards in this pack:

| Card | Rarity | Owned | Pull P | Value | EV |
|---|---|---|---|---|---|
| Oddish | one_diamond | 0 | 0.07139 | 1.00 | 0.07139 |
| Scyther | one_diamond | 0 | 0.07139 | 1.00 | 0.07139 |
| Pinsir | one_diamond | 0 | 0.07139 | 1.00 | 0.07139 |
| Chikorita | one_diamond | 0 | 0.07139 | 1.00 | 0.07139 |
| Ledian | one_diamond | 0 | 0.07139 | 1.00 | 0.07139 |

---

## Chase Deck Pack Guide

| Chase Deck | Missing Card | Short By | Best Pack | Pack EV | Pull Prob | Notes |
|---|---|---|---|---|---|---|
| Mega Venusaur ex | Ivysaur | 1 | Crimson Blaze | 0.14992 | 0.06247 |  |
| Incineroar ex | Incineroar ex | 1 | Solgaleo | 0.03996 | 0.01665 |  |
| Zygarde ex Fighting | Zygarde ex | 1 | **UNKNOWN** | N/A | N/A | PROMO-B card — cannot be obtained from any pack; must be acquired through events or missions |
| Magnezone ex (Clemont Engine) | Magnezone ex | 1 | Pulsing Aura | 0.02832 | 0.00833 |  |

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
| 1 | Paldean Wonders | Paldean Wonders | 4.1663 | 4.9016 | 4.8458 | 127 | 0.0000 | 0.2052 |
| 2 | Extradimensional Crisis | Extradimensional Crisis | 3.6448 | 4.2881 | 4.0909 | 88 | 0.0000 | 0.0000 |
| 3 | Solgaleo | Celestial Guardians | 3.5752 | 4.2062 | 3.8511 | 105 | 0.0611 | 0.0000 |
| 4 | Mew | Mythical Island | 3.5644 | 4.1934 | 3.9903 | 73 | 0.0000 | 0.0000 |
| 5 | Lugia | Wisdom of Sea and Sky | 3.5579 | 4.1858 | 3.9532 | 113 | 0.0000 | 0.0000 |
| 6 | Mega Altaria | Mega Rising | 3.5182 | 4.1391 | 4.0020 | 115 | 0.0000 | 0.2344 |
| 7 | Lunala | Celestial Guardians | 3.5085 | 4.1276 | 3.9411 | 115 | 0.0000 | 0.0000 |
| 8 | Fantastical Parade | Fantastical Parade | 3.4858 | 4.1009 | 3.7340 | 185 | 0.0000 | 0.2061 |
| 9 | Palkia | Space-Time Smackdown | 3.4382 | 4.0449 | 3.8913 | 104 | 0.0000 | 0.0000 |
| 10 | Ho-Oh | Wisdom of Sea and Sky | 3.4256 | 4.0301 | 3.8016 | 105 | 0.0000 | 0.0000 |
| 11 | Shining Revelry | Shining Revelry | 3.3983 | 3.9980 | 3.7963 | 92 | 0.0000 | 0.0000 |
| 12 | Eevee Grove | Eevee Grove | 3.3710 | 3.9659 | 3.8059 | 84 | 0.0000 | 0.0000 |
| 13 | Mega Shine | Mega Shine | 3.3539 | 3.9457 | 3.6964 | 94 | 0.0000 | 0.2115 |
| 14 | Dialga | Space-Time Smackdown | 3.3057 | 3.8890 | 3.7526 | 101 | 0.0000 | 0.0000 |
| 15 | Mega Blaziken | Mega Rising | 3.2697 | 3.8466 | 3.5895 | 106 | 0.0000 | 0.2344 |
| 16 | Secluded Springs | Secluded Springs | 3.2668 | 3.8433 | 3.6412 | 89 | 0.0000 | 0.0000 |
| 17 | Pikachu | Genetic Apex | 3.2348 | 3.8056 | 3.6269 | 98 | 0.0000 | 0.0000 |
| 18 | Mega Gyarados | Mega Rising | 3.2177 | 3.7856 | 3.6237 | 104 | 0.0059 | 0.2369 |
| 19 | Deluxe Pack: ex | Deluxe Pack: ex | 3.2089 | 3.7752 | 3.3690 | 281 | 0.0746 | 0.0067 |
| 20 | Charizard | Genetic Apex | 3.1789 | 3.7399 | 3.4660 | 93 | 0.0000 | 0.0000 |
| 21 | Mewtwo | Genetic Apex | 3.0077 | 3.5384 | 3.1798 | 84 | 0.1028 | 0.0000 |
| 22 | Arceus | Triumphant Light | 2.8383 | 3.3392 | 2.9819 | 68 | 0.0000 | 0.0000 |
| 23 | Crimson Blaze | Crimson Blaze | 1.4932 | 1.7567 | 1.1216 | 39 | 0.1499 | 0.1349 |
| 24 | Pulsing Aura | Pulsing Aura | 0.9321 | 1.0966 | 0.7347 | 65 | 0.0340 | 0.1692 |

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

