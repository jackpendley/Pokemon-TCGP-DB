# Recommendation Readiness

This document describes what data is required before pack-opening and deck-building
recommendations can be made reliably, lists current blockers, and outlines the next phase.

---

## Current 380-Card Recommendation Baseline (2026-05-11)

`collection.json` is the active exact collection. Validates at exactly 380 cards.

| Metric | Value |
|---|---|
| Active collection file | `collection.json` |
| Meta declared total | 380 |
| Actual verified count | **380 ✅** |
| Unique entries | 224 |
| Screenshots | 26 files (IMG_1556–IMG_1581), 232 card slots |
| Structural consistency | ✅ Screenshots structurally consistent with 224 unique entries |
| Deck validation | 4/8 decks fully buildable; 4 chase decks each 1 card short |
| Buildable decks | Mega Charizard Y ex (S), Victini + Darmanitan (A), Crobat Darkness Pivot (A), Staraptor Blitz (B+) |
| Chase decks | Mega Venusaur ex (−1 Ivysaur), Incineroar ex (−1 ex), Zygarde ex (−1 ex), Magnezone ex (−1 ex) |

Run full validation suite:
```bash
python3 scripts/validate_current_collection.py --expected-total 380
python3 scripts/normalize_current_collection.py
python3 scripts/inventory_screenshots.py
python3 scripts/reconcile_current_collection_sources.py
python3 scripts/validate_deck_recommendations.py
```

### Pack-Source Coverage (2026-05-11)

| Metric | Value |
|---|---|
| Pack-source DB | `pack_sources.json` (3110 records, 17 expansions) |
| Entries resolved | **157/224 (70%)** |
| Exact match | 108 entries |
| Unanimous pack | 49 entries |
| Ambiguous cross-expansion | 59 entries — need set/card-number confirmation |
| No match in pack_sources | 3 entries (Zygarde forms — not in Limitless DB) |
| Known trainer gap | 5 entries (Potion, X Speed, Red Card, Hand Scope, Pokédex) |

Coverage reports:
- `review/current_collection_pack_coverage.md`
- `data/current/current_collection_pack_coverage.json`
- `data/exports/current_collection_pack_coverage.csv`

Manual review package (67 unresolved entries):
- `review/current_pack_source_review.md` — per-card candidate list with app lookup instructions
- `data/exports/current_pack_source_review.csv` — fill `confirmed_set_code`, `confirmed_card_number`, `confirmed_yes_no`
- `data/exports/current_pack_source_review.json` — machine-readable review data

Apply after filling CSV:
```bash
python3 scripts/apply_current_pack_confirmations.py --dry-run
python3 scripts/apply_current_pack_confirmations.py --apply
```

### Remaining blockers before automated pack recommendations

1. **67 unresolved pack-source mappings** — 59 ambiguous (cross-expansion), 3 Zygarde no-match, 5 known trainer gaps. Resolve via review CSV to enable accurate pack EV.
2. **Pull probability model** — rarity tier pull rates by pack not yet modeled.
3. **Pack-source mapping for Zygarde** — Zygarde 10%/50%/ex not in current Limitless data; needs external set reference.
4. **Current meta/tier data** — deck recommendations are not yet meta-aware.
5. **Automated deck scorer** — `deck-recommendations.jsx` is a manual prototype.

### Recommended next phase

Fill `data/exports/current_pack_source_review.csv` with confirmed set_code + card_number for each ambiguous card, then run the apply script. Once coverage is ≥90%, build the pull probability model and pack EV scorer.

---

> **Pack-opening and deck-building recommendations are intentionally deferred.**
> Do not generate recommendations until pack-source coverage is substantially resolved.
> The 380-card baseline is validated; 70% of cards already have clear pack assignments.

---

## Current Status (as of 2026-05-11)

| Metric | Value |
|---|---|
| Provisional baseline | 329 cards (211 unique entries) |
| Original app count | 331 (not forced) |
| Validation | PASS at 329 |
| Metadata enrichment | 179 / 211 cards enriched from Limitless TCG Pocket reference |
| Readiness score | ~50% (see `review/collection_analytics.md` for current score) |
| pack_sources.json | **Expanded** — 3110 records across all 17 sets (A1–A4a, A4b, B1–B3) |
| Owned pack coverage | **166/211 exact (78.7%)**; 27 agreed name-match; **10 ambiguous**; 8 no-match |
| source_packs in cards.json | **193/211** (93 enrichment-phase + 27 rule-resolved + **73 user-confirmed**); 18 still unresolved |
| Pack coverage resolution | Rule D: 27 cards; 73 user-confirmed via manual review CSV (2026-05-11) |
| Remaining ambiguous (10) | Giovanni, Sabrina, Leaf, Cyrus, Rare Candy, Lillie, Giant Cape, Marowak, Bulbasaur (A1/A4b variant), Farfetch'd — each may be 2 owned versions; needs per-card quantity split to resolve |
| No-match (8) | Urshifu (form variant), Potion/X Speed/Hand Scope/Pokédex/Red Card (not in Limitless DB), Zygarde (set unknown) |

### Coverage Change Summary

| Phase | Exact | Agreed | Ambiguous | No-match | Broad % |
|---|---|---|---|---|---|
| Before user confirmations | 93 | 27 | 83 | 8 | 56.9% |
| After 73 user confirmations | 166 | 27 | 10 | 8 | **91.5%** |

### Pack Source Coverage Reports

- `review/owned_pack_coverage.md` — full coverage breakdown
- `data/exports/owned_pack_coverage.json` — machine-readable

### Ambiguous Pack Review Package

- `review/ambiguous_cards_review.md` — grouped review with how-to instructions (83 cards)
- `data/exports/ambiguous_cards_review.csv` — fill confirmed_set_code + confirmed_card_number + confirmed_yes_no
- `data/exports/ambiguous_cards_review.json` — full candidate lists
- `review/no_match_cards_review.md` — review guide for 8 no-match cards
- `data/exports/no_match_cards_review.csv` — fill confirmed columns
- `data/exports/no_match_cards_review.json` — no-match card details

Apply confirmations after filling the CSV:

```bash
python3 scripts/apply_ambiguous_confirmations.py --dry-run
python3 scripts/apply_ambiguous_confirmations.py --apply
```

### Skipped Multi-Value Review Package (10 cards)

73 of 83 ambiguous cards were resolved. 10 were skipped because the filled CSV used
multi-value format (e.g. `A1/A4b`). A focused review package exists for these:

- `review/skipped_multi_value_review.md` — per-card analysis and fill instructions
- `data/exports/skipped_multi_value_review.csv` — fill `confirmed_action` + relevant fields
- `data/exports/skipped_multi_value_review.json` — full candidate data

Apply after filling:

```bash
python3 scripts/apply_skipped_multi_value_confirmations.py --dry-run
python3 scripts/apply_skipped_multi_value_confirmations.py --apply
```

Coverage remains **193/211 (91.5%)** until these 10 cards are resolved.
Pull probability model will be most accurate after these are confirmed.

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

1. **10 cards still have no definitive pack assignment** — 73 ambiguous resolved by user
   confirmation (2026-05-11). Remaining 10 may represent 2 owned versions each (regular + special-art
   A4b trainers, or A1/A4b variant Pokémon). Cannot split without per-card quantities.
   8 have no Limitless reference (common trainer items, Urshifu form, Zygarde unidentified set).

2. **Pack coverage is 91.5% broad (193/211)** — 93 enrichment-phase exact + 27 rule-resolved +
   73 user-confirmed. 10 remain ambiguous (Giovanni, Sabrina, Leaf, Cyrus, Rare Candy, Lillie,
   Giant Cape, Marowak, Bulbasaur v2, Farfetch'd). 8 no Limitless reference.

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
