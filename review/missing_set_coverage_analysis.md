# Missing Set Coverage Analysis

Generated: 2026-05-10

## Current pack_sources.json Coverage (Before Expansion)

| Set Code | Expansion Name | Type | Records | Status |
|---|---|---|---|---|
| A4b | Deluxe Pack: ex | Single-pack | 333 | Partial — 46 cards missing (334–379) |
| B1 | Mega Rising | Multi-pack | 331 | Complete |
| B1a | Crimson Blaze | Single-pack | 103 | Complete |
| B2 | Fantastical Parade | Single-pack | 234 | Complete |
| B2a | Paldean Wonders | Single-pack | 131 | Complete |
| B2b | Mega Shine | Single-pack | 117 | Complete |
| B3 | Pulsing Aura | Single-pack | 234 | Complete |
| **Total** | | | **1483** | |

---

## Sets Available in Limitless Index but Not in pack_sources.json

| Set Code | Expansion Name | Type | Cards | Priority |
|---|---|---|---|---|
| A1 | Genetic Apex | Multi-pack (Charizard, Pikachu, Mewtwo) | 286 | High — covers Gen 1 Pokémon + basic trainers |
| A1a | Mythical Island | Single-pack (Mew) | 86 | Medium |
| A2 | Space-Time Smackdown | Multi-pack (Dialga, Palkia) | 207 | High — covers Gen 4 Pokémon, some trainers |
| A2a | Triumphant Light | Single-pack | 96 | Low |
| A2b | Shining Revelry | Single-pack | 111 | Low |
| A3 | Celestial Guardians | Multi-pack (Ho-Oh, Lugia) | 239 | Medium |
| A3a | Extradimensional Crisis | Single-pack | 103 | Low |
| A3b | Eevee Grove | Single-pack | 107 | Low |
| A4 | Wisdom of Sea and Sky | Multi-pack (Kyogre, Groudon) | 241 | Medium |
| A4a | Secluded Springs | Single-pack | 105 | Low |
| **Total** | | | **1581** | |

---

## No-Match Card Analysis (20 owned entries with 0 records in pack_sources)

### Confirmed in A4b 334–379 (already being fetched)

These cards were in the uncached tail of A4b. They are special-art or immersive versions:

| Card Name | A4b Cards | Expected pack_name |
|---|---|---|
| Giovanni | #334, #335 | Deluxe Pack: ex |
| Sabrina | #338, #339 | Deluxe Pack: ex |
| Leaf | #346, #347 | Deluxe Pack: ex |
| Lillie | #348, #349 (+ #374) | Deluxe Pack: ex |
| Professor's Research | #373 | Deluxe Pack: ex |

Note: these are special-art trainers. The base versions (normal rarity) of these cards also exist
in older sets (A1, A2) at lower card numbers. Whether the user's card is the special-art A4b
version or the older base version is unknown without set_code + card_number.

### Likely in A1 (Genetic Apex)

| Card Name | Expected Set | Notes |
|---|---|---|
| Venonat | A1 | Gen 1 Bug Pokémon, probably Pikachu or Mewtwo pack |
| Rattata | A1 | Gen 1 Normal Pokémon |
| Raticate | A1 | Gen 1 Normal Pokémon |

These are likely unique to A1 (no reprints in A4b–B3). Adding A1 data should resolve them.

### Trainers Present in Multiple Sets (will become ambiguous)

| Card Name | Appears In | Outcome |
|---|---|---|
| Potion | A4b #373 area + every set | Ambiguous: different pack per set |
| X Speed | A4b + multiple sets | Ambiguous |
| Hand Scope | A4b + some sets | Ambiguous |
| Pokédex | A4b + multiple sets | Ambiguous |
| Poké Ball | A4b + every set | Ambiguous |
| Red Card | A4b + multiple sets | Ambiguous |

These are common trainer items that appear in virtually every set. Even after expanding coverage,
they will remain ambiguous across sets with different pack names.

### Unknown Set Placement

| Card Name | Notes |
|---|---|
| Eelektross | Gen 5 (Unova); likely A2 or A3 |
| Zygarde (x2) | Gen 6 (Kalos); likely A3 or a sub-set |

### Known Unresolvable

| Card Name | Reason |
|---|---|
| Incineroar | is_ex ambiguity: Incineroar ex appears in B1 (Mega Gyarados) and A4b — 2 packs |
| Urshifu | Form variant: Rapid Strike vs Single Strike — requires visual confirmation |
| Marowak | Already resolved via Rule EX (Marowak ex, A4b). Shows as no-match only in owned_pack_coverage because owned card name is "Marowak", not "Marowak ex". |

---

## Resolution Results After Expansion

| Category | Before | After | Change |
|---|---|---|---|
| Exact match (high/medium, phase 2) | 93 | 93 | — |
| Rule D resolved (medium) | 37 | 27 | -10 net (14 stale cleared; 4 new added) |
| source_packs total | 130 | 120 | -10 (accuracy correction; stale data removed) |
| Still ambiguous | 62 | 83 | +21 (former no-match and stale agreed cards become correctly ambiguous) |
| No match | 20 | 8 | -12 (moved to ambiguous or resolved) |

Newly resolved (4): Incineroar (Eevee Grove), Venonat (Mewtwo pack), Poké Ball (Shining Revelry), Professor's Research (Deluxe Pack: ex)

Stale resolutions cleared (14): Marowak, Vaporeon, Charizard, Cyrus, Rare Candy, Giant Cape, Quagsire, Malamar, Bisharp, Farfetch'd, Cherubi, Buneary, Seviper, Chansey — all now correctly marked as ambiguous

No-match → ambiguous (12 cards moved): Rattata, Raticate, Giovanni, Sabrina, Leaf, Lillie, Marowak, Incineroar, Eelektross, and others now have records in pack_sources but across multiple sets with different packs

---

## Fetch Plan

Files to fetch: 1627 total
- A4b cards 334–379: 46 files (fast win — covers trainer special arts)
- A1–A4a cards: 1581 files (covers older Pokémon)
- Grid pages: 10 files (A1–A4a)
- Estimated time: ~16 minutes at 0.6s/request

Script: `python3 scripts/fetch_missing_html.py`

---

## Recommendation for Next Steps

| Step | Action | Priority |
|---|---|---|
| Immediate | Rebuild pack_sources.json after fetch completes | Required |
| Immediate | Rerun resolve_pack_coverage.py | Required |
| After rebuild | Update recommendation_readiness.md with new counts | Required |
| Future | Manual review package for ambiguous trainer items | Low — won't resolve without card number |
| Future | Expand rule set to handle "appears in all sets as shared" trainers | Medium |
| Future | Build pull probability model (Phase D in roadmap) | After coverage improves |

