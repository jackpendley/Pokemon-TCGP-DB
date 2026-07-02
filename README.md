# Pokemon TCG Pocket Collection Database

Personal collection tracker and pack-opening optimizer for Pokémon TCG Pocket.

## Quick Start

```bash
python3 scripts/run_recommendations.py
```

Syncs collection from Pokemon Zone, runs the full EV pipeline, and prints a condensed summary. Full verbose output logged to `data/pipeline.log`.

```
  ✓  Sync collection         1060 cards, 512 unique
  ✓  Validate collection     512 entries, total=1060
  ✓  Normalize collection    OK
  ✓  Build pack EV           25 packs
  ✓  Build promo EV          21 promo packs
  ✓  Recommendations         OK

  Top pack:   Deluxe Pack: ex (unified=70.3026) — 228/279 cards unowned
  Top promo:  Promo Pack A Series Vol. 8 (new_ev=0.9198) — Shop Tokens
  Pack Hourglasses: 1260  → buy 10x Deluxe Pack: ex (costs 120 ⧗), then re-run
  Shop Tickets:     347
  Log:        data/pipeline.log
```

**Flags:**

| Flag | Effect |
|---|---|
| _(none)_ | Full run: headless PZ sync + EV pipeline |
| `--skip-sync` | Skip sync, use current `collection.json` |
| `--json-import` | Auto-import newest `~/Downloads/pz_collection*.json` |
| `--json-import FILE` | Import specific bookmarklet JSON |
| `--dry-run-sync` | Preview sync diff, stop before EV |
| `--login` | Re-authenticate browser before sync |

---

## Collection

**Source of truth:** `collection.json` — synced from [Pokemon Zone](https://pokemon-zone.com/collection-tracker/).

| Stat | Value |
|---|---|
| Total cards | 1060 |
| Unique entries | 512 |
| Last synced | 2026-06-04 |

---

## Sync Options

### Option A — Browser bookmarklet (recommended)

Add this as a browser bookmark named "PZ Sync":

```
javascript:(async()=>{const b='https://www.pokemon-zone.com/api/';const[cr,or]=await Promise.all([fetch(b+'cards/search/'),fetch(b+'players/mine/')]);const cb=await cr.json();const ob=await or.json();const cat={};for(const i of(cb.data?.results??cb.data??[])){const m=(i.url||'').match(/\/cards\/[^/]+\/(\d+)\//);cat[i.cardDefKey]={name:i.name,set_code:i.expansionId||'',card_number:m?parseInt(m[1]):null}}const cards=[];for(const c of(ob.data?.cards??[])){if(!c.amount||c.amount<=0)continue;const info=cat[c.cardId];if(!info)continue;const sc=((c.expansionIds||[])[0]||info.set_code||'').toUpperCase();cards.push({cardName:info.name,setCode:sc,cardNumber:info.card_number,ownedCount:c.amount})}const bl=new Blob([JSON.stringify(cards,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download='pz_collection.json';a.click();alert('Done: '+cards.length+' cards downloaded as pz_collection.json')})();
```

To install in Chrome: Bookmarks → Bookmark Manager (Cmd+Option+B) → three-dot menu → Add new bookmark → paste the full `javascript:` one-liner as the URL.

Usage:
1. Open `https://www.pokemon-zone.com/collection-tracker/` (must be logged in)
2. Click the "PZ Sync" bookmark — `pz_collection.json` downloads automatically
3. Run: `python3 scripts/run_recommendations.py --json-import`

### Option B — Stored auth / headless (default pipeline)

```bash
# First-time setup — paste a cURL command copied from DevTools:
python3 scripts/sync_collection.py --curl-import

# All subsequent syncs (Chrome TLS impersonation via curl-cffi):
python3 scripts/run_recommendations.py
```

Auth stored in `data/sync/.auth.json` (gitignored). Re-run `--curl-import` when auth expires.

### Option C — HAR import (fallback)

```bash
# 1. Open https://www.pokemon-zone.com/collection-tracker/ (logged in)
# 2. DevTools → Network tab → reload → wait for cards → Export HAR
python3 scripts/run_recommendations.py --json-import ~/Downloads/pz_collection.json
```

---

## Pipeline Architecture

```
sync_collection.py              ← fetch from Pokemon Zone (stored auth or bookmarklet JSON)
validate_current_collection.py  ← sum(count) == meta.total_cards
normalize_current_collection.py ← clean JSON, no comments
build_pack_ev.py                ← EV for 24 regular packs
build_promo_pack_ev.py          ← EV for 21 promo packs (Shop Tokens)
generate_pack_recommendation_report.py
```

EV is computed directly from `pz_pack_odds.json` keyed by `(set_code, card_number)` — no fuzzy matching or confidence scoring. Pokemon Zone provides exact card identity on sync.

---

## Key Outputs

These are **generated locally on every run** (regenerated from `collection.json` + `data/reference/*`)
and are **gitignored** — `data/current/`, `data/exports/`, and `review/` are build artifacts, not
version-controlled. `collection.json` is the tracked source of truth; commit it when your cards change.

| File | Description |
|---|---|
| `review/inferred_pack_recommendations.md` | Ranked pack list with EV scores and deck-chase guide |
| `review/promo_pack_ev.md` | Promo pack rankings (Shop Token currency) |
| `data/pipeline.log` | Full verbose output from last run (gitignored) |

---

## EV Model

```
EV per pack = Σ (p_pull × value_of_next_copy)

value_of_next_copy (per printing — each set coord counted independently):
  owned=0  →  1.0 + RARITY_BONUS[rarity]  (ultra_rare=10.0, immersive=7.5 … uncommon=0.0)
  owned=1  →  0.4
  owned≥2  →  0.0

unified_score = new_card_ev_10x×1.0 + copy_ev×0.2 + deck_target_ev×1.5
               (× confidence_weight: 1.0 for pz_verified)

new_card_ev_10x = E[rarity-weighted new cards in 10 consecutive openings]
```

---

## Reference Data

| File | Contents |
|---|---|
| `data/reference/pack_sources.json` | 3228 card → pack mappings (A1–B3A + PROMO-A/B) |
| `data/reference/pz_pack_odds.json` | PZ per-card drop chances (45 packs: 24 regular + 21 promo) |
| `data/reference/pull_probability_model.json` | Pull rate model v0.6.0, `pz_verified` |

**Pull rate source:** Pokemon Zone pack pages (`?show_pack_odds=1&show_pack_slot_odds=1`). All 24 regular packs and 21 promo packs are `pz_verified`. No in-app verification required.

---

## Utility Scripts

These are not part of the daily pipeline — run them when reference data needs rebuilding (e.g., new set release).

```bash
# New pack/cards appeared after a sync? Refresh PZ odds + reference automatically.
# Live fetch via stored sync auth — no manual HAR export needed.
python3 scripts/ingest_pz.py                                      # dry-run: report new packs
python3 scripts/ingest_pz.py --apply --write-pack-sources --rebuild-refs
#   → writes pz_pack_odds.json (drop odds), adds pack_sources records for the new
#     cards, and rebuilds card_reference.json so validation passes. Re-run the
#     pipeline afterwards. Use `--har FILE` to ingest a browser capture offline.

# Pack source reference rebuild (if pack_sources.json needs updating)
python3 scripts/build_pack_sources.py
python3 scripts/validate_pack_sources.py

# Pull probability model rebuild/validation
python3 scripts/build_pull_probability_model.py
python3 scripts/validate_pull_probability_model.py
```

---

## Sync Notes

- Rate-limited to once per ~24h by Pokemon Zone (skips gracefully if too early)
- Chrome136 TLS impersonation (`curl-cffi`) prevents Cloudflare 403 on headless syncs
- Raw API response not committed (`data/sync/last_sync_raw.json` gitignored)
- Player stats (hourglasses, shop tickets) fetched automatically on each sync
- **Auth expiry is graceful:** PZ sessions last ~3–4 weeks. When stored auth lapses the
  pipeline does **not** fail — it keeps going on your existing `collection.json`, still
  prints recommendations, and surfaces the one-step refresh
  (`python3 scripts/sync_collection.py --curl-import`, which reads your clipboard). A
  heads-up also prints once the stored auth passes 21 days, before it lapses mid-run.

---

## Roadmap / Known Limitations

- **Deck-building EV (deferred):** The model currently optimizes purely for collection
  completion (owned 0 / 1 / 2+ per printing). A deck-target scoring layer
  (`deck_recommendation_validation.json`) is stubbed in `build_pack_ev.py` and
  `generate_pack_recommendation_report.py` but intentionally inert — `deck_target_ev`
  is always 0 at runtime. When deck logic lands, the owned-count basis will switch to
  name-level counting (decks can mix sets) and the `SCORING_WEIGHTS["deck_target"]`
  term will become active.
- **Wonder Pick / trade / craft:** not modelled.
- **Event / limited packs:** included via `--include-limited` flag; ranked on the same
  EV metric but noted separately.
