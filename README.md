# Pokemon TCG Pocket Collection Database

Personal collection tracker and pack-opening optimizer for Pokémon TCG Pocket.

## Quick Start

```bash
python3 scripts/run_recommendations.py
```

Syncs collection from Pokemon Zone, runs the full EV pipeline, and prints a condensed summary. Full verbose output logged to `data/pipeline.log`.

```
  ✓  Sync collection         588 cards, 272 unique
  ✓  Validate collection     272 entries, total=588
  ✓  Normalize collection    OK
  ✓  Pack coverage           202 direct, 70 ambiguous → resolver
  ✓  Confidence scoring      141 high-conf, 131 queued for resolver
  ✓  Resolve pack sources    272/272 EV-ready
  ✓  Build pack EV           24 packs
  ✓  Build promo EV          21 promo packs
  ✓  Recommendations         OK
  ✓  Spending plan           OK

  Top pack:   Paldean Wonders (adj_ev=4.8900) — 127/131 cards unowned
  Top promo:  Promo Pack A Series Vol. 8 (new_ev=0.9198) — Shop Tokens
  Log:        data/pipeline.log
```

**Flags:**

| Flag | Effect |
|---|---|
| _(none)_ | Full run: headless PZ sync + EV pipeline |
| `--skip-sync` | Skip sync, use current collection.json |
| `--json-import` | Auto-import newest `~/Downloads/pz_collection*.json` |
| `--json-import FILE` | Import specific bookmarklet JSON |
| `--dry-run-sync` | Preview sync diff, stop before EV |
| `--login` | Re-authenticate browser before sync |

---

## Collection

**Source of truth:** `collection.json` — synced from [Pokemon Zone](https://pokemon-zone.com/collection-tracker/).

| Stat | Value |
|---|---|
| Total cards | 588 |
| Unique entries | 272 |
| Last synced | 2026-05-21 |
| Pack-source coverage | 272/272 (100%) EV-ready |

Auth is stored in `data/sync/.auth.json` (gitignored). To re-authenticate:

```bash
python3 scripts/sync_collection.py --curl-import
```

---

## Pipeline Architecture

```
sync_collection.py            ← fetch from Pokemon Zone (stored auth)
validate_current_collection.py
normalize_current_collection.py
current_collection_pack_coverage.py   ← match entries against pack_sources.json
score_pack_source_confidence.py       ← score each match (auto_accept / secondary / low_conf)
resolve_ambiguous_pack_sources.py     ← HP/evolution/PZ-set-code disambiguation
build_pack_ev.py                      ← EV for 24 regular packs
build_promo_pack_ev.py                ← EV for 21 promo packs (Shop Tokens)
generate_pack_recommendation_report.py
generate_hourglass_spending_plan.py
```

**Why coverage + confidence + resolver all run:**
- Coverage identifies which 70 entries have multiple candidate packs (ambiguous)
- Confidence scores all 272 entries; 141 clear, 131 need disambiguation
- Resolver applies 4 passes (HP match → evolution chain → rarity inference → PZ set code) to bring all 272 to EV-ready

---

## Key Outputs

| File | Description |
|---|---|
| `review/inferred_pack_recommendations.md` | Ranked pack list with EV scores and deck-chase guide |
| `review/final_hourglass_spending_plan.md` | Scenario-based spending plan (conservative / moderate / aggressive) |
| `review/promo_pack_ev.md` | Promo pack rankings (Shop Token currency) |
| `review/resolved_pack_sources.md` | Pack-source resolution detail |
| `review/deck_recommendation_validation.md` | Deck buildability report |
| `data/pipeline.log` | Full verbose output from last run (gitignored) |

---

## Reference Data

| File | Contents |
|---|---|
| `data/reference/pack_sources.json` | 3119 card → pack mappings (A1–B3 + PROMO-A/B) |
| `data/reference/pz_pack_odds.json` | PZ per-card drop chances (45 packs: 24 regular + 21 promo) |
| `data/reference/pull_probability_model.json` | Pull rate model v0.6.0, `pz_verified` |

**Pull rate source:** Pokemon Zone pack pages (`?show_pack_odds=1&show_pack_slot_odds=1`). All 24 regular packs and 21 promo packs are `pz_verified`.

---

## EV Model

```
EV per pack = Σ (p_pull × value_of_next_copy)

value_of_next_copy:
  owned=0, not ex  →  1.0
  owned=0, ex      →  2.0
  owned=1, not ex  →  0.4
  owned=1, ex      →  1.4
  owned≥2          →  0.0

adj_ev = pack_total_ev × confidence_multiplier  (1.0 for pz_verified)
```

---

## Manual Tools

```bash
# Re-run individual pipeline steps
python3 scripts/current_collection_pack_coverage.py
python3 scripts/score_pack_source_confidence.py
python3 scripts/resolve_ambiguous_pack_sources.py

# Manual pack-source confirmation (when resolver can't disambiguate)
python3 scripts/create_current_pack_review.py
python3 scripts/apply_current_pack_confirmations.py --dry-run
python3 scripts/apply_current_pack_confirmations.py --apply

# Deck validation
python3 scripts/validate_deck_recommendations.py

# Pack source reference rebuild
python3 scripts/build_pack_sources.py
python3 scripts/validate_pack_sources.py
```

---

## Sync Notes

- Rate-limited to once per ~24h by Pokemon Zone (skips gracefully if too early)
- Chrome136 impersonation for both GET and POST (prevents Cloudflare 403)
- Raw API response not committed (`data/sync/last_sync_raw.json` gitignored)
- Player sync triggered automatically before each collection fetch

See `PROJECT.md` for full project context and decision log.
