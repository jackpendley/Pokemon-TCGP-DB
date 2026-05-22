# Pokemon TCG Pocket Collection Database

Personal collection tracker and pack-opening optimizer for Pokémon TCG Pocket.

## Quick Start

```bash
python3 scripts/run_recommendations.py
```

Syncs collection from Pokemon Zone, runs the full EV pipeline, and prints a condensed summary. Full verbose output logged to `data/pipeline.log`.

```
  ✓  Sync collection         599 cards, 277 unique
  ✓  Validate collection     277 entries, total=599
  ✓  Normalize collection    OK
  ✓  Build pack EV           24 packs
  ✓  Build promo EV          21 promo packs
  ✓  Recommendations         OK
  ✓  Spending plan           OK

  Top pack:   Paldean Wonders (adj_ev=4.7464) — 121/131 cards unowned
  Top promo:  Promo Pack A Series Vol. 8 (new_ev=0.9198) — Shop Tokens
  Pack Hourglasses: 756  → buy 10x Paldean Wonders (costs 120 ⧗), then re-run
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
| Total cards | 599 |
| Unique entries | 277 |
| Last synced | 2026-05-21 |

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
generate_hourglass_spending_plan.py
```

EV is computed directly from `pz_pack_odds.json` keyed by `(set_code, card_number)` — no fuzzy matching or confidence scoring. Pokemon Zone provides exact card identity on sync.

---

## Key Outputs

| File | Description |
|---|---|
| `review/inferred_pack_recommendations.md` | Ranked pack list with EV scores and deck-chase guide |
| `review/final_hourglass_spending_plan.md` | Scenario-based spending plan (conservative / moderate / aggressive) |
| `review/promo_pack_ev.md` | Promo pack rankings (Shop Token currency) |
| `data/pipeline.log` | Full verbose output from last run (gitignored) |

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

## Reference Data

| File | Contents |
|---|---|
| `data/reference/pack_sources.json` | 3119 card → pack mappings (A1–B3 + PROMO-A/B) |
| `data/reference/pz_pack_odds.json` | PZ per-card drop chances (45 packs: 24 regular + 21 promo) |
| `data/reference/pull_probability_model.json` | Pull rate model v0.6.0, `pz_verified` |

**Pull rate source:** Pokemon Zone pack pages (`?show_pack_odds=1&show_pack_slot_odds=1`). All 24 regular packs and 21 promo packs are `pz_verified`. No in-app verification required.

---

## Utility Scripts

These are not part of the daily pipeline — run them when reference data needs rebuilding (e.g., new set release).

```bash
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
