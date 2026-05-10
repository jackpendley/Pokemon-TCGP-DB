# Recommendation Readiness

This document describes what data is required before pack-opening and deck-building
recommendations can be made reliably, lists current blockers, and outlines the next phase.

> **Pack-opening and deck-building recommendations are intentionally deferred.**
> Do not generate recommendations until all blockers below are resolved.

---

## Current Status (as of 2026-05-10)

| Metric | Value |
|---|---|
| Provisional baseline | 329 cards (211 unique entries) |
| Original app count | 331 (not forced) |
| Validation | PASS at 329 |
| Metadata enrichment | 179 / 211 cards enriched from Limitless TCG Pocket reference |
| Readiness score | ~50% (see `review/collection_analytics.md` for current score) |
| pack_sources.json | **Built** — 1483 records across 7 sets (A4b, B1, B1a, B2, B2a, B2b, B3) |
| Owned pack coverage | 93/211 exact (44.1%); 36 agreed name-match; 62 ambiguous; 20 no match |
| source_packs in cards.json | Added for 93 exact-match cards |

### Pack Source Coverage Reports

- `review/owned_pack_coverage.md` — full coverage breakdown
- `data/exports/owned_pack_coverage.json` — machine-readable

---

## What Data Is Required Before Pack Recommendations

### Must-have

| Data | Current State | Source |
|---|---|---|
| Owned cards with quantities | Complete (329 cards, 211 entries) | cards.json |
| Set / expansion identity | **Incomplete** — set_code enriched for ~108 cards; set_or_pack still unknown for all | Needs manual review or further enrichment |
| Pack availability by set | **Missing** — pack_sources.json does not exist | Build from Limitless TCG Pocket |
| Rarity per card | **Partial** — 117/211 enriched; 94 still unknown | Further enrichment from external reference |
| Card category | **Partial** — 179/211 known; 32 still unknown | Further enrichment |

### Nice-to-have

| Data | Notes |
|---|---|
| Current app pack offerings | Which packs are available to open today |
| Collection goals | Which cards the user is prioritizing |
| Pack pull rate tables | Probability tables per pack per rarity tier |

### Blocker: Pack Source Mapping

A `data/reference/pack_sources.json` file is required to map each card to which
pack it can be obtained from. Without this, it is impossible to recommend "open pack X
to get card Y."

The schema for this file is defined in `data/reference/pack_sources.schema.json`.
See `review/pack_source_mapping_plan.md` for how to build it.

---

## What Data Is Required Before Deck Recommendations

### Must-have

| Data | Current State |
|---|---|
| Owned Pokémon cards | Partially known — 179/211 cards have card_category enriched |
| Trainer / Supporter / Item cards | Partially known — same enrichment coverage |
| EX / Mega cards | 8 cards marked is_ex=true in cards.json |
| Evolution lines | stage field enriched for ~167 cards; some still unknown |
| Type coverage | pokemon_type enriched for ~167 non-trainer cards |
| Current meta data | **Not available** — requires external meta research |
| Deck legality / rules | **Not integrated** — deck size, format rules not yet modeled |

### Nice-to-have

| Data | Notes |
|---|---|
| Win rate data by deck archetype | From tournament results on Limitless TCG Pocket |
| Missing card counts per archetype | How many cards away from completing a meta deck |

---

## Current Blockers

1. **set_or_pack is unknown for all 211 cards** — `set_code` has been enriched for 93
   cards and `source_packs` added, but `set_or_pack` (the human-readable set/pack name)
   remains `unknown` in cards.json. For the remaining 118 cards without set_code,
   pack source cannot be definitively determined from name alone (62 ambiguous, 20 no match).

2. **Pack coverage is only 44% by exact match** — 118 owned cards still have no confirmed
   pack assignment. Name-only matches add 36 more with medium confidence, but 62 are
   ambiguous (same name appears in multiple packs across sets) and 20 have no reference match.

3. **special_type is unknown for 209/211 cards** — Full art, illustration rare, special art,
   immersive, and crown/gold distinctions are not captured. Affects recommendation quality
   for high-rarity targeted pulls.

4. **rarity is unknown for 94/211 cards** — These are cards where the external reference
   had multiple matches with disagreeing rarities, or no match at all. Rarity is needed
   to estimate the value of opening a specific pack.

5. **No pack pull probability model** — Rarity tier pull rates by pack are not yet modeled.
   This is needed to calculate expected value of opening any given pack.

6. **No meta data** — Current meta deck archetypes, win rates, and tier lists are not
   integrated. Deck recommendations cannot be confident without this.

---

## Suggested Next Phase

### Phase A: Build pack/source mapping

1. Use `data/reference/pack_sources.schema.json` as the target structure.
2. Retrieve pack source data from Limitless TCG Pocket
   (`https://pocket.limitlesstcg.com/cards`) for each set (A4b, B1, B1a, B2, B2a, B2b, B3).
3. Map each `set_code + card_number` to the pack(s) it is available in.
4. Store as `data/reference/pack_sources.json`.
5. Validate with `python3 scripts/validate_pack_sources.py`.

### Phase B: Resolve special_type for high-rarity cards

1. Focus on cards where `rarity` is `one_star`, `double_star`, `triple_star`, `four_diamond`, or `crown`.
2. Cross-reference with the Limitless card images or Game8 full-art list.
3. Update `special_type` for confirmed special cards.

### Phase C: Integrate meta tier list

1. Retrieve current meta tier list from Limitless TCG Pocket tournament data.
2. Build a `data/reference/meta_decks.json` with top archetypes and their required cards.
3. Cross-reference with `cards.json` to identify missing cards per archetype.

### Phase D: Generate recommendations

Only after Phases A–C are substantially complete, run the recommendation engine.

---

## Trusted External Sources for Next Phase

| Source | Use |
|---|---|
| `https://pocket.limitlesstcg.com/cards` | Set/pack/card metadata, pull rates |
| `https://pocket.limitlesstcg.com/tournaments` | Meta tier lists and deck archetypes |
| `https://game8.co/games/Pokemon-TCG-Pocket/archives/482685` | Complete card list reference |
| `https://game8.co/games/Pokemon-TCG-Pocket/archives/483152` | Full art / special card list |
